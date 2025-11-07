"""
app/generator_gemini.py
Generación de clasificación arancelaria con Gemini structured output.
"""

import json
import logging
from typing import Dict, Any, List

import google.generativeai as genai
from app.config import get_settings
from app.prompts import SYSTEM_INSTRUCTIONS, OUTPUT_SCHEMA, FOLLOWUP_SYSTEM_INSTRUCTIONS

logger = logging.getLogger(__name__)

# Config Gemini API key
settings = get_settings()
try:
    if getattr(settings, "gemini_api_key", None):
        genai.configure(api_key=settings.gemini_api_key)
        logger.info("Gemini API key configured.")
    else:
        logger.warning("GEMINI_API_KEY missing - LLM generation will be offline.")
except Exception as e:
    logger.exception("Failed to configure Gemini: %s", e)


def _offline_result(evidence: List[Dict[str, Any]] | None = None, reason: str = "LLM offline") -> Dict[str, Any]:
    """
    Resultado consistente con guardrails cuando el LLM no está disponible.
    Sin códigos inventados.
    """
    return {
        "top_candidates": [],
        "evidence": evidence or [],
        "applied_rgi": [],
        "inclusions": [],
        "exclusions": [],
        "missing_fields": ["No se pudo usar el generador LLM. " + reason],
        "warnings": ["LLM offline"],
        "versions": {"hs_edition": "HS_2022"},
    }


