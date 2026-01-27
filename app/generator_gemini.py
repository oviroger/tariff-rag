"""
app/generator_gemini.py
Generación de clasificación arancelaria con Gemini structured output.
"""

import json
import re
import unicodedata
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from openai import AzureOpenAI
from app.config import get_settings
from app.prompts import SYSTEM_INSTRUCTIONS, OUTPUT_SCHEMA, FOLLOWUP_SYSTEM_INSTRUCTIONS

logger = logging.getLogger(__name__)
settings = get_settings()

# Cargar configuración de palabras clave de dispositivos
_DEVICE_CONFIG_PATH = Path(__file__).parent / "device_keywords.json"
_DEVICE_CONFIG: Dict[str, Any] = {}

def _load_device_config() -> Dict[str, Any]:
    """Carga configuración de palabras clave desde device_keywords.json"""
    global _DEVICE_CONFIG
    if not _DEVICE_CONFIG:
        try:
            if _DEVICE_CONFIG_PATH.exists():
                with open(_DEVICE_CONFIG_PATH, "r", encoding="utf-8") as f:
                    _DEVICE_CONFIG = json.load(f)
                logger.info(f"Device keywords loaded from {_DEVICE_CONFIG_PATH}")
            else:
                logger.warning(f"Device keywords file not found: {_DEVICE_CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Error loading device_keywords.json: {e}")
    return _DEVICE_CONFIG


def _default_missing_fields(blob: str) -> List[str]:
    """Generate a minimal, deterministic missing_fields list based on the query blob."""
    b = (blob or "").lower()
    
    # Electrodomésticos (Cap. 84-85)
    appliances = ["electrodomestico", "electrodoméstico", "lavadora", "refrigerador", "nevera", 
                  "frigorifico", "frigorífico", "microondas", "horno", "cocina", "estufa",
                  "lavavajilla", "lavavajillas", "secadora", "aspiradora", "batidora", "licuadora"]
    if any(a in b for a in appliances):
        # Caso específico: lavadora → preguntas concretas en vez de genéricas
        if "lavadora" in b:
            return [
                "Capacidad de carga en kg",
                "Tipo de carga (frontal o superior)",
                "¿Incluye función de secado o solo lava?",
                "Voltaje/frecuencia (110/220V, 50/60Hz)",
                "¿Es para uso doméstico o industrial/comercial?",
                "¿Es nuevo o usado?",
            ]
        # Otros electrodomésticos
        return [
            "¿Qué electrodoméstico específico es?",
            "¿Es para uso doméstico o industrial/comercial?",
            "¿Es nuevo o usado?",
        ]
    
    # Vehículos (Cap. 87)
    vehicles = ["vehiculo", "vehículo", "auto", "carro", "coche", "camion", "camión", "bus", 
                "autobus", "autobús", "microbus", "microbús", "moto", "motocicleta"]
    if any(v in b for v in vehicles):
        return [
            "Tipo de motor (gasolina, diésel, eléctrico, híbrido)",
            "Cilindrada del motor en cm³",
            "Número de plazas/pasajeros",
        ]
    
    # Metales (Cap. 72-76)
    metals = ["acero", "steel", "hierro", "lamina", "lámina", "chapa", "plancha", "bobina", 
              "inox", "aluminio", "cobre", "metal"]
    if any(m in b for m in metals):
        return [
            "Tipo de producto metálico y material (lámina, bobina, acero, aluminio, etc.)",
            "Espesor en mm",
            "Dimensiones (ancho y largo)",
            "Proceso (laminado en caliente o en frío)",
            "Recubrimiento si aplica (galvanizado, pintado, etc.)",
        ]
    
    # Textiles (Cap. 50-63)
    textiles = ["tela", "tejido", "textil", "algodón", "algodon", "poliéster", "poliester", 
                "lana", "seda", "prenda", "camisa", "pantalón", "pantalon"]
    if any(t in b for t in textiles):
        return [
            "¿De qué material está hecho? (algodón, poliéster, lana, mezcla, etc.)",
            "¿Es tejido, punto o no tejido?",
            "¿Cuál es el uso? (prenda de vestir, tela por metro, uso industrial)",
        ]
    
    # Alimentos (Cap. 01-24)
    foods = ["carne", "pescado", "fruta", "verdura", "alimento", "comida", "bebida", 
             "conserva", "enlatado", "congelado"]
    if any(f in b for f in foods):
        return [
            "¿Qué tipo de alimento específico?",
            "¿Es fresco, refrigerado, congelado o procesado?",
            "¿Cómo está presentado? (entero, troceado, fileteado, envasado)",
        ]
    
    # Computadoras/Electrónica (Cap. 84-85)
    electronics = ["computadora", "ordenador", "laptop", "notebook", "tablet", "celular", 
                   "móvil", "movil", "teléfono", "telefono", "pantalla", "monitor"]
    if any(e in b for e in electronics):
        return [
            "¿Qué tipo de dispositivo específico? (laptop, tablet, teléfono móvil, monitor, etc.)",
            "¿Es nuevo o usado?",
        ]
    
    # Muebles (Cap. 94)
    furniture = ["mueble", "silla", "mesa", "estanteria", "estantería", "armario", "cama", "sofá", "sofa"]
    if any(f in b for f in furniture):
        return [
            "¿Qué tipo de mueble específico?",
            "¿De qué material principal está hecho? (madera, metal, plástico)",
            "¿Para qué uso? (hogar, oficina, comercial)",
        ]
    
    # Genérico (cuando no se detecta categoría)
    return [
        "Descripción precisa del producto (material, uso, presentación)",
        "Características técnicas clave (dimensiones, potencia, composición)",
        "Estado o presentación (nuevo/usado, a granel, envasado)",
    ]


def _normalize_code_from_fields(src: Dict[str, Any]) -> List[str]:
    """Extrae y normaliza posibles códigos HS desde campos chapter/heading/subheading."""
    codes: List[str] = []
    for key in ("subheading", "heading", "chapter"):
        val = src.get(key)
        if not val:
            continue
        s = str(val)
        digits = re.sub(r"\D", "", s)
        if not digits:
            continue
        if len(digits) >= 10:
            codes.append(digits[:10])
        if len(digits) >= 8:
            codes.append(digits[:8])
        if len(digits) >= 6:
            codes.append(f"{digits[:4]}.{digits[4:6]}")
    seen = set()
    out: List[str] = []
    for c in codes:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _ensure_missing_fields(res: Dict[str, Any], blob: str, conversation_history: list | None = None) -> Dict[str, Any]:
    """Ensure missing_fields is populated with sensible defaults when empty.
    IMPORTANT: Also prunes defaults based on conversation_history to avoid re-asking answered questions.
    """
    if res.get("missing_fields"):
        return res
    
    # Get defaults
    res["missing_fields"] = _default_missing_fields(blob)
    
    # Prune defaults based on conversation history to avoid re-asking
    # This is critical because _aggressive_missing_fields_cleanup may have cleared all fields
    res = _prune_missing_fields(res, blob, conversation_history or [])
    
    return res


