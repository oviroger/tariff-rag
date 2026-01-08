"""
app/generator_gemini.py
Generación de clasificación arancelaria con Gemini structured output.
"""

import json
import re
import unicodedata
import logging
from typing import Dict, Any, List, Optional

from openai import AzureOpenAI
from app.config import get_settings
from app.prompts import SYSTEM_INSTRUCTIONS, OUTPUT_SCHEMA, FOLLOWUP_SYSTEM_INSTRUCTIONS

logger = logging.getLogger(__name__)
settings = get_settings()


def _offline_result(evidence: List[Dict[str, Any]] | None = None, reason: str = "LLM offline") -> Dict[str, Any]:
    """
    Resultado consistente con guardrails cuando el LLM no está disponible.
    Sin códigos inventados.
    """
    # Fallback opcional: proponer candidatos desde evidencia recuperada
    top_from_retrieval: List[Dict[str, Any]] = []
    try:
        if getattr(settings, "enable_retrieval_fallback", False) and evidence:
            top_from_retrieval = _infer_candidates_from_docs(evidence, max_candidates=3)
    except Exception:
        top_from_retrieval = []

    warning_msg = "LLM offline"
    if reason:
        warning_msg = f"{warning_msg}: {reason}"

    return {
        "top_candidates": top_from_retrieval,
        "evidence": evidence or [],
        "applied_rgi": ["RGI 1"] if top_from_retrieval else [],
        "inclusions": [],
        "exclusions": [],
        "missing_fields": ["No se pudo usar el generador LLM. " + (reason or "")],
        "warnings": [warning_msg] + (["Usando candidatos derivados de la recuperación"] if top_from_retrieval else []),
        "versions": {"hs_edition": "HS_2022"},
    }


def _normalize_code_from_fields(src: Dict[str, Any]) -> List[str]:
    """Extrae y normaliza posibles códigos HS desde campos chapter/heading/subheading."""
    import re
    codes: List[str] = []
    # Preferir subheading si existe
    for key in ("subheading", "heading", "chapter"):
        val = src.get(key)
        if not val:
            continue
        s = str(val)
        digits = re.sub(r"\D", "", s)
        if not digits:
            continue
        # Solo devolver códigos con granularidad HS6 o superior (NANDINA8 / NATIONAL10).
        # Evitamos headings (4 dígitos) o capítulos (2 dígitos).
        if len(digits) >= 10:
            codes.append(digits[:10])
        if len(digits) >= 8:
            codes.append(digits[:8])
        if len(digits) >= 6:
            codes.append(f"{digits[:4]}.{digits[4:6]}")
    # Unicos manteniendo orden
    seen = set()
    out: List[str] = []
    for c in codes:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _infer_candidates_from_docs(context_docs: List[Dict[str, Any]], max_candidates: int = 3) -> List[Dict[str, Any]]:
    """Genera candidatos HS básicos a partir de metadatos de recuperación (sin LLM)."""
    counts: Dict[str, int] = {}
    for d in context_docs:
        src = d.get("_source") or d  # admite lista proveniente de _build_evidence
        if not isinstance(src, dict):
            continue
        for code in _normalize_code_from_fields(src):
            counts[code] = counts.get(code, 0) + 1
    # Ordenar por frecuencia y recortar
    sorted_codes = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    candidates: List[Dict[str, Any]] = []
    for code, freq in sorted_codes[:max_candidates]:
        digits = code.replace(".", "")
        if not digits.isdigit():
            continue
        if len(digits) == 6:
            level = "HS6"
        elif len(digits) == 8:
            level = "NANDINA8"
        elif len(digits) == 10:
            level = "NATIONAL10"
        else:
            # No devolvemos capítulos (2) ni headings (4)
            continue
        # Confianza heurística suave por frecuencia
        confidence = min(0.6, 0.35 + 0.1 * (freq - 1))
        candidates.append({
            "code": code,
            "description": "Candidato derivado de la evidencia recuperada",
            "confidence": confidence,
            "level": level,
        })
    return candidates


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
            "bucket": source.get("bucket", ""),
            "chapter": source.get("chapter", ""),
            "heading": source.get("heading", ""),
            "subheading": source.get("subheading", ""),
        })
    return evidence