def _build_evidence_from_os_hits(context_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for doc in context_docs[:5]:  # Top 5 para no exceder límites
        source = doc.get("_source", {}) or {}
        evidence.append({
            "fragment_id": doc.get("_id", "unknown"),
            "score": doc.get("_score", 0.0),
            "text": source.get("text", "")[:600],  # Limitar texto
            "doc_id": source.get("doc_id", ""),
            "unit": source.get("unit", ""),
            "bucket": source.get("bucket", "")
        })
    return evidence


def generate_label(query: str, context_docs: list, max_candidates: int = 5) -> dict:
    """
    Genera clasificación HS usando Gemini con contexto RAG.
    """
    if not getattr(settings, "gemini_api_key", None):
        logger.warning("GEMINI_API_KEY no configurada, usando resultado offline.")
        return _offline_result(evidence=context_docs, reason="verifica GEMINI_API_KEY / conectividad")

    evidence = _build_evidence_from_os_hits(context_docs)
    context_text = "\n\n".join([
        f"[Fragment {e['fragment_id']} | Score: {e['score']:.3f}]\n{e['text']}"
        for e in evidence
    ])

    # PROMPT MEJORADO: gestiona consultas vagas y seguimientos
    prompt = f"""Eres un experto en clasificación arancelaria del Sistema Armonizado (HS).

CONTEXTO RECUPERADO (HS docs):
{context_text}

CONSULTA DEL USUARIO:
{query}

INSTRUCCIONES:
- Si la consulta es VAGA o GENÉRICA (ej: "vehículos" sin especificar tipo/uso):
  - NO propongas códigos HS.
  - Deja top_candidates VACÍO [].
  - En missing_fields, lista la información necesaria (tipo, uso, características técnicas, estado).
  - En warnings, indica: "La descripción del producto es muy general. Se necesita más información para clasificar correctamente."

- Si la consulta tiene SUFICIENTE DETALLE (o es un seguimiento que completa información):
  - Propón hasta {max_candidates} códigos HS candidatos (formato: XXXXXX o XXXX.XX).
  - Para cada código: description (español), confidence (0.0-1.0), level (HS2/HS4/HS6).
  - Indica inclusions/exclusions de la partida.
  - Lista missing_fields solo si aún faltan detalles para refinar (ej: cilindrada, peso, nuevo/usado).
  - Especifica applied_rgi (RGI 1, RGI 3(a), etc.).

FORMATO DE RESPUESTA (JSON estricto, en español):
{{
  "top_candidates": [
    {{"code": "XXXXXX", "description": "...", "confidence": 0.85, "level": "HS6"}}
  ],
  "inclusions": ["...", "..."],
  "exclusions": ["...", "..."],
  "applied_rgi": ["RGI 1"],
  "missing_fields": ["...", "..."],
  "warnings": []
}}

EJEMPLO 1 (consulta vaga):
Usuario: "Cual es la partida arancelaria de los vehículos"
{{
  "top_candidates": [],
  "missing_fields": [
    "Tipo de vehículo (automóvil, camión, motocicleta, etc.)",
    "Uso del vehículo (transporte de personas, mercancías, uso especial)",
    "Características técnicas (cilindrada, tipo de motor, peso)",
    "Si está completo o incompleto",
    "Si es nuevo o usado"
  ],
  "warnings": ["La descripción del producto es muy general. Se necesita más información para clasificar el vehículo correctamente."]
}}

EJEMPLO 2 (seguimiento con tipo):
Usuario: "Tipo de vehículo automóvil"
{{
  "top_candidates": [
    {{"code": "8703", "description": "Automóviles de turismo para transporte de personas", "confidence": 0.70, "level": "HS4"}}
  ],
  "missing_fields": [
    "Cilindrada del motor",
    "Tipo de motor (gasolina, diesel, eléctrico, híbrido)",
    "Si es nuevo o usado"
  ],
  "inclusions": ["Automóviles de turismo", "Vehículos familiares (station wagon)"],
  "exclusions": ["Vehículos de la partida 87.02 (transporte de más de 10 personas)"],
  "applied_rgi": ["RGI 1"]
}}

RESPUESTA (solo JSON, sin explicaciones adicionales):"""

    try:
        s = get_settings()
        model_name = s.gemini_model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(
                temperature=s.gemini_temperature,
                top_p=s.gemini_top_p,
                top_k=s.gemini_top_k,
                max_output_tokens=s.gemini_max_output_tokens,
                response_mime_type="application/json",
                response_schema=OUTPUT_SCHEMA,
            ),
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            },
            system_instruction=SYSTEM_INSTRUCTIONS,
        )

        logger.info(f"Llamando a Gemini {model_name} para generación...")
        response = model.generate_content(prompt)

        if not getattr(response, "parts", None):
            finish = getattr(response.candidates[0], "finish_reason", "unknown")
            logger.warning(f"Gemini bloqueó la respuesta. Finish reason: {finish}")
            raise ValueError(f"Gemini bloqueó el contenido (finish_reason={finish})")

        text = (response.text or "").strip()
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            result = json.loads(text.strip())

        # Normalizar campos
        result.setdefault("top_candidates", [])
        result.setdefault("applied_rgi", [])
        result.setdefault("inclusions", [])
        result.setdefault("exclusions", [])
        result.setdefault("missing_fields", [])
        result.setdefault("warnings", [])

        # Evitar descripciones None
        for candidate in result.get("top_candidates", []):
            if candidate.get("description") is None:
                candidate["description"] = ""

        # Adjuntar evidencia
        if "evidence" not in result:
            result["evidence"] = [
                {"fragment_id": e["fragment_id"], "score": e["score"], "reason": "retrieved_by_hybrid_search"}
                for e in evidence
            ]

        logger.info(f"Gemini generó {len(result.get('top_candidates', []))} candidatos")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Gemini no devolvió JSON válido: {e}")
        return _offline_result(evidence=context_docs, reason="JSON inválido de LLM")
    except Exception as e:
        logger.error(f"Error en generación con Gemini: {e}")
        return _offline_result(evidence=context_docs, reason=str(e))


def generate_structured(query: str, docs: list, versions: dict) -> dict:
    """
    Compatibilidad con interfaces previas.
    Convierte docs al formato de OpenSearch y delega a generate_label.
    """
    os_docs = []
    for d in docs:
        if hasattr(d, "metadata") and hasattr(d, "page_content"):
            os_docs.append({
                "_id": d.metadata.get("fragment_id", ""),
                "_score": 1.0,
                "_source": {
                    "text": d.page_content,
                    "doc_id": d.metadata.get("source", ""),
                    "unit": d.metadata.get("unit", ""),
                    "edition": d.metadata.get("edition", "")
                }
            })
        else:
            os_docs.append(d)
    return generate_label(query, os_docs)


