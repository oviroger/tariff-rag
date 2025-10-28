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


def generate_label(query: str, context_docs: List[Dict[str, Any]], max_candidates: int = 3) -> Dict[str, Any]:
    """
    Genera clasificación arancelaria usando Gemini con structured output.
    Args:
        query: Descripción del producto a clasificar
        context_docs: Lista de hits de OpenSearch (formato: {_id, _score, _source: {text, ...}})
        max_candidates: Número máximo de códigos candidatos
    Returns:
        Dict con: top_candidates, applied_rgi, inclusions, exclusions, missing_fields
    """

    # Si no hay clave API, retornar resultado offline (sin inventar códigos)
    if not getattr(settings, "gemini_api_key", None):
        logger.warning("GEMINI_API_KEY no configurada, usando resultado offline.")
        return _offline_result(evidence=context_docs, reason="verifica GEMINI_API_KEY / conectividad")

    # Construir evidencia y contexto textual
    evidence = _build_evidence_from_os_hits(context_docs)
    context_text = "\n\n".join([
        f"[Fragment {e['fragment_id']} | Score: {e['score']:.3f}]\n{e['text']}"
        for e in evidence
    ])

    # Prompt (las reglas de alcance y guardrails están en SYSTEM_INSTRUCTIONS)
    prompt = f"""You are an expert in tariff classification using the Harmonized System (HS).

PRODUCT DESCRIPTION:
{query}

RELEVANT HS DOCUMENTATION (from tariff database):
{context_text}

TASK:
Based on the product description and HS documentation, provide a complete tariff classification analysis.

INSTRUCTIONS:
1. Identify {max_candidates} most likely HS codes with confidence scores
2. Apply relevant General Rules for Interpretation (RGI)
3. List what products are INCLUDED in this classification
4. List what products are EXCLUDED
5. Identify any MISSING information needed for precise classification

Return ONLY valid JSON, no markdown formatting.
"""

    try:
        model_name = "models/gemini-2.0-flash"

        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",
                # Si tu SDK >= 0.8.x soporta schema, esto ayuda a mantener el contrato
                "response_schema": OUTPUT_SCHEMA,
            },
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            },
            # CRÍTICO: Guardrails de alcance y formato
            system_instruction=SYSTEM_INSTRUCTIONS,
        )

        logger.info(f"Llamando a Gemini {model_name} para generación...")
        response = model.generate_content(prompt)

        # Manejo de respuesta bloqueada
        if not getattr(response, "parts", None):
            finish = getattr(response.candidates[0], "finish_reason", "unknown")
            logger.warning(f"Gemini bloqueó la respuesta. Finish reason: {finish}")
            raise ValueError(f"Gemini bloqueó el contenido (finish_reason={finish})")

        # Parsear JSON robusto
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

        # Normalizar campos esperados
        result.setdefault("top_candidates", [])
        result.setdefault("applied_rgi", ["RGI 1"])
        result.setdefault("inclusions", [])
        result.setdefault("exclusions", [])
        result.setdefault("missing_fields", [])
        # Adjuntar evidencia si no vino ya integrada
        if "evidence" not in result:
            result["evidence"] = [
                {"fragment_id": e["fragment_id"], "score": e["score"], "reason": "retrieved_by_hybrid_search"}
                for e in evidence
            ]

        logger.info(f"Gemini generó {len(result.get('top_candidates', []))} candidatos")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Gemini no devolvió JSON válido: {e}")
        # Devolvemos fallback sin códigos inventados
        return _offline_result(evidence=context_docs, reason="JSON inválido de LLM")

    except Exception as e:
        logger.error(f"Error en generación con Gemini: {e}")
        # Devolvemos fallback sin códigos inventados
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
    Usa Gemini para responder una pregunta de seguimiento basándose SOLO en previous_result.
    Devuelve texto en español con Markdown ligero.
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
        prompt = (
            "Clasificación previa (JSON):\n"
            f"{json.dumps(previous_result, ensure_ascii=False, indent=2)}\n\n"
            f"Pregunta del usuario: {question}\n\n"
            "Responde en español, con Markdown simple, y SOLO en base a esa clasificación."
        )
        resp = model.generate_content(prompt)
        text = (getattr(resp, "text", None) or "").strip()
        return text or _fallback_followup_answer(question, previous_result)
    except Exception as e:
        logger.exception("Error en generate_followup_answer: %s", e)
        return _fallback_followup_answer(question, previous_result)