def _offline_result(evidence: List[Dict[str, Any]] | None = None, reason: str = "LLM offline") -> Dict[str, Any]:
    """Deterministic fallback when LLM is unavailable."""
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
        "missing_fields": _default_missing_fields(""),
        "warnings": [warning_msg] + (["Usando candidatos derivados de la recuperación"] if top_from_retrieval else []),
        "versions": {"hs_edition": "HS_2022"},
    }


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
            "year": source.get("year"),  # Incluir año
        })
    return evidence


def _normalize_result_fields(res: Dict[str, Any], evidence: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normaliza los campos del resultado del LLM."""
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
            continue

        code = str(candidate.get("code") or candidate.get("hs_code") or "")
        digits = re.sub(r"\D", "", code)
        inferred = None
        if len(digits) >= 10:
            inferred = "NATIONAL10"
        elif len(digits) >= 8:
            inferred = "NANDINA8"
        elif len(digits) == 6:
            inferred = "HS6"

        level = candidate.get("level")
        if level not in allowed_levels:
            candidate["level"] = inferred or "HS6"

        normalized_candidates.append(candidate)

    if dropped:
        res.setdefault("warnings", [])
        res["warnings"].append(
            f"Se descartaron {dropped} candidato(s) porque el código no era HS6/NANDINA8/NATIONAL10 o el nivel era inválido."
        )
    res["top_candidates"] = normalized_candidates
    if "evidence" not in res and evidence:
        res["evidence"] = [
            {"fragment_id": e["fragment_id"], "score": e["score"], "reason": "retrieved_by_hybrid_search"}
            for e in evidence
        ]
    return res


def _strip_accents(s: str) -> str:
    """Remove accents from string."""
    try:
        return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode('utf-8')
    except Exception:
        return (s or '')


def _text_blob_from_query_history(query: str, conversation_history: list | None, include_assistant: bool = False) -> str:
    """Build text blob from query and conversation history."""
    parts = [query or ""]
    if conversation_history:
        for turn in conversation_history:
            if isinstance(turn, dict):
                if turn.get("user"):
                    parts.append(str(turn.get("user")))
                if include_assistant and turn.get("assistant"):
                    parts.append(str(turn.get("assistant")))
            elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                parts.append(str(turn[0]))
                if include_assistant:
                    parts.append(str(turn[1]))
    text_blob = " ".join(parts).lower()
    logger.info(f"LOG_TEXT_BLOB_RAW: '{text_blob[:200]}'")
    # Important: Use the same _normalize_text normalization for field matching
    normalized = _normalize_text(text_blob)
    logger.info(f"LOG_TEXT_BLOB_NORMALIZED: '{normalized[:200]}'")
    return normalized


def _normalize_text(text: str) -> str:
    """Normalize text: strip accents, remove special chars, lowercase.
    IMPORTANT: Preserves numbers which are critical for field matching (50 pasajeros, etc.)
    Also cleans up corrupted UTF-8 sequences from LLM output.
    """
    import unicodedata
    try:
        # First, clean up corrupted UTF-8 sequences (e.g., "┬┐" from mojibake)
        # These are often caused by double/triple encoding issues
        text = (text or '').encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        
        # Try NFD decomposition
        nfd = unicodedata.normalize('NFD', text)
        # Remove combining characters (accents) but KEEP numbers, letters, and spaces
        clean = ''.join(
            c if (unicodedata.category(c) != 'Mn' and (c.isalnum() or c == ' '))
            else ''
            for c in nfd
        )
        # Collapse multiple spaces into one
        clean = ' '.join(clean.split())
        return clean.lower()
    except Exception as e:
        logger.warning(f"Normalization error: {e}")
        # Fallback: remove anything that's not ASCII alphanumeric/space
        result = ''.join(c if c.isalnum() or c == ' ' else '' for c in text.lower())
        return ' '.join(result.split())


def _prune_missing_fields(res: Dict[str, Any], query_text: str, conversation_history: list) -> Dict[str, Any]:
    """Remove missing_fields that were already answered in the query or history."""
    # Get the text blob - now returns already normalized text
    text_blob_norm = _text_blob_from_query_history(query_text, conversation_history, include_assistant=False)
    
    logger.info(f"LOG_PRUNE_START: text_blob_norm='{text_blob_norm[:200]}...', missing_fields_count={len(res.get('missing_fields', []))}")
    
    if not res.get("missing_fields"):
        return res
    
    # Clean up missing_fields to remove corrupted characters and emojis before processing
    cleaned_missing_fields = []
    for field in res.get("missing_fields", []):
        # Normalize the field - this removes corrupted UTF-8 sequences
        cleaned_field = _normalize_text(field)
        if cleaned_field.strip():  # Only keep non-empty fields
            cleaned_missing_fields.append(cleaned_field)
            logger.info(f"LOG_FIELD_CLEANUP: '{field[:50]}' → '{cleaned_field}'")
    
    logger.info(f"LOG_PRUNE_CLEANUP: After cleanup, {len(cleaned_missing_fields)} fields remaining")
    
    # Map of field keywords to text keywords that satisfy them
    field_satisfaction_map = {
        # Estado/Condición
        ("nuevo", "usado", "condicion"): ["nuevo", "usado", "seminuevo", "recondicionado"],
        # Tipo de Combustible (NOT cilindrada)
        ("tipo de motor", "combustible", "fuel"): ["gasolina", "diesel", "electrico", "electrica", "hibrido", "hibrida", "nafta"],
        # Cilindrada - SOLO detecta si hay número + unidad explícita
        ("cilindrada", "cm3", "cm³", "cc", "centimetros cubicos"): ["cc", "cm3", "cm³", "centimetros cubicos", "centímetros cúbicos", "cilindrada"],
        # Ejes
        ("eje", "ejes", "numero de ejes"): ["2 eje", "3 eje", "4 eje", "eje", "ejes", "trieje", "de eje"],
        # Puertas
        ("puerta", "puertas", "numero de puertas"): ["2 puerta", "3 puerta", "4 puerta", "5 puerta", "puerta", "puertas"],
        # Marca/Modelo
        ("marca", "modelo", "toyota", "ford", "volvo", "scania"): ["toyota", "ford", "volvo", "scania", "benz", "daimler", "hyundai", "chevrolet", "nissan", "hino", "isuzu"],
        # Peso/Capacidad
        ("peso", "tonelada", "capacidad", "carga", "kg"): ["tonelada", "ton", "kg", "kilogramo", "carga", "peso"],
        # Plazas/Pasajeros
        ("plaza", "plazas", "pasajero", "pasajeros", "persona", "personas", "asiento", "asientos"): ["plaza", "plazas", "pasajero", "pasajeros", "persona", "personas", "asiento", "asientos"],
        # Propósito/Uso
        ("proposito", "uso", "comercial", "particular"): ["comercial", "particular", "privado", "publico", "transporte", "domestico", "domestica", "industrial", "industria", "hogar"],
        # Material
        ("material", "madera", "metal", "plastico", "aluminio", "acero", "vidrio"): ["madera", "metal", "plastico", "plastica", "aluminio", "acero", "vidrio"],
        # CRÍTICO: Tipo de dispositivo (laptop vs desktop)
        ("portatil", "tipo de dispositivo", "tipo de computadora", "desktop", "escritorio"): ["laptop", "portatil", "notebook", "netbook", "desktop", "escritorio", "computadora de escritorio"],
    }
    
    # DETECCIÓN ESPECIAL: Cilindrada con número (ej: "6000 cc", "2500 cm3", "cilindrada de 3000")
    has_cilindrada_with_number = bool(re.search(r'\d{3,5}\s*(cc|cm3|cm³|centimetr)', text_blob_norm, re.IGNORECASE))
    
    cleaned = []
    for field_norm in cleaned_missing_fields:  # Use already-cleaned fields
        # CRÍTICO: Eliminar campos genéricos que el LLM devuelve por defecto
        # Estos son patrones que aparecen en los missing_fields pero el usuario ya respondió
        generic_patterns = [
            "tipo de mesa", "tipo de", "especifico",
            "dimensiones", "largo", "ancho", "alto", "tamano", "tamao",
            "descripcion", "descripcion precisa", "caracteristicas", "caracteristica",
            "informacion", "informacion adicional", "detalles", "detalle",
            "especificaciones", "especificacion",
        ]
        
        is_generic = any(pattern in field_norm for pattern in generic_patterns)
        
        # Si el usuario YA respondió sobre esto, eliminar el campo
        user_already_answered = False
        for pattern in generic_patterns:
            if pattern in field_norm and pattern in text_blob_norm:
                user_already_answered = True
                logger.info(f"LOG_PRUNE_FIELD: User already answered '{pattern}' - removing field '{field_norm}'")
                break

        # Regla específica: si el campo habla de "tipo de electrodoméstico" y el usuario ya mencionó
        # un electrodoméstico concreto (lavadora, refrigerador, etc.), no volver a preguntar.
        appliance_kws = [
            "lavadora", "refrigerador", "microonda", "microondas", "horno", "lavavajilla", "secadora",
            "licuadora", "batidora", "plancha", "aspiradora"
        ]
        mentions_appliance = any(kw in text_blob_norm for kw in appliance_kws)
        # También revisar la query actual normalizada por si el historial no llegó
        query_norm = _normalize_text(query_text)
        mentions_in_query = any(kw in query_norm for kw in appliance_kws)
        if "electrodom" in field_norm and (mentions_appliance or mentions_in_query):
            logger.info("LOG_PRUNE_FIELD: User already specified appliance; removing generic electrodomestico field")
            continue
        
        if is_generic and user_already_answered:
            continue
        
        # DETECCIÓN ESPECIAL: Si el campo es sobre cilindrada y detectamos número+unidad, eliminarlo
        if any(kw in field_norm for kw in ["cilindrada", "cm3", "cm³", "cc"]) and has_cilindrada_with_number:
            logger.info(f"LOG_PRUNE_FIELD: Removing cilindrada field - user provided number with units")
            continue
        
        # Check if this field has been satisfied by text_blob
        is_satisfied = False
        for field_keywords, satisfaction_keywords in field_satisfaction_map.items():
            # Check if field matches this category
            field_matches = any(kw in field_norm for kw in field_keywords)
            if field_matches:
                # Check if any satisfaction keyword is in text_blob
                is_satisfied = any(kw in text_blob_norm for kw in satisfaction_keywords)
                if is_satisfied:
                    logger.info(f"LOG_PRUNE_FIELD: Removing '{field_norm}' (field_keywords={field_keywords}) - satisfied in conversation")
                    break
        
        if not is_satisfied:
            cleaned.append(field_norm)
        else:
            logger.info(f"LOG_PRUNE_FIELD_REMOVED: '{field_norm}' - was satisfied")
    
    logger.info(f"LOG_PRUNE_END: cleaned={len(cleaned)} fields (from {len(cleaned_missing_fields)} after cleanup)")
    res["missing_fields"] = cleaned
    return res


def _rule_based_smartphone_candidate(text_blob: str) -> Optional[Dict[str, Any]]:
    """Return HS6 for smartphones/phones if the text indicates a cellular phone."""
    if not text_blob:
        return None

    config = _load_device_config()
    if not config or "smartphones" not in config:
        return None

    smartphone_config = config["smartphones"]
    kws = smartphone_config.get("keywords", [])
    exclude_kws = smartphone_config.get("exclude_keywords", [])

    if any(k in text_blob for k in exclude_kws):
        return None
    if not any(k in text_blob for k in kws):
        return None

    return {
        "code": smartphone_config.get("hs_code", "8517.13"),
        "description": smartphone_config.get("description", "Aparatos telefónicos para redes celulares u otras redes inalámbricas"),
        "confidence": smartphone_config.get("confidence", 0.82),
        "level": smartphone_config.get("level", "HS6"),
    }


def _rule_based_motorcycle_candidate(text_blob: str) -> Optional[Dict[str, Any]]:
    """Generate a basic motorcycle HS code based on keywords in the text."""
    if not text_blob:
        return None

    config = _load_device_config()
    if not config or "motorcycles" not in config:
        return None

    moto_config = config["motorcycles"]
    kws = moto_config.get("keywords", [])

    if not any(k in text_blob for k in kws):
        return None

    is_electric = any(k in text_blob for k in moto_config.get("electric_keyword", []))
    cc_val = None
    m = re.search(r"(\d{2,4})\s*cc", text_blob)
    if m:
        try:
            cc_val = int(m.group(1))
        except Exception:
            cc_val = None

    if is_electric:
        code = moto_config.get("electric_code", "8711.60")
        desc = moto_config.get("electric_description", "Motocicletas con motor eléctrico")
    else:
        if cc_val is None:
            code = moto_config.get("default_code", "8711.90")
            desc = moto_config.get("default_description", "Motocicletas; otras")
        else:
            # Buscar en los rangos de cilindrada
            code = moto_config.get("default_code", "8711.90")
            desc = moto_config.get("default_description", "Motocicletas; otras")
            for cc_range in moto_config.get("cc_ranges", []):
                min_cc = cc_range.get("min", 0)
                max_cc = cc_range.get("max")
                if max_cc is None:  # Último rango (sin límite superior)
                    if cc_val > min_cc:
                        code = cc_range.get("code", code)
                        desc = cc_range.get("description", desc)
                        break
                elif min_cc < cc_val <= max_cc:
                    code = cc_range.get("code", code)
                    desc = cc_range.get("description", desc)
                    break

    return {
        "code": code,
        "description": desc,
        "confidence": 0.72,
        "level": "HS6",
    }


def _apply_rule_based_fallback(res: Dict[str, Any], query: str, conversation_history: list | None) -> Dict[str, Any]:
    """If LLM didn't return candidates, try rule-based heuristic for motorcycles, appliances, vehicles, etc.
    SIEMPRE intenta generar candidatos tentatives si detecta palabras clave en la query."""
    blob = _text_blob_from_query_history(query, conversation_history, include_assistant=False)
    
    # Si el LLM no devolvió candidatos (o devolvió muy pocos), usar heurística
    current_candidates = res.get("top_candidates") or []
    if len(current_candidates) == 0:
        # Intenta smartphone
        phone_candidate = _rule_based_smartphone_candidate(blob)
        if phone_candidate:
            res["top_candidates"] = [phone_candidate]
            res["applied_rgi"] = res.get("applied_rgi") or ["RGI 1"]
            res.setdefault("warnings", []).append("Clasificación tentativa heurística: teléfono celular detectado (45% confianza).")
            return res
        
        # Intenta motocicleta
        moto_candidate = _rule_based_motorcycle_candidate(blob)
        if moto_candidate:
            res["top_candidates"] = [moto_candidate]
            res["applied_rgi"] = res.get("applied_rgi") or ["RGI 1"]
            res.setdefault("warnings", []).append("Clasificación tentativa heurística: motocicleta (45% confianza).")
            return res
        
        # Intenta electrodoméstico genérico (8450+ para lavadoras, etc.)
        appliance_kws = {
            "lavadora": ("8450.11", "Lavadora automática", 0.45),
            "refrigerador": ("8418.69", "Refrigerador doméstico", 0.40),
            "nevera": ("8418.69", "Refrigerador doméstico", 0.40),
            "microondas": ("8516.50", "Horno microondas", 0.45),
            "horno": ("8517.80", "Aparato de calefacción", 0.35),
            "lavavajillas": ("8422.11", "Lavavajillas", 0.45),
            "secadora": ("8450.20", "Secadora de ropa", 0.45),
            "aspiradora": ("8508.11", "Aspiradora", 0.45),
            "batidora": ("8509.40", "Batidora/Licuadora", 0.45),
            "licuadora": ("8509.40", "Licuadora", 0.45),
            "electrodomestico": ("8509.80", "Electrodoméstico (genérico)", 0.35),
        }
        
        for kw, (code, desc, conf) in appliance_kws.items():
            if kw in blob:
                res["top_candidates"] = [{
                    "code": code,
                    "description": desc,
                    "confidence": conf,
                    "level": "HS6"
                }]
                res["applied_rgi"] = res.get("applied_rgi") or ["RGI 1"]
                res.setdefault("warnings", []).append(f"Clasificación tentativa: {kw} (basada en palabras clave, {conf*100:.0f}% confianza).")
                logger.info(f"LOG_FALLBACK_APPLIANCE: Proposed {code} for '{kw}'")
                return res
        
        # Intenta vehículo genérico
        if any(v in blob for v in ["vehiculo", "vehículo", "auto", "carro", "camion", "camión", "bus"]):
            res["top_candidates"] = [{
                "code": "8703.21",
                "description": "Automóvil de gasolina (genérico)",
                "confidence": 0.35,
                "level": "HS6"
            }]
            res["applied_rgi"] = res.get("applied_rgi") or ["RGI 1"]
            res.setdefault("warnings", []).append("Clasificación tentativa: vehículo (basada en palabras clave, 35% confianza).")
            logger.info(f"LOG_FALLBACK_VEHICLE: Proposed 8703.21 for vehicle")
            return res
    
    return res


def _apply_device_overrides(res: Dict[str, Any], query: str, conversation_history: list | None) -> Dict[str, Any]:
    """Re-rank candidates for known device cases (e.g., smartphones vs. laptops)."""
    blob = _text_blob_from_query_history(query, conversation_history, include_assistant=False)
    phone_candidate = _rule_based_smartphone_candidate(blob)
    if not phone_candidate:
        return res
    # TODO: Implement phone re-ranking logic if needed
    return res


def _aggressive_missing_fields_cleanup(res: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Post-process missing_fields aggressively when we have sufficient classification.
    
    Strategy:
    - HS6+ (6+ digits) with confidence >= 75% → clear most missing_fields EXCEPT critical ones
    - HS4 (4 digits) with confidence >= 85% → clear most missing_fields EXCEPT critical ones
    - Critical fields (nuevo/usado for vehicles, etc.) are NEVER auto-removed
    - Otherwise, keep missing_fields for further refinement
    """
    candidates = res.get("top_candidates", [])
    if not candidates:
        return res
    
    top = candidates[0]
    confidence = float(top.get("confidence", 0))
    code = top.get("code", "")
    
    # Check digit count (remove dots/spaces)
    code_clean = code.replace(".", "").replace(" ", "")
    digit_count = len(code_clean)
    
    original_missing = res.get("missing_fields", [])
    logger.info(f"LOG_AGGRESSIVE_CLEANUP_BEFORE: code={code}, confidence={confidence:.0%}, digits={digit_count}, missing_count={len(original_missing)}, missing={original_missing}")
    
    # Determine if code is "refined enough"
    should_cleanup = False
    if digit_count >= 6 and confidence >= 0.75:
        # HS6 or more with 75%+ confidence
        should_cleanup = True
        logger.info(f"LOG_AGGRESSIVE_CLEANUP: HS{digit_count} code with {confidence:.0%} confidence → removing non-critical missing_fields")
    elif digit_count == 4 and confidence >= 0.85:
        # HS4 with very high confidence (85%+)
        should_cleanup = True
        logger.info(f"LOG_AGGRESSIVE_CLEANUP: HS4 code with {confidence:.0%} confidence (high) → removing non-critical missing_fields")
    
    if should_cleanup:
        # Define critical fields that should NEVER be auto-removed
        # These are fields that actually affect the tariff classification
        critical_patterns = [
            "nuevo", "usado", "new", "used",  # Vehicle condition - affects subheading
            "cilindrada", "cc", "cm3",  # Engine displacement - affects subheading for vehicles
            "nacional", "imported",  # Origin
        ]
        
        # Keep only critical fields
        kept_fields = []
        for field in original_missing:
            field_lower = field.lower()
            is_critical = any(pattern in field_lower for pattern in critical_patterns)
            if is_critical:
                kept_fields.append(field)
                logger.info(f"LOG_AGGRESSIVE_CLEANUP: Keeping critical field: '{field}'")
        
        original_count = len(original_missing)
        removed_count = original_count - len(kept_fields)
        res["missing_fields"] = kept_fields
        logger.info(f"LOG_AGGRESSIVE_CLEANUP_AFTER: Removed {removed_count} fields, kept {len(kept_fields)} critical fields")
    else:
        logger.info(f"LOG_AGGRESSIVE_CLEANUP: Keeping missing_fields (code={code}, confidence={confidence:.0%}, digits={digit_count})")
    
    return res


    existing = res.get("top_candidates") or []
    updated: List[Dict[str, Any]] = []
    has_phone = False

    for cand in existing:
        code_raw = str(cand.get("code") or cand.get("hs_code") or "")
        digits = re.sub(r"\D", "", code_raw)
        if digits.startswith("851713"):
            has_phone = True
            # Keep the LLM candidate but prefer the heuristic confidence if higher
            merged = cand.copy()
            if merged.get("confidence", 0) < phone_candidate["confidence"]:
                merged["confidence"] = phone_candidate["confidence"]
            merged.setdefault("description", phone_candidate["description"])
            merged.setdefault("level", "HS6")
            updated.append(merged)
            continue
        # Drop computer/laptop misclassifications when it's clearly a phone
        if digits.startswith("8471"):
            logger.info("LOG_OVERRIDE_PHONE: dropped 8471 candidate because query implies smartphone")
            continue
        updated.append(cand)

    if not has_phone:
        updated.insert(0, phone_candidate)
        res.setdefault("warnings", []).append("Ajuste heurístico: se prioriza 8517.13 para teléfonos celulares detectados en el texto.")
    else:
        # Ensure phone is top-ranked
        updated = [c for c in updated if re.sub(r"\D", "", str(c.get("code") or c.get("hs_code") or ""))[:6] == "851713"] + [c for c in updated if re.sub(r"\D", "", str(c.get("code") or c.get("hs_code") or ""))[:6] != "851713"]

    res["top_candidates"] = updated
    res.setdefault("applied_rgi", [])
    if "RGI 1" not in res["applied_rgi"]:
        res["applied_rgi"].append("RGI 1")
    return res


def _calculate_confidence_from_details(blob: str, code: str, missing_fields_original: List[str]) -> float:
    """Calcula confianza basada en detalles proporcionados en la conversación.
    
    Estrategia:
    - Base: 0.35 (muy poco info, solo detección de categoría)
    - +0.10 por cada detalle crítico respondido
    - Ajuste por missing_fields: cuantos menos campos falten, más confianza
    - Escala:
      * 0.35: Solo categoría identificada
      * 0.45: Categoría + 1 detalle
      * 0.55: Categoría + 2-3 detalles
      * 0.65: Categoría + 4 detalles
      * 0.75: Categoría + 5+ detalles + pocos campos faltantes
      * 0.85: Categoría + 5+ detalles + 1 campo faltante
      * 0.95: Todos los detalles + cero campos faltantes (HS10 ready)
    - Máximo: 0.95
    """
    import logging
    logger = logging.getLogger(__name__)
    
    base_confidence = 0.35
    
    # Si no hay campos faltantes, máxima confianza
    if not missing_fields_original or len(missing_fields_original) == 0:
        logger.info(f"[CONFIDENCE_CALC] No missing fields → confidence=0.95 (HS10 ready)")
        return 0.95
    
    # Contar cuántos detalles críticos se han respondido
    critical_details = {
        "capacidad": ["kg", "litro", "watt", "btu", "l"],
        "tipo": ["frontal", "superior", "diesel", "gasolina", "eléctrico", "hibrido"],
        "nuevo": ["nuevo", "usado", "seminuevo"],
        "voltaje": ["220", "110", "127", "50hz", "60hz"],
        "uso": ["doméstico", "industrial", "comercial"],
        "cilindrada": ["cc", "cm3", "centimetro", "cilindrada"],
        "plazas": ["pasajero", "personas", "plaza", "asiento"],
        "motor": ["diesel", "gasolina", "eléctrico", "nafta"],
        "secado": ["secado", "secadora", "ropa seca"],
        "carga": ["carga frontal", "carga superior", "carga superior"],
    }
    
    answered_details = 0
    for detail_type, keywords in critical_details.items():
        blob_lower = blob.lower()
        if any(kw in blob_lower for kw in keywords):
            answered_details += 1
    
    # Ajuste por completitud: cuantos más campos falten, menos confianza
    fields_remaining = len(missing_fields_original)
    
    # Escala más granular:
    # Base (0.35) + detalles (0.10 cada uno, máx 0.50) + ajuste por completitud
    confidence = base_confidence + min(answered_details * 0.10, 0.50)
    
    # Penalizar por campos faltantes
    if fields_remaining > 5:
        confidence *= 0.70  # Muchos campos faltantes → máx 0.35+0.35=0.70
    elif fields_remaining > 3:
        confidence *= 0.85  # Algunos campos → máx ≈0.65
    elif fields_remaining > 1:
        confidence *= 0.95  # Pocos campos (1-3) → máx ≈0.80
    # else: 0 campos faltantes (ya manejado arriba con 0.95)
    
    # Cap en 0.95
    final_confidence = min(0.95, max(0.35, confidence))
    
    logger.info(
        f"[CONFIDENCE_CALC] answered_details={answered_details}, "
        f"fields_remaining={fields_remaining}, confidence={final_confidence:.2f}"
    )
    
    return final_confidence


def _refine_hs_code_from_details(code: str, blob: str, level: str) -> tuple:
    """Refina HS6 a HS8/HS10 basado en detalles específicos.
    
    Soporta:
    - Lavadoras: 8450.11.10 (nueva) / 8450.11.90 (usada)
    - Vehículos: 8702/8703/8704 + cilindrada + nuevo/usado → HS10
    - Retorna (refined_code, new_level)
    
    Niveles:
    - HS6: 6 dígitos (XXXXXX)
    - HS8: 8 dígitos (XXXXXX.YY) 
    - NANDINA8: 8 dígitos con código de país
    - NATIONAL10: 10 dígitos (XXXXXX.YY.ZZ) con máxima precisión
    """
    import logging
    import re
    logger = logging.getLogger(__name__)
    
    code_clean = code.replace(".", "").replace(" ", "").upper()
    blob_lower = blob.lower()
    
    if not code_clean or len(code_clean) < 6:
        return code, level
    
    # ======= LAVADORAS (Capítulo 84, Código 8450) =======
    if code_clean.startswith("845011"):
        is_new = "nueva" in blob_lower or "nuevo" in blob_lower
        is_old = "usado" in blob_lower or "usada" in blob_lower
        
        if is_new:
            logger.info(f"[REFINE_LAVADORA] Nueva → 8450.11.10 (NANDINA8)")
            return "8450.11.10", "NANDINA8"
        elif is_old:
            logger.info(f"[REFINE_LAVADORA] Usada → 8450.11.90 (NANDINA8)")
            return "8450.11.90", "NANDINA8"
        # Si no especifica estado, devuelve HS6 original
    
    # ======= VEHÍCULOS (Capítulo 87: 8702=Bus, 8703=Auto, 8704=Camión) =======
    elif code_clean.startswith(("8702", "8703", "8704")):
        # Extraer cilindrada
        cilindrada_match = re.search(r'(\d{3,5})\s*(cc|cm3|cm²)', blob_lower)
        cilindrada = int(cilindrada_match.group(1)) if cilindrada_match else None
        
        is_new = "nueva" in blob_lower or "nuevo" in blob_lower
        is_old = "usado" in blob_lower or "usada" in blob_lower
        
        logger.info(
            f"[REFINE_VEHICULO] code={code}, cilindrada={cilindrada}, "
            f"is_new={is_new}, is_old={is_old}"
        )
        
        # Si tenemos cilindrada, refinar a HS10 (máxima precisión)
        if cilindrada and len(code_clean) == 6:
            # Usar código limpio (sin puntos)
            base_clean = code_clean[:6]  # ej: "870321"
            base_formatted = f"{base_clean[:4]}.{base_clean[4:6]}"  # ej: "8703.21"
            
            # Determinar subcode basado en cilindrada
            # Para autos/camiones/buses, los rangos típicos son:
            # .10 = ≤ 1500 cc (pequeño)
            # .20 = 1500-3000 cc (mediano)
            # .90 = > 3000 cc (grande)
            
            if cilindrada <= 1500:
                subcode = "10"
            elif cilindrada <= 3000:
                subcode = "20"
            else:
                subcode = "90"
            
            refined = f"{base_formatted}.{subcode}"
            logger.info(
                f"[REFINE_VEHICULO_SUCCESS] {code} + {cilindrada}cc → {refined} (NATIONAL10)"
            )
            return refined, "NATIONAL10"
        
        # Si tenemos estado pero no cilindrada, refinar a HS8
        elif (is_new or is_old) and len(code_clean) == 6:
            base_clean = code_clean[:6]
            base_formatted = f"{base_clean[:4]}.{base_clean[4:6]}"
            
            if is_new:
                refined = f"{base_formatted}.10"
                logger.info(f"[REFINE_VEHICULO_NEW] {code} + nuevo → {refined} (NANDINA8)")
                return refined, "NANDINA8"
            elif is_old:
                refined = f"{base_formatted}.90"
                logger.info(f"[REFINE_VEHICULO_USED] {code} + usado → {refined} (NANDINA8)")
                return refined, "NANDINA8"
    
    # ======= ELECTRODOMÉSTICOS GENÉRICOS (Capítulo 85, Código 8509) =======
    elif code_clean.startswith("8509"):
        if "lavadora" in blob_lower:
            logger.info(f"[REFINE_GENERIC_APPLIANCE] 8509.80 + lavadora → 8450.11 (HS6)")
            return "8450.11", "HS6"
        elif "refrigerador" in blob_lower or "nevera" in blob_lower:
            logger.info(f"[REFINE_GENERIC_APPLIANCE] 8509.80 + refrigerador → 8418.69 (HS6)")
            return "8418.69", "HS6"
        elif "microondas" in blob_lower:
            logger.info(f"[REFINE_GENERIC_APPLIANCE] 8509.80 + microondas → 8516.50 (HS6)")
            return "8516.50", "HS6"
    
    # No hay cambios
    return code, level





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
        logger.info(f"Historial recibido: {len(conversation_history)} turnos")
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
                history_lines.append(f"  Usuario: {user_msg}")
                # Truncar respuesta larga del asistente - extraer solo el código propuesto
                assistant_short = assistant_msg[:200] if len(assistant_msg) > 200 else assistant_msg
                history_lines.append(f"  Asistente propuso: {assistant_short}...")
        if history_lines:
            history_text = "\n".join(history_lines)

    # Detectar si es un refinamiento (pregunta corta después de una clasificación)
    is_refinement = False
    if conversation_history and len(conversation_history) > 0:
        # Extraer el mensaje del último turno
        last_turn = conversation_history[-1]
        last_user_msg = None
        if isinstance(last_turn, dict):
            last_user_msg = last_turn.get("user", "")
        elif isinstance(last_turn, (list, tuple)) and len(last_turn) >= 1:
            last_user_msg = last_turn[0]
        
        # REFINAMIENTO: Query corto (<60 caracteres) Y hay historial previo con clasificaciones
        # - Si hay cualquier turno anterior, asumimos que esta es una continuación/refinamiento
        # - Especialmente si el query es corto (probablemente es "es usado", "de 1 tonelada", etc.)
        if len(query) < 60 and last_user_msg:
            is_refinement = True
            logger.info(f"LOG_REFINEMENT_DETECTED: '{query}' (len={len(query)}) refines previous turn: '{last_user_msg[:60]}...'")

    # PROMPT MEJORADO CON CONTEXTO
    has_context = context_text.strip() != ""
    
    if has_context:
        # CON DOCUMENTOS: PROPONER CÓDIGOS
        # Agregar instrucción especial si es refinamiento y el tema es claramente vehículos
        refinement_instruction = ""
        priority_guidance = ""
        
        # CRÍTICO: Construir texto completo del usuario para detectar contexto (incluyendo "laptop", "portátil", etc.)
        all_user_text = query.lower()
        all_assistant_text = ""
        if conversation_history:
            for turn in conversation_history:
                if isinstance(turn, dict):
                    all_user_text += " " + str(turn.get("user", "")).lower()
                    all_assistant_text += " " + str(turn.get("assistant", "")).lower()
                elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                    all_user_text += " " + str(turn[0]).lower()
                    all_assistant_text += " " + str(turn[1]).lower()
        
        if is_refinement and history_text:
            q_low = (query or "").lower()
            # Detectar el capítulo del último código propuesto
            last_chapter = None
            last_code_match = re.search(r'\b(8[0-9]{3}|[0-9]{4})\b', all_assistant_text[::-1])  # Buscar de atrás hacia adelante
            if last_code_match:
                last_code_str = last_code_match.group(1)[::-1]  # Revertir porque buscamos al revés
                last_chapter = last_code_str[:2]
            
            logger.info(f"LOG_REFINEMENT_CONTEXT: last_chapter={last_chapter}, query='{query[:40]}'")
            
            # INSTRUCCIÓN GENERAL: Mantener el capítulo anterior
            if last_chapter:
                refinement_instruction = f"""
CONTEXTO ANTERIOR (para refinamiento):
{history_text}

INSTRUCCIÓN CRÍTICA: El usuario está REFINANDO la consulta anterior.
- El último código propuesto fue del CAPÍTULO {last_chapter}
- Esta nueva información ("{query}") es un DETALLE ADICIONAL del mismo producto
- NO cambies de capítulo a menos que el usuario mencione explícitamente un producto diferente
- Mantén la clasificación en el capítulo {last_chapter} y refina con subdivisiones si corresponde

EJEMPLOS DE REFINAMIENTO (NO son cambio de producto):
- Usuario pregunta por "lavadora" → responde "es de carga frontal" → Sigue siendo lavadora (8450)
- Usuario pregunta por "vehículo" → responde "es para carga" → Sigue siendo vehículo del capítulo apropiado
- Usuario pregunta por "acero" → responde "espesor 5mm" → Sigue siendo acero (capítulo 72/73)
"""
                
            # GUÍA ESPECÍFICA SOLO PARA VEHÍCULOS (capítulo 87) por su complejidad
            vehicle_terms = ["vehiculo", "vehículo", "vehiculos", "vehículos", "camion", "camión", "camioneta", "pickup", "remolque", "semirremolque", "bus", "autobus", "autobús", "microbus", "microbús", "tractor"]
            vehicle_context = any(t in all_user_text for t in vehicle_terms) or last_chapter == "87"
            
            if vehicle_context and last_chapter == "87":
                # Agregar guía específica para vehículos (subdivisiones complejas)
                refinement_instruction += """

GUÍA ESPECÍFICA PARA VEHÍCULOS (Capítulo 87):
- 8702: Autobuses (≥10 plazas)
- 8703: Automóviles de turismo (<10 plazas)
- 8704: Camiones y vehículos de carga (peso define subdivisión: .21 ≤5t, .22 5-20t, .23 >20t)
- 8716: Remolques (SOLO si menciona explícitamente "remolque" o "semirremolque")

Si el usuario proporciona peso/capacidad/plazas, ajusta la SUBDIVISIÓN (.21, .22, etc.) pero mantén el código base correcto.
"""
        
        # DETECCIÓN ESPECIAL: Laptops/Portátiles (evitar confusión con tablets)
        laptop_keywords = ["laptop", "portatil", "portátil", "notebook", "netbook"]
        has_laptop_context = any(kw in all_user_text for kw in laptop_keywords)
        laptop_guidance = ""
        if has_laptop_context:
            laptop_guidance = """\n\n🔴 CONTEXTO CRÍTICO DETECTADO:
El usuario YA MENCIONÓ que es una LAPTOP/COMPUTADORA PORTÁTIL.
- NO preguntes "¿Es portátil o de escritorio?"
- NO preguntes "¿Qué tipo de dispositivo?"
- Clasifica directamente en 8471.30 (máquinas portátiles de procesamiento de datos)
- Si proporciona specs adicionales (RAM, procesador, etc.), mantén 8471.30 y NO pidas información redundante
"""
        
        prompt = f"""Eres experto en aranceles HS. Tu tarea es clasificar productos según el Sistema Armonizado.

{refinement_instruction}
{laptop_guidance}

HISTORIAL CONVERSACIONAL (LÉELO TODO):
{history_text if history_text else "(No hay historial previo)"}

DOCUMENTOS ENCONTRADOS:
{context_text}

NUEVA CONSULTA DEL USUARIO: {query}

{priority_guidance}

REGLAS PARA PROPONER CÓDIGOS:
- Si la consulta es GENÉRICA SIN DETALLES (ej: "¿Partida de vehículos?", "¿Qué es...?"), propón el CÓDIGO BASE HS6 (8703, 8704, etc)
- Si la consulta INCLUYE DETALLES ESPECÍFICOS (peso, capacidad, año, especificaciones), PUEDES proponer SUBDIVISIONES (8703.21, 8704.22, etc.)
- Ejemplos:
  * "¿Partida de vehículos?" → Propón 8703 (código base, pregunta genérica)
  * "Camión de 3 toneladas" → PUEDES proponer 8704.21 (hay especificación de peso)
  * "Automóvil a gasolina" → PUEDES proponer 8703.10 (hay especificación de motor)

TAREA: 
1. Propón 1-2 códigos HS6 basado en los documentos recuperados
2. Explica brevemente por qué
3. Pregunta 2-3 campos faltantes para refinar la clasificación

RESPUESTA EN JSON:
{{"top_candidates": [{{"code": "XXXXXX", "description": "Descripción breve", "confidence": 0.75, "level": "HS6"}}], "inclusions": ["Incluye X"], "exclusions": ["Excluye Y"], "applied_rgi": ["RGI 1"], "missing_fields": ["¿Campo 1?", "¿Campo 2?"], "warnings": []}}"""
        logger.info(f"LOG_PROMPT: Refinement={is_refinement}, Context_len={len(context_text)}, Query={query[:80]}")
    else:
        # SIN DOCUMENTOS: NO PROPONER, PEDIR INFO
        prompt = f"""Eres experto en aranceles HS.

NO HAY DOCUMENTOS ENCONTRADOS.

USUARIO PREGUNTA: {query}

TAREA: No propongas códigos. Pide información específica en missing_fields para poder buscar.

RESPUESTA (JSON):
{{"top_candidates": [], "missing_fields": ["¿...?", "¿...?"], "warnings": ["Información insuficiente"]}}"""
        logger.info(f"LOG_PROMPT_SIN_CONTEXTO. Query: {query[:80]}")

    # CALL AZURE OPENAI LLM
    s = get_settings()
    logger.info(f"LOG_TRY_AZURE: endpoint={s.azure_openai_endpoint}, key_set={bool(s.azure_openai_key)}, deploy={s.azure_openai_chat_deployment}")
    
    if not (s.azure_openai_endpoint and s.azure_openai_key and s.azure_openai_chat_deployment):
        logger.warning(f"LOG_TRY_AZURE: Skipped - missing config")
        # Fallback sin LLM
        offline = _offline_result(evidence=context_docs, reason="LLM offline o sin cuota disponible (Azure)")
        offline = _apply_rule_based_fallback(offline, query, conversation_history)
        offline = _apply_device_overrides(offline, query, conversation_history)
        offline = _prune_missing_fields(offline, query, conversation_history)
        return _ensure_missing_fields(offline, query, conversation_history)
    
    try:
        client = AzureOpenAI(
            api_key=s.azure_openai_key,
            azure_endpoint=s.azure_openai_endpoint,
            api_version=s.azure_openai_api_version,
        )
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
        logger.info(f"LOG_LLM_RESPONSE: {choice[:200]}")
        parsed = json.loads(choice or "{}")
        logger.info(f"LOG_LLM_PARSED: top_candidates={len(parsed.get('top_candidates', []))} items")
        
        # Normalizar y procesar respuesta
        norm = _normalize_result_fields(parsed, evidence)
        norm = _apply_device_overrides(norm, query, conversation_history)
        norm = _prune_missing_fields(norm, query, conversation_history)
        norm = _apply_rule_based_fallback(norm, query, conversation_history)
        norm = _apply_device_overrides(norm, query, conversation_history)
        norm = _aggressive_missing_fields_cleanup(norm, query)
        norm = _ensure_missing_fields(norm, query, conversation_history)
        
        # Refinar confianza y códigos basados en detalles respondidos
        blob = _text_blob_from_query_history(query, conversation_history, include_assistant=False)
        candidates = norm.get("top_candidates") or []
        if candidates:
            top_cand = candidates[0]
            original_mf = norm.get("missing_fields") or []
            
            # Recalcular confianza basada en detalles
            new_confidence = _calculate_confidence_from_details(blob, top_cand.get("code"), original_mf)
            top_cand["confidence"] = new_confidence
            logger.info(f"LOG_CONFIDENCE_REFINED: {top_cand.get('code')} → {new_confidence:.0%}")
            
            # Refinar código a HS8/HS10 si hay detalles
            original_code = top_cand.get("code")
            original_level = top_cand.get("level", "HS6")
            refined_code, refined_level = _refine_hs_code_from_details(original_code, blob, original_level)
            if refined_code != original_code:
                top_cand["code"] = refined_code
                top_cand["level"] = refined_level
                logger.info(f"LOG_CODE_REFINED: {original_code} ({original_level}) → {refined_code} ({refined_level})")

            # PRESERVAR EL CÓDIGO MÁS ESPECÍFICO DEL HISTORIAL PARA EVITAR REGRESIONES
            try:
                prev_code = None
                if conversation_history:
                    # Buscar el último código propuesto por el asistente en el historial
                    for turn in reversed(conversation_history):
                        if isinstance(turn, dict):
                            prev_code = turn.get("assistant") or prev_code
                        elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                            prev_code = turn[1] or prev_code
                        if prev_code:
                            break
                if prev_code:
                    # Normalizar y comparar especificidad (cantidad de dígitos sin puntos)
                    import re as _re
                    def _digits(c: str):
                        return ''.join(_re.findall(r"\d", c or ""))
                    prev_digits = _digits(prev_code)
                    curr_digits = _digits(top_cand.get("code") or "")
                    # Si pertenecen al mismo capítulo y el previo es más largo (más específico), conservarlo
                    if prev_digits[:4] == curr_digits[:4] and len(prev_digits) > len(curr_digits):
                        logger.info(f"LOG_PRESERVE_SPECIFIC: Keeping previous more specific code {prev_code} over {top_cand.get('code')}")
                        top_cand["code"] = prev_code
                        # Ajustar nivel según longitud
                        if len(prev_digits) >= 10:
                            top_cand["level"] = "NATIONAL10"
                        elif len(prev_digits) >= 8:
                            top_cand["level"] = "NANDINA8"
                        else:
                            top_cand["level"] = "HS6"
                        # Recalcular confianza tras preservación
                        top_cand["confidence"] = _calculate_confidence_from_details(blob, top_cand["code"], original_mf)
            except Exception as _e:
                logger.warning(f"LOG_PRESERVE_SPECIFIC_FAILED: {_e}")
        
        logger.info(f"LOG_LLM_FINAL: top_candidates={len(norm.get('top_candidates', []))} items")
        return norm
    except Exception as e:
        logger.error(f"LOG_ERROR_AZURE: {e}")
        import traceback
        logger.error(f"LOG_TRACEBACK: {traceback.format_exc()}")
        # Fallback sin LLM
        offline = _offline_result(evidence=context_docs, reason=f"Error en Azure OpenAI: {e}")
        offline = _apply_rule_based_fallback(offline, query, conversation_history)
        offline = _apply_device_overrides(offline, query, conversation_history)
        offline = _prune_missing_fields(offline, query, conversation_history)
        return _ensure_missing_fields(offline, query, conversation_history)


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