def _fallback_followup_answer(question: str, previous_result: dict) -> str:
    # Respuesta simple sin LLM, basada en previous_result
    q = (question or "").lower()
    candidates = previous_result.get("top_candidates") or previous_result.get("candidates") or []
    applied_rgi = previous_result.get("applied_rgi", [])
    inclusions = previous_result.get("inclusions", [])
    missing = previous_result.get("missing_fields", [])
    if not previous_result:
        return "No hay clasificación previa en contexto."
    if any(k in q for k in ["por qué", "porque", "razón", "justifica", "explica"]):
        parts = []
        if applied_rgi:
            parts.append(f"Se aplicaron: {', '.join(applied_rgi)}.")
        if inclusions:
            parts.append("Incluye:\n" + "\n".join(f"- {i}" for i in inclusions))
        return "### ¿Por qué estos códigos?\n\n" + ("\n\n".join(parts) or "La descripción coincide con la partida propuesta.")
    if any(k in q for k in ["qué falta", "información", "missing", "faltante", "detalles"]):
        if missing:
            return "### Información adicional requerida\n\n" + "\n".join(f"- {m}" for m in missing)
        return "No faltan datos para HS6; a nivel nacional podrían requerirse detalles adicionales."
    if any(k in q for k in ["alternativa", "otro código", "otras opciones"]):
        if len(candidates) > 1:
            lines = []
            for c in candidates[1:]:
                code = c.get("code") or c.get("hs_code")
                conf = c.get("confidence", 0) * 100
                lines.append(f"- {code} (Confianza: {conf:.0f}%)")
            return "### Códigos alternativos\n\n" + "\n".join(lines)
        return "No hay alternativas con suficiente confianza."
    if any(k in q for k in ["resumen", "resume", "sintetiza"]):
        if candidates:
            main = candidates[0]
            code = main.get("code") or main.get("hs_code")
            conf = main.get("confidence", 0) * 100
            return f"### Resumen\n\nCódigo recomendado: {code} (Confianza: {conf:.0f}%)."
        return "No hay resumen disponible."
    return "Esta es una pregunta de seguimiento, pero necesito más contexto o una clasificación previa."


def generate_followup_answer(question: str, previous_result: dict) -> str:
    """
    Usa Gemini para responder una pregunta de seguimiento o reclasificar con nueva info.
    """
    if not question or not previous_result:
        return "No hay clasificación previa en contexto."
    try:
        if not getattr(settings, "gemini_api_key", None):
            return _fallback_followup_answer(question, previous_result)

        model = genai.GenerativeModel(
            model_name="models/gemini-2.0-flash",
            system_instruction=FOLLOWUP_SYSTEM_INSTRUCTIONS,
        )
        
        # Construir prompt con historial y detectar si es reclasificación
        prompt_parts = []
        
        # Agregar historial si existe
        conv_history = previous_result.get("conversation_history")
        if conv_history:
            prompt_parts.append("## Historial de conversación:\n")
            prompt_parts.append(conv_history)
            prompt_parts.append("\n---\n")
        
        # Agregar clasificación actual
        prompt_parts.append("## Clasificación previa:\n")
        candidates = previous_result.get("top_candidates", [])
        if candidates:
            top = candidates[0]
            prompt_parts.append(f"**Código principal:** {top.get('code', 'N/A')}")
            prompt_parts.append(f"**Descripción:** {top.get('description', '')}")
        
        # Agregar información faltante si existe
        missing = previous_result.get("missing_fields", [])
        if missing:
            prompt_parts.append("\n**Información que faltaba:**")
            for field in missing:
                prompt_parts.append(f"- {field}")
        
        prompt_parts.append("\n---\n")
        
        # Pregunta/información del usuario
        prompt_parts.append(f"**Usuario dice:** {question}\n\n")
        
        # Instrucciones adaptativas
        prompt_parts.append("**INSTRUCCIONES:**\n")
        prompt_parts.append("Si el usuario está proporcionando información adicional (estado, presentación, tipo):\n")
        prompt_parts.append("1. Actualiza la clasificación con los nuevos datos\n")
        prompt_parts.append("2. Ajusta el código HS según corresponda\n")
        prompt_parts.append("3. Explica el cambio si lo hay\n")
        prompt_parts.append("4. Menciona si ahora hay mayor certeza\n\n")
        prompt_parts.append("Si es una pregunta de seguimiento normal:\n")
        prompt_parts.append("- Responde basándote solo en la clasificación previa\n\n")
        prompt_parts.append("Responde en español con Markdown simple.")
        
        prompt = "".join(prompt_parts)
        
        resp = model.generate_content(prompt)
        text = (getattr(resp, "text", None) or "").strip()
        return text or _fallback_followup_answer(question, previous_result)
    except Exception as e:
        logger.exception("Error en generate_followup_answer: %s", e)
        return _fallback_followup_answer(question, previous_result)