def generate_label(query: str, context_docs: list, max_candidates: int = 5, conversation_history: list = None) -> dict:
    """
    Genera clasificación HS usando Azure OpenAI con contexto RAG.
    """

    evidence = _build_evidence_from_os_hits(context_docs)
    context_text = "\n\n".join([
        f"[Fragment {e['fragment_id']} | Score: {e['score']:.3f}]\n{e['text']}"
        for e in evidence
    ])

    # Construir historial conversacional para contexto
    history_text = ""
    if conversation_history:
        logger.info(f"📝 Historial recibido: {len(conversation_history)} turnos")
        logger.debug(f"Historial completo: {conversation_history}")
        history_lines = []
        for i, turn in enumerate(conversation_history, 1):
            user_msg = None
            assistant_msg = None
            
            # Soportar ambos formatos: tupla (user, assistant) y dict {user, assistant, timestamp}
            if isinstance(turn, dict):
                user_msg = turn.get("user")
                assistant_msg = turn.get("assistant")
            elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                user_msg, assistant_msg = turn[0], turn[1]
            
            if user_msg and assistant_msg:
                history_lines.append(f"Turno {i}:")
                history_lines.append(f"Usuario: {user_msg}")
                # Truncar respuesta larga del asistente
                assistant_short = assistant_msg[:300] + "..." if len(assistant_msg) > 300 else assistant_msg
                history_lines.append(f"Asistente: {assistant_short}")
                history_lines.append("")
        if history_lines:
            history_text = "\n".join(history_lines)

    # PROMPT MEJORADO: gestiona consultas vagas y seguimientos
    prompt = f"""Eres un experto en clasificación arancelaria del Sistema Armonizado (HS).

CONTEXTO RECUPERADO (HS docs):
{context_text}

{"HISTORIAL DE CONVERSACIÓN PREVIA:" if history_text else ""}
{history_text}

CONSULTA ACTUAL DEL USUARIO:
{query}

INSTRUCCIONES CRÍTICAS:
 - **LEE EL HISTORIAL COMPLETO**: Si hay conversación previa, el usuario puede haber proporcionado información en turnos anteriores. NO vuelvas a pedir datos que ya fueron dados.
 
 - **REGLA CRÍTICA - ESPECIFICACIONES SON CONTINUACIÓN**: Si el historial menciona un producto (ej: "laptop", "bus", "láminas de acero") y la consulta actual proporciona especificaciones técnicas (ej: "procesador X, RAM Y", "30 pasajeros", "espesor 5mm"), estas especificaciones son SIEMPRE ACERCA DEL MISMO PRODUCTO del historial. NO lo trates como producto diferente.

- 🔍 **DETECCIÓN AUTOMÁTICA DE CAMBIO DE TEMA** (SOLO para productos completamente diferentes):
  Si existe HISTORIAL DE CONVERSACIÓN (hay turnos previos):
     1. Compara el ÚLTIMO PRODUCTO del historial con la CONSULTA ACTUAL
     2. CAMBIO DE TEMA = usuario menciona un PRODUCTO DIFERENTE explícitamente
         → Ejemplos de cambio: "laptop" → "ahora quiero clasificar un bus" | "láminas de acero" → "¿y los plátanos?"
         → ACCIÓN: IGNORA TODO el contexto anterior, procesa COMO SI FUERA PRIMERA VEZ
     3. MISMO TEMA = usuario proporciona specs, detalles, o clarifica el mismo producto
         → Ejemplos: "laptop" → "procesador Snapdragon, 16GB RAM" | "bus" → "30 pasajeros, diesel" | "acero" → "espesor 5mm, galvanizado"
         → ACCIÓN: Usa el historial como contexto, RECUERDA el producto mencionado previamente
  **IMPORTANTE**: Especificaciones técnicas (procesador, RAM, espesor, pasajeros, cilindrada) NUNCA son cambio de tema - son completar información del producto ya mencionado.

- CONSULTAS VAGAS = solo menciona categoría genérica sin detalles específicos:
    * "vehículos" (¿automóvil? ¿camión? ¿bus? ¿moto?)
    * "productos de metal" (¿láminas? ¿cables? ¿tubos?)
    * "textiles" (¿algodón? ¿poliéster? ¿tejido plano o punto?)
  
    Para consultas VAGAS (Y sin historial que aporte datos):
    - NO propongas códigos HS. Deja top_candidates = []
    - En missing_fields: pide el TIPO ESPECÍFICO primero (ej: "Tipo de vehículo: automóvil, camión, motocicleta, autobús, etc.")
    - Luego pide uso, motor/cilindrada, características según el tipo
    - En warnings: "La descripción del producto es muy general. Se necesita más información para clasificar correctamente."

- CONSULTAS CON DETALLE SUFICIENTE = menciona tipo específico + algún detalle:
    * "bus a diésel" (tipo=bus, motor=diésel) ✓ puede proponer 8702
    * "automóvil de turismo" (tipo=automóvil, uso=turismo) ✓ puede proponer 8703
    * "láminas de acero laminadas en caliente" (tipo+proceso) ✓ puede proponer 7208
  
    Para consultas CON DETALLE:
    - Propón hasta {max_candidates} códigos HS (formato: XXXXXX o XXXX.XX)
    - Para HS, devuelve SOLO códigos HS6 (6 dígitos). Si solo puedes llegar a 2 o 4 dígitos, NO los devuelvas: pide los datos faltantes.
    - Para cada código: description (español), confidence (0.0-1.0), level (HS6 | NANDINA8 | NATIONAL10)
    - Indica inclusions/exclusions de la partida
    - Lista missing_fields solo si faltan detalles para refinar (ej: cilindrada, nuevo/usado)
    - Especifica applied_rgi (RGI 1, RGI 3(a), etc.)

REGLAS CRÍTICAS (VEHÍCULOS - Cap. 87):
- **CONTEXTO ES CLAVE**: Si en el historial el usuario dijo "es un bus a diesel", NO vuelvas a preguntar tipo de vehículo ni tipo de motor.
- Bus/autobús/microbús con ≥10 plazas → 8702
- Bus/autobús/microbús con ≤9 plazas → 8703
- Si ya sabes que es "bus a diésel" (del historial o consulta actual) y el usuario indica "30 pasajeros", propón 8702 con confianza 0.85+
- Para bus con motor conocido, missing_fields SOLO: "Cilindrada motor cm³ (afina subpartida)" y "Si es nuevo o usado"
    - Si la consulta o el historial menciona "nuevo" o "usado", NO incluyas "Si es nuevo o usado" en missing_fields.
- PROHIBIDO pedir "tipo de producto", "tipo de vehículo", "tipo de motor", "material", "características técnicas genéricas" si ya fueron mencionados en el historial.
- **CUANDO EL USUARIO RESPONDE**: Si el usuario dice "Es un bus a diesel", "Es para 30 pasajeros", etc., está COMPLETANDO información. Actualiza la clasificación con esos datos sin volver a pedirlos.

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

EJEMPLO 2 (bus a diésel + 15 pasajeros):
Usuario: "es un bus a diesel. es para 15 pasajeros"
{{
  "top_candidates": [
    {{"code": "8702.10", "description": "Vehículos para transporte de 10 o más personas (motor diésel)", "confidence": 0.88, "level": "HS6"}}
  ],
  "missing_fields": [
    "Cilindrada del motor en cm³ (afina la subpartida)",
    "Si es nuevo o usado"
  ],
  "inclusions": ["Autobuses", "Microbuses de 10-20 plazas", "Autobuses de más de 20 plazas"],
  "exclusions": ["Automóviles hasta 9 plazas (87.03)", "Vehículos para mercancías (87.04)"],
  "applied_rgi": ["RGI 1"],
  "warnings": []
}}

RESPUESTA (solo JSON, sin explicaciones adicionales):"""

    def _normalize_gemini_json(response_text: str) -> Dict[str, Any]:
        txt = (response_text or "").strip()
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            if txt.startswith("```json"):
                txt = txt[7:]
            if txt.startswith("```"):
                txt = txt[3:]
            if txt.endswith("```"):
                txt = txt[:-3]
            return json.loads(txt.strip())

    def _strip_accents(s: str) -> str:
        try:
            return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode('utf-8')
        except Exception:
            return (s or '')

    def _prune_missing_fields(res: Dict[str, Any], query_text: str, conversation_history: list) -> Dict[str, Any]:
        """Elimina campos faltantes que ya fueron respondidos en la consulta o historial."""
        text_blob = (query_text or "")
        text_blob = _strip_accents(text_blob).lower()
        # Incluir historial en texto de referencia
        if conversation_history:
            for turn in conversation_history:
                if isinstance(turn, (list, tuple)) and len(turn) >= 2:
                    text_blob += " " + _strip_accents(str(turn[0])).lower() + " " + _strip_accents(str(turn[1])).lower()
                elif isinstance(turn, dict):
                    user_msg = turn.get("user", "")
                    asst_msg = turn.get("assistant", "")
                    text_blob += " " + _strip_accents(str(user_msg)).lower() + " " + _strip_accents(str(asst_msg)).lower()

        before = list(res.get("missing_fields", []))

        def _remove_if_present(keyword: str):
            kw = _strip_accents(keyword).lower()
            filtered = []
            for m in res.get("missing_fields", []) or []:
                m_norm = _strip_accents(m).lower()
                if kw not in m_norm:
                    filtered.append(m)
            res["missing_fields"] = filtered

        # Si ya se dijo nuevo/usado, no lo pidas de nuevo
        if any(k in text_blob for k in ["nuevo", "usado"]):
            _remove_if_present("nuevo")
            _remove_if_present("usado")

        # Si ya se especificó tipo de vehículo (bus/autobús/microbús), no pedir "tipo de vehículo"
        if any(k in text_blob for k in ["bus", "autobus", "microbus"]):
            _remove_if_present("tipo de vehículo")
            _remove_if_present("tipo específico de vehículo")

        # Si ya se especificó tipo de motor (diesel/gasolina/eléctrico/híbrido), no pedirlo
        diesel_typos = ["diesel", "díesel", "diesl", "diessel", "diseel", "dieesl", "disel"]
        if any(k in text_blob for k in diesel_typos + ["gasolina", "electrico", "hibrido"]):
            _remove_if_present("tipo de motor")

        # Detectar cilindrada en texto (cc, cm3, cm³, litros)
        has_cc = False
        cc_patterns = [
            r"\b\d{3,5}(?:[\.,]\d{3})*(?:\s)*(?:cc|cm3|cm³|cmc)\b",
            r"\b\d{1,2}(?:[\.,]\d{1,2})?\s*(?:l|litros)\b",
            r"cilindrada\s*[:=]?\s*\d{3,5}"
        ]
        for pat in cc_patterns:
            if re.search(pat, text_blob, flags=re.IGNORECASE):
                has_cc = True
                break
        if has_cc:
            _remove_if_present("cilindrada")
            _remove_if_present("cm³")
            _remove_if_present("cm3")
            _remove_if_present("motor en cm")

        # Detectar plazas/pasajeros
        has_seats = False
        if re.search(r"\b\d{1,3}\s*(pasajeros|plazas)\b", text_blob, flags=re.IGNORECASE) or re.search(r"para\s+\d{1,3}\s*(pasajeros|plazas)\b", text_blob, flags=re.IGNORECASE):
            has_seats = True
        if has_seats:
            _remove_if_present("plazas")
            _remove_if_present("pasajeros")

        # --- ACERO: Detectar recubrimiento (galvanizado, pintado, estañado, etc.) ---
        if any(k in text_blob for k in ["galvanizado", "galvanizada", "galvanizadas", "pintura", "pintada", "pintado", "estanado", "cromado", "esmaltado", "cromada", "cromadas"]):
            _remove_if_present("recubrimiento")
            _remove_if_present("galvanizado")
            _remove_if_present("pintado")
            _remove_if_present("estanado")
            # Elimina campos que mencionan recubrimiento/galvanizado de forma genérica
            filtered = []
            for m in res.get("missing_fields", []) or []:
                m_norm = _strip_accents(m).lower()
                # Si el field contiene "recubrimiento" y el usuario ya mencionó galvanizado, elímina
                if "recubrimiento" in m_norm and any(k in text_blob for k in ["galvanizado", "galvanizada", "galvanizadas"]):
                    continue
                filtered.append(m)
            res["missing_fields"] = filtered

        # --- ACERO: Detectar proceso de laminado (caliente/frío) ---
        # Variaciones de caliente y frío (con acentos y sin)
        caliente_vars = ["laminada en caliente", "laminadas en caliente", "laminado en caliente", "laminacion en caliente", "laminacion caliente"]
        frio_vars = ["laminada en frio", "laminadas en frio", "laminada en frío", "laminadas en frío", "laminado en frio", "laminado en frío", "laminacion en frio", "laminacion en frío", "laminacion frio", "laminacion frío"]
        
        if any(k in text_blob for k in caliente_vars + frio_vars):
            _remove_if_present("proceso de laminado")
            _remove_if_present("laminado en caliente")
            _remove_if_present("laminado en frio")
            _remove_if_present("laminado en frío")
            # Elimina campos que mencionan proceso de laminado de forma genérica
            filtered = []
            for m in res.get("missing_fields", []) or []:
                m_norm = _strip_accents(m).lower()
                # Si el field contiene "laminado" y el usuario ya lo especificó, elímina
                if ("laminado" in m_norm or "proceso de laminado" in m_norm) and any(k in text_blob for k in caliente_vars + frio_vars):
                    continue
                filtered.append(m)
            res["missing_fields"] = filtered

        # --- ACERO: Detectar espesor en mm ---
        has_espesor = False
        espesor_patterns = [
            r"\b\d{1,4}(?:[\.,]\d{1,2})?\s*(?:mm|milímetros|milimetros)\b",
            r"espesor\s*[:=]?\s*\d{1,4}\s*mm"
        ]
        for pat in espesor_patterns:
            if re.search(pat, text_blob, flags=re.IGNORECASE):
                has_espesor = True
                break
        if has_espesor:
            _remove_if_present("espesor")
            _remove_if_present("espesor en mm")

        # Quitar duplicados preservando orden
        seen = set()
        dedup = []
        for m in res.get("missing_fields", []):
            if m not in seen:
                seen.add(m)
                dedup.append(m)
        res["missing_fields"] = dedup
        
        # Post-procesamiento agresivo: elimina campos que mencionan información ya dada
        final_missing = []
        for field in res.get("missing_fields", []):
            field_lower = _strip_accents(field).lower()
            skip = False
            
            # Variaciones de galvanizado
            galv_keywords = ["galvanizado", "galvanizada", "galvanizadas", "galvanizados", "galvaniza", "pintada", "pintado", "pintadas", "pintados", "estanado", "estañado", "cromado", "cromada"]
            
            # Si el usuario mencionó galvanizado/pintado/etc y el field pide recubrimiento, sáltalo
            if any(kw in field_lower for kw in ["recubrimiento", "galvanizado", "pintado", "estanado", "estañado", "cromado"]) and \
               any(k in text_blob for k in galv_keywords):
                logger.info(f"[PRUNE] Skipping field '{field}' because galvanizado/pintado detected in text_blob")
                skip = True
            
            # Variaciones de laminado
            laminado_keywords = ["laminada en caliente", "laminadas en caliente", "laminada en frio", "laminadas en frio", "laminada en frío", "laminadas en frío", "laminado en caliente", "laminado en frio", "laminado en frío", "laminacion", "laminacion en caliente", "laminacion en frio", "laminacion en frío"]
            
            # Si el usuario mencionó laminado en caliente/frío y el field pide proceso de laminado, sáltalo
            if ("proceso de laminado" in field_lower) and any(k in text_blob for k in laminado_keywords):
                logger.info(f"[PRUNE] Skipping field '{field}' because laminado process detected in text_blob")
                skip = True
            
            if not skip:
                final_missing.append(field)
        
        res["missing_fields"] = final_missing
        
        after = list(res.get("missing_fields", []))
        if before != after:
            logger.info(f"Pruning missing_fields. Before: {before} | After: {after}")
        
        # Logging para debug
        logger.info(f"[PRUNE DEBUG] text_blob: {text_blob[:300] if text_blob else 'empty'}")
        logger.info(f"[PRUNE DEBUG] Final missing_fields after pruning: {after}")
        
        return res

    def _normalize_result_fields(res: Dict[str, Any]) -> Dict[str, Any]:
        res.setdefault("top_candidates", [])
        res.setdefault("applied_rgi", [])
        res.setdefault("inclusions", [])
        res.setdefault("exclusions", [])
        res.setdefault("missing_fields", [])
        res.setdefault("warnings", [])
        # Normalizar candidatos para cumplir el contrato de niveles: HS6/NANDINA8/NATIONAL10.
        allowed_levels = {"HS6", "NANDINA8", "NATIONAL10"}
        normalized_candidates = []
        dropped = 0
        for candidate in res.get("top_candidates", []) or []:
            if not isinstance(candidate, dict):
                dropped += 1
                # Alinear nivel con el código (p.ej. por error marcó HS6 con 8 dígitos)
                candidate["level"] = inferred

            normalized_candidates.append(candidate)

        if dropped:
            res.setdefault("warnings", [])
            res["warnings"].append(
                f"Se descartaron {dropped} candidato(s) porque el código no era HS6/NANDINA8/NATIONAL10 o el nivel era inválido."
            )
        res["top_candidates"] = normalized_candidates
        if "evidence" not in res:
            res["evidence"] = [
                {"fragment_id": e["fragment_id"], "score": e["score"], "reason": "retrieved_by_hybrid_search"}
                for e in evidence
            ]
        return res

    def _try_azure() -> Optional[Dict[str, Any]]:
        s = get_settings()
        if not (s.azure_openai_endpoint and s.azure_openai_key and s.azure_openai_chat_deployment):
            return None
        try:
            client = AzureOpenAI(
                api_key=s.azure_openai_key,
                azure_endpoint=s.azure_openai_endpoint,
                api_version=s.azure_openai_api_version,
            )
            # Use max_completion_tokens for newer models (GPT-4o, GPT-5, etc.)
            # GPT-5-nano only supports temperature=1 (default), so we omit it
            completion = client.chat.completions.create(
                model=s.azure_openai_chat_deployment,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=get_settings().gemini_max_output_tokens,
                response_format={"type": "json_object"},
            )
            choice = completion.choices[0].message.content if completion.choices else "{}"
            parsed = json.loads(choice or "{}")
            norm = _normalize_result_fields(parsed)
            norm = _prune_missing_fields(norm, query, conversation_history)
            return norm
        except Exception as e:
            logger.error(f"Error en generación con Azure OpenAI: {e}")
            return None

    res_azure = _try_azure()
    if res_azure is not None:
        return res_azure

    # Último recurso: offline
    return _offline_result(evidence=context_docs, reason="LLM offline o sin cuota disponible (Azure)")


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
    Usa Azure OpenAI para responder una pregunta de seguimiento o reclasificar con nueva info.
    """
    if not question or not previous_result:
        return "No hay clasificación previa en contexto."
    try:
        s = get_settings()
        if not (s.azure_openai_endpoint and s.azure_openai_key and s.azure_openai_chat_deployment):
            return _fallback_followup_answer(question, previous_result)

        client = AzureOpenAI(
            api_key=s.azure_openai_key,
            azure_endpoint=s.azure_openai_endpoint,
            api_version=s.azure_openai_api_version,
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

        completion = client.chat.completions.create(
            model=s.azure_openai_chat_deployment,
            messages=[
                {"role": "system", "content": FOLLOWUP_SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "text"},
        )
        text = completion.choices[0].message.content if completion.choices else ""
        text = (text or "").strip()
        return text or _fallback_followup_answer(question, previous_result)
    except Exception as e:
        logger.exception("Error en generate_followup_answer: %s", e)
        return _fallback_followup_answer(question, previous_result)
