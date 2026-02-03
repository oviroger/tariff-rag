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

_MATERIALS_CONFIG_PATH = Path(__file__).parent / "materials_keywords.json"
_MATERIALS_CONFIG: Dict[str, Any] = {}


def _load_materials_keywords() -> Dict[str, Any]:
    """Carga materiales y recubrimientos desde app/materials_keywords.json"""
    global _MATERIALS_CONFIG
    if _MATERIALS_CONFIG:
        return _MATERIALS_CONFIG
    try:
        if _MATERIALS_CONFIG_PATH.exists():
            with open(_MATERIALS_CONFIG_PATH, "r", encoding="utf-8") as f:
                _MATERIALS_CONFIG = json.load(f)
            logger.info(f"Materials keywords loaded from {_MATERIALS_CONFIG_PATH}")
        else:
            logger.warning(f"Materials keywords file not found: {_MATERIALS_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Error loading materials_keywords.json: {e}")
        _MATERIALS_CONFIG = {}
    return _MATERIALS_CONFIG


# Category keywords and missing_fields templates (data-driven)
_CATEGORY_CONFIG_PATH = Path(__file__).parent / "category_keywords.json"
_CATEGORY_CONFIG: Dict[str, Any] = {}

_MISSING_FIELDS_TEMPLATES_PATH = Path(__file__).parent / "missing_fields_templates.json"
_MISSING_FIELDS_TEMPLATES: Dict[str, Any] = {}


def _load_category_keywords() -> Dict[str, Any]:
    global _CATEGORY_CONFIG
    if _CATEGORY_CONFIG:
        return _CATEGORY_CONFIG
    try:
        if _CATEGORY_CONFIG_PATH.exists():
            with open(_CATEGORY_CONFIG_PATH, "r", encoding="utf-8") as f:
                _CATEGORY_CONFIG = json.load(f)
            logger.info(f"Category keywords loaded from {_CATEGORY_CONFIG_PATH}")
        else:
            logger.warning(f"Category keywords file not found: {_CATEGORY_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Error loading category_keywords.json: {e}")
        _CATEGORY_CONFIG = {}
    return _CATEGORY_CONFIG


def _load_missing_fields_templates() -> Dict[str, Any]:
    global _MISSING_FIELDS_TEMPLATES
    if _MISSING_FIELDS_TEMPLATES:
        return _MISSING_FIELDS_TEMPLATES
    try:
        if _MISSING_FIELDS_TEMPLATES_PATH.exists():
            with open(_MISSING_FIELDS_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                _MISSING_FIELDS_TEMPLATES = json.load(f)
            logger.info(f"Missing fields templates loaded from {_MISSING_FIELDS_TEMPLATES_PATH}")
        else:
            logger.warning(f"Missing fields templates file not found: {_MISSING_FIELDS_TEMPLATES_PATH}")
    except Exception as e:
        logger.error(f"Error loading missing_fields_templates.json: {e}")
        _MISSING_FIELDS_TEMPLATES = {}
    return _MISSING_FIELDS_TEMPLATES


def _get_critical_fields_for_code(code: str) -> List[str]:
    """Dynamically get critical field keywords based on HS code and templates.
    
    This replaces hardcoded critical_patterns with data-driven approach from JSON.
    
    Args:
        code: HS code (e.g., "5208.51", "8703.10", "7208.90")
    
    Returns:
        List of critical field keywords that should never be auto-removed for this code
    """
    templates = _load_missing_fields_templates()
    critical_fields = templates.get("critical_fields", {})
    
    code_str = str(code).replace(".", "").replace(" ", "")
    critical_keywords = []
    
    # Check which category matches this code
    for category, config in critical_fields.items():
        if category == "code_patterns":
            continue
        
        patterns = config.get("code_patterns", [])
        for pattern in patterns:
            if code_str.startswith(pattern):
                critical_keywords.extend(config.get("critical_keywords", []))
                logger.debug(f"LOG_CRITICAL_FIELDS: Code {code} matches pattern {pattern} in category {category}")
                break
    
    # Always include universal critical patterns
    universal_critical = ["nuevo", "usado", "new", "used", "nacional", "imported", "condicion"]
    critical_keywords.extend(universal_critical)
    
    return list(set(critical_keywords))  # Remove duplicates


def _is_terminal_hs_code(code: str) -> bool:
    """Detecta si un código HS ya está en nivel terminal sin subpartidas HS10.
    
    Códigos TERMINALES = No hay subpartidas HS10 adicionales disponibles
    Ejemplo: 0808.10 (manzanas frescas) es terminal en HS8
    
    Esto ayuda a identificar cuándo la falta de progresión es por limitación estructural,
    no por problema del algoritmo.
    
    Args:
        code: HS code (e.g., "0808.10", "8702.20")
    
    Returns:
        True si es terminal, False si hay más niveles disponibles
    """
    # Mapa de capítulos y su nivel terminal esperado
    chapter = str(code)[:2]
    
    # Capítulos que son terminales en HS8 (no tienen HS10 discriminante)
    terminal_chapters = {
        "08": {"terminal_level": "HS8", "reason": "Frutas: no hay subpartidas HS10 adicionales"},
        "02": {"terminal_level": "HS8", "reason": "Carnes: terminal temprano"},
        "03": {"terminal_level": "HS8", "reason": "Pescado: muy específico al HS8"},
        "09": {"terminal_level": "HS8", "reason": "Café, té: terminal en HS8"},
    }
    
    if chapter in terminal_chapters:
        return True
    
    return False


def _default_missing_fields(blob: str, conversation_history: list | None = None) -> List[str]:
    """Fallback inteligente cuando el LLM no tiene documentos o falla.
    
    Estrategia:
    - Detecta CATEGORÍAS AMPLIAS (no códigos específicos)
    - Hace preguntas GENERALES para ayudar a especificar
    - NO asume clasificaciones finales
    - El LLM+RAG manejará la clasificación real cuando tenga documentos
    - IMPORTANTE: También verifica el historial para evitar re-preguntar
    - CRÍTICO: Valida que la categoría del historial sea consistente
    
    Este fallback SOLO se usa cuando no hay documentos RAG disponibles.
    """
    b = (blob or "").lower()
    
    # Reconstruir el texto del historial para detectar qué se mencionó previamente
    history_text = _text_blob_from_query_history("", conversation_history or [], include_assistant=False).lower()
    combined_context = f"{b} {history_text}"
    
    # ✅ CRÍTICO PRIMERO: Detectar categoría CLARA del historial
    # Si el historial CLARAMENTE habla de una categoría, usar ESA, no mezclar con vehiculos
    history_is_laptop = any(
        kw in history_text 
        for kw in ["laptop", "portátil", "computadora", "notebook", "dell", "xps", "ssd", "ram", "gb", "procesador", "computadora portátil", "almacenamiento", "procesamiento", "datos", "cpu", "i9", "ryzen"]
    )
    history_is_electrodomestico = any(
        kw in history_text 
        for kw in ["lavadora", "automática", "carga frontal", "microondas", "microonda", "horno de microondas"]
    )
    
    logger.info(f"LOG_DEFAULT_MISSING_FIELDS: history_is_laptop={history_is_laptop}, history_text={history_text[:100]}")
    
    # Si hay categoría CLARA en el historial, ignorar palabras clave conflictivas en blob
    if history_is_laptop:
        # Suprimir cualquier detección de vehículos cuando sabemos que es laptop
        combined_context_for_detection = b  # SOLO usar blob, NO history con vehículos confusos
        logger.info(f"LOG_DEFAULT_MISSING_FIELDS: IGNORING history for vehicle detection - detected LAPTOP")
    elif history_is_electrodomestico:
        # Suprimir cualquier detección de vehículos cuando sabemos que es electrodoméstico
        combined_context_for_detection = b
        logger.info(f"LOG_DEFAULT_MISSING_FIELDS: IGNORING history for vehicle detection - detected ELECTRODOMESTICO")
    else:
        # Usar contexto combinado (hay ambigüedad)
        combined_context_for_detection = combined_context
        logger.info(f"LOG_DEFAULT_MISSING_FIELDS: Using combined context")
    
    # Computadoras/Electrónica - Pedir especificación SIN asumir tipo
    if any(kw in combined_context for kw in ["computadora", "computador", "ordenador", "pc", "equipo de computo", "equipo informático", "informática"]):
        return [
            "¿Qué tipo de computadora es? (portátil/laptop, escritorio/desktop, tablet, servidor, todo en uno, etc.)",
            "¿Es nueva o usada?"
        ]
    
    # Dispositivos electrónicos portátiles ya especificados
    if any(kw in combined_context for kw in ["laptop", "notebook", "portátil", "portatil"]):
        return ["¿Es nueva o usada?"]
    
    # Teléfonos - Pedir especificación SIN asumir tipo
    if any(kw in combined_context for kw in ["telefono", "teléfono", "celular", "móvil", "movil", "smartphone", "iphone", "android"]):
        return [
            "¿Qué tipo? (teléfono inteligente/smartphone, teléfono básico, teléfono fijo, etc.)",
            "¿Es nuevo o usado?"
        ]
    
    # Vehículos - Preguntas críticas basadas en lo que ya se sabe
    # PERO: Solo si NO hay categoría clara de laptop/electrodoméstico
    category_cfg = _load_category_keywords() or {}
    vehicle_syns = set(_normalize_text(str(s)) for s in (category_cfg.get("vehicles", {}).get("synonyms", []) or []))
    vehicle_type_syns = set(_normalize_text(str(s)) for s in (category_cfg.get("vehicle_types", []) or []))

    normalized_combined_for_detection = _normalize_text(combined_context_for_detection)

    if vehicle_syns and any(kw in normalized_combined_for_detection for kw in vehicle_syns) or (not vehicle_syns and any(kw in combined_context_for_detection for kw in ["vehiculo", "vehículo", "auto", "automóvil", "carro", "coche", "camion", "camión", "camioneta", "bus", "autobus", "autobús", "microbus", "microbús", "moto", "motocicleta"])):
        questions = []

        # Preguntar tipo específico si es genérico "vehículo"
        if "vehiculo" in normalized_combined_for_detection:
            if not any(spec in normalized_combined_for_detection for spec in (vehicle_type_syns or ["auto", "automóvil", "automovil", "camion", "camión", "bus", "moto"])):
                questions.append("¿Qué tipo de vehículo específico? (automóvil, camioneta, camión, bus, motocicleta)")

        # Preguntar cuántas personas/plazas (crítico para 8702 vs 8703)
        if not any(kw in normalized_combined_for_detection for kw in ["persona", "personas", "plaza", "plazas", "pasajero", "pasajeros", "asiento", "asientos"]):
            questions.append("¿Cuántas personas puede transportar? (esto determina si es autobús ≥10 plazas u automóvil <10 plazas)")

        # Preguntar tipo de motor
        if not any(kw in normalized_combined_for_detection for kw in ["gasolina", "diesel", "diesel", "electrico", "electrico", "hibrido"]):
            questions.append("¿Qué tipo de motor? (gasolina, diesel, eléctrico, híbrido)")

        # Preguntar nuevo/usado
        if not any(kw in normalized_combined_for_detection for kw in ["nuevo", "nueva", "usado", "usada", "seminuevo", "segunda mano"]):
            questions.append("¿Es nuevo o usado?")

        return questions if questions else ["Por favor proporciona más detalles sobre el vehículo"]
    
    # MICROONDAS - Si se mencionó "microondas", hacer preguntas ESPECÍFICAS para microondas
    if any(kw in combined_context for kw in ["microondas", "microonda", "horno microonda", "horno de microondas"]):
        questions = []
        
        # Preguntar capacidad/litros si no se menciona
        if not any(kw in combined_context for kw in ["litro", "litros", "l", "capacidad"]):
            questions.append("¿Cuál es la capacidad en litros?")
        
        # Preguntar si tiene función de convección (ya mencionada en Turno 1, así que se prueba)
        # Si ya se mencionó, se elimina en prune_missing_fields
        if not any(kw in combined_context for kw in ["conveccion", "convección", "grill"]):
            questions.append("¿Tiene funciones adicionales como convección o grill?")
        
        # Preguntar nuevo/usado
        if not any(kw in combined_context for kw in ["nuevo", "nueva", "usado", "usada", "seminuevo", "recondicionado"]):
            questions.append("¿Es nuevo o usado?")
        
        return questions if questions else ["Microondas completamente especificado"]
    
    # Electrodomésticos - Pedir especificación si es genérico
    if any(kw in combined_context for kw in ["electrodomestico", "electrodoméstico", "aparato"]) and not any(kw in combined_context for kw in ["lavadora", "refrigerador", "microondas", "microonda", "horno"]):
        return [
            "¿Qué electrodoméstico específico? (lavadora, refrigerador, microondas, etc.)",
            "¿Es para uso doméstico o comercial/industrial?"
        ]
    
    # ALIMENTOS ESPECÍFICOS - Preguntas discriminantes correctas
    # Frutas
    if any(kw in combined_context for kw in ["fruta", "frutas", "manzana", "naranja", "plátano", "piña", "limón", "uva", "durazno", "pera", "melocotón"]):
        questions = []
        if not any(kw in combined_context for kw in ["tipo especifico", "tipo de fruta", "manzana", "naranja", "plátano"]):
            questions.append("¿Qué tipo específico de fruta? (manzana, naranja, plátano, etc.)")
        if not any(kw in combined_context for kw in ["fresco", "seco", "procesado", "refrigerado", "congelado"]):
            questions.append("¿Está fresco, seco, o procesado?")
        if not any(kw in combined_context for kw in ["entero", "troceado", "fileteado", "pelado"]):
            questions.append("¿Está entero o ha sido procesado?")
        return questions if questions else ["Fruta completamente especificada"]
    
    # Carnes
    if any(kw in combined_context for kw in ["carne", "carnes", "res", "pollo", "cerdo", "cordero", "ternera", "pavo", "conejo"]):
        questions = []
        if not any(kw in combined_context for kw in ["tipo de carne", "res", "pollo", "cerdo", "cordero"]):
            questions.append("¿Qué tipo de carne? (res, pollo, cerdo, cordero, etc.)")
        if not any(kw in combined_context for kw in ["entero", "trozo", "trozos", "deshuesado", "deshuesa", "filete"]):
            questions.append("¿Está entera, en trozos, o deshuesada?")
        if not any(kw in combined_context for kw in ["fresco", "refrigerado", "congelado", "salado", "curado"]):
            questions.append("¿Fresca, refrigerada, congelada, o salada?")
        return questions if questions else ["Carne completamente especificada"]
    
    # Pescado
    if any(kw in combined_context for kw in ["pescado", "peces", "atún", "tilapia", "salmón", "trucha", "anchoa", "sardina", "bacalao"]):
        questions = []
        if not any(kw in combined_context for kw in ["especie", "tipo de pescado", "atún", "tilapia", "salmón"]):
            questions.append("¿Qué especie de pescado? (atún, tilapia, salmón, etc.)")
        if not any(kw in combined_context for kw in ["entero", "fileteado", "filete", "conserva", "enlatado"]):
            questions.append("¿Está entero, fileteado, o en conserva?")
        if not any(kw in combined_context for kw in ["fresco", "congelado", "seco", "salado", "ahumado"]):
            questions.append("¿Fresco, congelado, o en conserva?")
        return questions if questions else ["Pescado completamente especificado"]
    
    # Genérico cuando no detectamos categoría
    return [
        "Por favor, describe el producto con más detalle: ¿qué es exactamente y para qué se usa?"
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


def _was_motor_question_asked_in_previous_turn(conversation_history: list | None = None) -> bool:
    """Check if motor question was asked in the previous turn but user didn't answer it.
    
    This prevents repetitive questions: if we asked "¿Qué tipo de motor?" in TURN N-1,
    and user answered something else (like capacity), don't repeat the motor question in TURN N.
    """
    if not conversation_history or len(conversation_history) == 0:
        return False
    
    # Get the last turn's assistant response
    last_turn = conversation_history[-1]
    if isinstance(last_turn, dict):
        assistant_response = last_turn.get("assistant", {})
    elif isinstance(last_turn, (list, tuple)) and len(last_turn) >= 2:
        assistant_response = last_turn[1]
    else:
        return False
    
    # Check if missing_fields from last turn contained a motor question
    if isinstance(assistant_response, dict):
        missing_fields = assistant_response.get("missing_fields", [])
        motor_was_asked = any("motor" in _normalize_text(f) for f in missing_fields)
        return motor_was_asked
    
    return False


def _fix_missing_field(field: str) -> str:
    """Insert spaces and clean common merged words in missing_field strings."""
    if not isinstance(field, str):
        return field

    original = field
    
    # Insert space between lowercase and uppercase merged words
    field = re.sub(r'([a-z])([A-Z])', r'\1 \2', field)

    # CRÍTICO: Separar palabras compuestas comunes - usar lookbehind/lookahead para más precisión
    # Capturar también casos donde hay números antes: "10 personasautobus" o "10personasautobus"
    replacements = [
        # Vehículos: [código HS] [número] [palabra pegada]
        # Ejemplo: "8702 10 personasautobus" → "8702 10 personas autobús"
        (r'(\d{4}\s+\d+\s+)personasautobus', r'\1personas autobús'),
        (r'(\d{4}\s+\d+\s+)personasautomovil', r'\1personas automóvil'),
        (r'(\d{4}\s+\d+\s+)personasautocar', r'\1personas autocar'),
        (r'(\d{4}\s+\d+\s+)personascamion', r'\1personas camión'),
        # También sin código HS: "10 personasautobus" → "10 personas autobús"  
        (r'(\d+\s+)personasautobus', r'\1personas autobús'),
        (r'(\d+\s+)personasautomovil', r'\1personas automóvil'),
        (r'(\d+\s+)personasautocar', r'\1personas autocar'),
        (r'(\d+\s+)personascamion', r'\1personas camión'),
        # Sin número y sin espacio también
        (r'(?<!\d\s)\bpersonasautobus\b', r'personas autobús'),
        (r'(?<!\d\s)\bpersonasautomovil\b', r'personas automóvil'),
        (r'(?<!\d\s)\bpersonasautocar\b', r'personas autocar'),
        (r'(?<!\d\s)\bpersonascamion\b', r'personas camión'),
        (r'(?<!\d\s)\bpersonasmotocicleta\b', r'personas motocicleta'),
        # Vehículos: mercancías + tipo
        (r'\bmercanciascamion\b', r'mercancías camión'),
        (r'\bmercanciascamioneta\b', r'mercancías camioneta'),
        # Versiones ya con espacio parcial (normalizar acentos)
        (r'\bpersonas\s+autobus\b', r'personas autobús'),
        (r'\bpersonas\s+automovil\b', r'personas automóvil'),
        (r'\bmercancias\s+camion\b', r'mercancías camión'),
        # Capacidad
        (r'litroscapacidad', r'litros capacidad'),
        (r'litrocapacidad', r'litro capacidad'),
        # Condición
        (r'nuevocondicion', r'nuevo condición'),
        (r'usadocondicion', r'usado condición'),
        # Motor
        (r'gasolinamotor', r'gasolina motor'),
        (r'dieselmotor', r'diesel motor'),
        (r'electricomotor', r'eléctrico motor'),
    ]

    for pattern, replacement in replacements:
        field = re.sub(pattern, replacement, field, flags=re.IGNORECASE)

    field = ' '.join(field.split())
    
    if field != original:
        logger.debug(f"[FIX_MISSING_FIELD] '{original}' → '{field}'")
    
    return field

def _ensure_missing_fields(res: Dict[str, Any], blob: str, conversation_history: list | None = None) -> Dict[str, Any]:
    """Ensure missing_fields is populated with sensible defaults when empty."""
    logger.info(f"LOG_ENSURE_MISSING_FIELDS_ENTER: candidates_count={len(res.get('top_candidates', []))}, has_mf={bool(res.get('missing_fields'))}")
    
    candidates = res.get("top_candidates") or []
    if candidates:
        top = candidates[0]
        confidence = float(top.get("confidence", 0))
        code = top.get("code", "")
        
        # CRÍTICO: Para categorías de alto impacto, SIEMPRE asegurar que haya missing_fields críticos
        # incluso si el LLM dice que tiene suficiente información
        code_str = str(code).replace(".", "").replace(" ", "")
        is_textile_code = code_str.startswith(("50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63"))
        is_vehicle_code = code_str.startswith(("8702", "8703", "8704"))
        is_metal_code = code_str.startswith("72")
        
        # Si es textile, metal o vehículo, SIEMPRE generar missing_fields críticos  
        if (is_textile_code or is_vehicle_code or is_metal_code) and confidence <= 0.95:
            logger.info(f"LOG_ENSURE_CRITICAL: Forcing critical fields for high-impact category (code={code}, conf={confidence:.0%})")
            
            # Get existing missing fields
            existing_missing = res.get("missing_fields") or []
            existing_text = " ".join(existing_missing).lower()
            
            if is_textile_code:
                # Textiles: Must have material, type, and use
                critical_missing = [
                    "¿De qué material está hecho? (algodón, poliéster, lana, mezcla, sintético)",
                    "¿Es tejido, punto, o no tejido?",
                    "¿Cuál es el uso final? (prenda de vestir, tela por metro, artículos de hogar)"
                ]
                # Only add if not already present
                for cm in critical_missing:
                    cm_key = cm.split("?")[0].lower()
                    if cm_key not in existing_text and cm not in existing_missing:
                        existing_missing.append(cm)
                res["missing_fields"] = existing_missing
            
            elif is_vehicle_code:
                # Vehicles: Must have motor type and condition
                vehicle_critical = [
                    "¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)",
                    "¿Es nuevo o usado?"
                ]
                for vm in vehicle_critical:
                    vm_key = vm.split("?")[0].lower()
                    if vm_key not in existing_text and vm not in existing_missing:
                        existing_missing.append(vm)
                res["missing_fields"] = existing_missing
            
            elif is_metal_code:
                # Metals: Must have thickness and finish
                metal_critical = [
                    "¿Cuál es el espesor de la lámina en mm?",
                    "¿Cuál es el acabado? (laminado en caliente, laminado en frío, pulido, etc.)"
                ]
                for mm in metal_critical:
                    mm_key = mm.split("?")[0].lower()
                    if mm_key not in existing_text and mm not in existing_missing:
                        existing_missing.append(mm)
                res["missing_fields"] = existing_missing
    
    if candidates and not res.get("missing_fields"):
        top = candidates[0]
        confidence = float(top.get("confidence", 0))
        code = top.get("code", "")

        # Detectar si el código es "genérico" (termina en .90, .00, etc.)
        is_generic_code = str(code).endswith((".90", ".00", ".10"))

        combined_context = f"{(blob or '').lower()} {_text_blob_from_query_history('', conversation_history or [], include_assistant=False).lower()}"
        normalized_context = _normalize_text(combined_context)

        # Load materials keywords (data-driven)
        materials_cfg = _load_materials_keywords() or {}
        mat_synonyms = set()
        textile_synonyms = set()
        metal_synonyms = set()
        coatings_synonyms = set()
        for m in materials_cfg.get("materials", []):
            for s in m.get("synonyms", []) or []:
                mat_synonyms.add(_normalize_text(str(s)))
            tags = m.get("tags", []) or []
            if "textil" in tags or "textile" in tags:
                for s in m.get("synonyms", []) or []:
                    textile_synonyms.add(_normalize_text(str(s)))
            if "metal" in tags:
                for s in m.get("synonyms", []) or []:
                    metal_synonyms.add(_normalize_text(str(s)))
        for c in materials_cfg.get("coatings", []) or []:
            for s in c.get("synonyms", []) or []:
                coatings_synonyms.add(_normalize_text(str(s)))

        # Detectar tipo de producto (usar texto normalizado sin acentos)
        is_steel = any(kw in normalized_context for kw in list(metal_synonyms) + ["lamina", "laminas", "plancha", "chapa", "bobina", "inoxidable"])
        is_electrodomestico = any(kw in normalized_context for kw in ["lavadora", "refrigerador", "microondas", "horno", "lavavajillas", "secadora", "aspiradora"])
        is_textile = any(kw in normalized_context for kw in list(textile_synonyms) + ["textil", "tela", "tejido", "prenda", "ropa", "lana"])
        is_food = any(kw in normalized_context for kw in ["carne", "pescado", "cafe", "azucar", "fruta", "verdura", "alimento"])
        
        logger.info(f"LOG_ENSURE_MISSING_FIELDS: code={code}, conf={confidence:.0%}, is_generic={is_generic_code}, is_textile={is_textile}, is_steel={is_steel}, is_electro={is_electrodomestico}, is_food={is_food}")

        # Señales de falta de especificidad
        has_thickness = bool(re.search(r"\b\d+(?:[\.,]\d+)?\s*mm\b", normalized_context))
        # Detectar recubrimiento incluyendo sinónimos y variaciones comunes (from data)
        has_recubrimiento = False
        if coatings_synonyms:
            has_recubrimiento = any(kw in normalized_context for kw in coatings_synonyms)
        else:
            has_recubrimiento = any(kw in normalized_context for kw in ["galvanizado", "galvanizacion", "galvanizada", "zincado", "pintado", "recubierto", "sin recubrimiento"])
        has_acabado = any(kw in normalized_context for kw in ["laminado en caliente", "laminado en frio", "pulido"])

        auto_missing = []

        # Reglas específicas por categoría: generar preguntas si el código es genérico o falta detalle clave
        if is_steel and str(code).startswith("72") and (is_generic_code or not (has_thickness and has_acabado)):
            auto_missing = [
                "¿Cuál es el espesor de la lámina en mm? → Define si es lámina fina, plancha o chapa gruesa",
                "¿Está galvanizado, pintado, o sin recubrimiento? → Puede cambiar la partida",
                "¿Cuál es el acabado? (laminado en caliente, laminado en frío, pulido, etc.) → Diferencia entre capítulos",
                "¿Cuál es la composición? (acero al carbono, inoxidable, etc.) → Podría cambiar de capítulo",
            ]
        elif is_electrodomestico and str(code).startswith("84") and (is_generic_code or confidence <= 0.85):
            auto_missing = [
                "¿Qué tipo específico de electrodoméstico es? (lavadora, refrigerador, microondas, etc.)",
                "¿Cuál es la capacidad? (kg para lavadora, litros para refrigerador, watts para microondas)",
                "¿Es de carga frontal o superior? (si aplica para lavadora)",
                "¿Es nuevo o usado?"
            ]
        elif is_textile and (is_generic_code or confidence <= 0.85):
            # Textiles: Chapters 50-63
            # Always ask for critical fields if not high confidence
            auto_missing = [
                "¿De qué material está hecho? (algodón, poliéster, lana, mezcla, sintético)",
                "¿Es tejido, punto, o no tejido?",
                "¿Cuál es el uso final? (prenda de vestir, tela por metro, artículos de hogar)"
            ]
        elif is_food and str(code).startswith(("02", "03", "04", "05", "07", "08", "09", "10", "11", "12", "19", "20", "21")) and (is_generic_code or confidence < 0.85):
            # MEJORADO: Preguntas discriminantes específicas por subcategoría de alimento
            code_str = str(code)
            
            if code_str.startswith("02"):  # Carnes (capítulo 02)
                auto_missing = [
                    "¿Qué tipo de carne? (res, pollo, cerdo, cordero, etc.) → Determina partida dentro de capítulo 02",
                    "¿Está entero, en trozos grandes, o deshuesado? → Discrimina entre 0201, 0202, 0203",
                    "¿Fresca, refrigerada, congelada, o salada? → Cambia significativamente el código HS"
                ]
            elif code_str.startswith("03"):  # Pescado (capítulo 03)
                auto_missing = [
                    "¿Qué especie o tipo de pescado específico? → Discrimina dentro del capítulo 03",
                    "¿Entero, fileteado, en filetes congelados, o en conserva? → Define la subpartida",
                    "¿Fresco, congelado, seco-salado, ahumado, o en conserva? → Importante para clasificación"
                ]
            elif code_str.startswith("08"):  # Frutas (capítulo 08)
                auto_missing = [
                    "¿Qué tipo específico de fruta? (manzana, naranja, plátano, etc.) → Define si es 0801-0809",
                    "¿Está fresco/refrigerado, seco, o procesado? → Afecta la subpartida dentro de 08XX",
                    "¿Está entero o ha sido procesado/pelado? → Discrimina dentro de la partida"
                ]
            elif code_str.startswith(("09", "10", "11", "12")):  # Otros alimentos (café, azúcar, etc.)
                auto_missing = [
                    "¿Qué presentación tiene? (grano, molido, refinado, en rama, etc.) → Cambia la partida",
                    "¿Está crudo, tostado, procesado, o refinado? → Define el nivel HS",
                    "¿Qué grado de pureza o calidad? (si aplica para su tipo de producto)"
                ]
            else:
                auto_missing = [
                    "¿Qué tipo específico de alimento es?",
                    "¿Cuál es su presentación? (fresco, procesado, congelado, envasado)"
                ]

        if auto_missing:
            res["missing_fields"] = auto_missing
            
            # DIAGNÓSTICO: Detectar si el código es terminal y confianza es baja
            is_terminal = _is_terminal_hs_code(code)
            if is_terminal and confidence < 0.85:
                logger.warning(
                    f"LOG_TERMINAL_CODE_DETECTED: code={code} (terminal HS8/HS6) but low confidence={confidence:.0%}. "
                    f"This may be a structural limitation - verify corpus has complete HS documentation."
                )
            
            logger.info(f"LOG_AUTO_MISSING_FIELDS: Generated {len(auto_missing)} questions for code {code} (confidence={confidence:.0%}, generic={is_generic_code}, terminal={is_terminal})")
    
    if res.get("missing_fields"):
        # Augment with microondas-specific questions if still missing critical fields
        try:
            history_text = _text_blob_from_query_history("", conversation_history or [], include_assistant=False).lower()
            combined_context = f"{(blob or '').lower()} {history_text}"
            is_microondas = any(kw in combined_context for kw in ["microondas", "microonda", "horno microonda", "horno de microondas"])
            has_liters = (
                bool(re.search(r"\b\d+(?:[\.,]\d+)?\s*(l|litros?)\b", combined_context))
                or any(kw in combined_context for kw in ["litro", "litros", "capacidad"])
            )
            already_asks_liters = any(
                "litro" in _normalize_text(f) or "capacidad" in _normalize_text(f)
                for f in (res.get("missing_fields") or [])
            )
            if is_microondas and not has_liters and not already_asks_liters:
                res["missing_fields"].insert(0, "¿Cuál es la capacidad en litros?")
        except Exception:
            pass
        
        # NUEVA LÓGICA: Para vehículos, agregar múltiples preguntas estratégicas faltantes
        try:
            candidates = res.get("top_candidates") or []
            is_vehicle_code = any(
                str(cand.get("code", "")).startswith(("8702", "8703", "8704"))
                for cand in candidates
            )
            
            if is_vehicle_code:
                combined_context = f"{(blob or '').lower()} {_text_blob_from_query_history('', conversation_history or [], include_assistant=False).lower()}"
                
                # ✅ CRÍTICO: VALIDACIÓN DE CATEGORÍA
                # Si el historial habla de laptop/electrodoméstico pero el código es vehículo,
                # RECHAZAR las preguntas de vehículos (el LLM se confundió)
                history_is_laptop = any(
                    kw in combined_context 
                    for kw in ["laptop", "portátil", "computadora", "notebook", "dell", "xps", "ssd", "ram", "gb", "procesador"]
                )
                history_is_electrodomestico = any(
                    kw in combined_context 
                    for kw in ["lavadora", "automática", "carga frontal", "microondas"]
                )
                
                # Si hay conflicto de categoría → NO agregar preguntas de vehículos
                if history_is_laptop or history_is_electrodomestico:
                    logger.warning(f"LOG_CATEGORY_CONFLICT_IN_ENSURE: History indicates laptop/electrodomestico but code suggests vehicle. REJECTING vehicle questions.")
                    # Limpiar missing_fields de preguntas de vehículos
                    res["missing_fields"] = [
                        f for f in (res.get("missing_fields") or [])
                        if not any(kw in f.lower() for kw in ["vehículo", "autobus", "automóvil", "camión", "personas puede transportar", "tipo de motor"])
                    ]
                    # Prune fields against conversation history before returning
                    res = _prune_missing_fields(res, blob, conversation_history or [])
                    return res
                
                # Detectar qué información ya tenemos
                has_capacity = any(
                    kw in combined_context 
                    for kw in ["persona", "personas", "plazas", "plaza", "asiento", "asientos", "capacidad"]
                )
                has_motor_type = any(
                    kw in combined_context 
                    for kw in ["gasolina", "diesel", "diésel", "electrico", "eléctrico", "hibrido", "híbrido"]
                )
                has_cilindrada = any(
                    kw in combined_context 
                    for kw in ["cilindrada", "cc", "cm3", "cilindrada", "desplazamiento", "cc"]
                )
                has_nuevo_usado = any(
                    kw in combined_context 
                    for kw in ["nuevo", "usa", "usado", "antiguo", "nuevos", "usados", "new", "second hand"]
                )
                
                # Construir lista de preguntas FALTANTES en orden estratégico
                strategic_questions = []
                
                if not has_capacity:
                    strategic_questions.append("¿Cuántas personas puede transportar? (define si es autobús ≥10, vehículo ≤9, o camión)")
                
                if not has_motor_type:
                    strategic_questions.append("¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)")
                
                if not has_cilindrada and (has_motor_type or not has_capacity):
                    strategic_questions.append("¿Cilindrada del motor en cm³?")
                
                if not has_nuevo_usado and (has_motor_type or has_capacity):
                    strategic_questions.append("¿Es nuevo o usado?")
                
                # Si hay preguntas estratégicas NUEVAS que agregar
                if strategic_questions:
                    # Conservar preguntas del LLM que no sean sobre motor
                    existing_questions = [
                        f for f in (res.get("missing_fields") or [])
                        if "motor" not in _normalize_text(f)
                    ]
                    
                    # Combinar: preguntas estratégicas primero, luego las existentes
                    res["missing_fields"] = strategic_questions + existing_questions
                    
                    logger.info(f"LOG_VEHICLE_MULTIPLE_QUESTIONS: Added {len(strategic_questions)} strategic questions for vehicle {candidates[0].get('code') if candidates else '?'}")
                
        except Exception as e:
            logger.error(f"Error in vehicle strategic questions logic: {e}")
            pass
        
        # Before returning, prune missing_fields against history to avoid re-asking answered questions
        res = _prune_missing_fields(res, blob, conversation_history or [])
        return res
    
    # CRÍTICO: Solo usar fallback si NO hay candidatos válidos
    # Si el LLM devolvió candidatos correctos (no 9999.00), confiar en su criterio de no pedir más campos
    candidates = res.get("top_candidates") or []
    has_valid_candidates = any(
        cand.get("code") and cand.get("code") != "9999.00"
        for cand in candidates
    )
    
    if has_valid_candidates:
        # El LLM identificó un código real, confiar en su criterio
        # Si decidió no pedir más campos, respetarlo (clasificación suficiente para HS6)
        
        # PERO: FORCE motor question para vehículos si no está especificado
        # PERO: NO repetir si ya fue preguntado en turno anterior sin ser respondido
        is_vehicle_code = any(
            str(cand.get("code", "")).startswith(("8702", "8703", "8704"))
            for cand in candidates
        )
        
        if is_vehicle_code:
            combined_context = f"{(blob or '').lower()} {_text_blob_from_query_history('', conversation_history or [], include_assistant=False).lower()}"
            
            # ✅ CRÍTICO: VALIDACIÓN DE CATEGORÍA (SEGUNDA SECCIÓN)
            # Si el historial habla de laptop/electrodoméstico pero el código es vehículo,
            # RECHAZAR las preguntas de vehículos (el LLM se confundió)
            history_is_laptop = any(
                kw in combined_context 
                for kw in ["laptop", "portátil", "computadora", "notebook", "dell", "xps", "ssd", "ram", "gb", "procesador"]
            )
            history_is_electrodomestico = any(
                kw in combined_context 
                for kw in ["lavadora", "automática", "carga frontal", "microondas"]
            )
            
            # Si hay conflicto de categoría → NO agregar preguntas de vehículos
            if history_is_laptop or history_is_electrodomestico:
                logger.warning(f"LOG_CATEGORY_CONFLICT_IN_ENSURE_V2: History indicates laptop/electrodomestico but code suggests vehicle. REJECTING vehicle questions.")
                # Limpiar missing_fields de preguntas de vehículos
                res["missing_fields"] = [
                    f for f in (res.get("missing_fields") or [])
                    if not any(kw in f.lower() for kw in ["vehículo", "autobus", "automóvil", "camión", "personas puede transportar", "tipo de motor"])
                ]
                return res
            
            # Detectar qué información ya tenemos
            has_capacity = any(
                kw in combined_context 
                for kw in ["persona", "personas", "plazas", "plaza", "asiento", "asientos", "capacidad"]
            )
            has_motor_type = any(
                kw in combined_context 
                for kw in ["gasolina", "diesel", "diésel", "electrico", "eléctrico", "hibrido", "híbrido"]
            )
            has_cilindrada = any(
                kw in combined_context 
                for kw in ["cilindrada", "cc", "cm3", "cilindrada", "desplazamiento", "cc"]
            )
            has_condition = any(
                kw in combined_context 
                for kw in ["nuevo", "usada", "usad", "recondicionado", "seminuevo"]
            )
            
            motor_asked_in_previous_turn = _was_motor_question_asked_in_previous_turn(conversation_history)
            
            # Construir lista de preguntas FALTANTES en orden estratégico
            strategic_questions = []
            
            if not has_capacity:
                strategic_questions.append("¿Cuántas personas puede transportar? (define si es autobús ≥10, vehículo ≤9, o camión)")
            
            if not has_motor_type and not motor_asked_in_previous_turn:
                strategic_questions.append("¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)")
            
            if not has_cilindrada and (has_motor_type or not has_capacity):
                strategic_questions.append("¿Cilindrada del motor en cm³?")
            
            # CRÍTICO: Para vehículos, SIEMPRE preguntar si es nuevo/usado (afecta al último dígito HS10)
            if not has_condition:
                strategic_questions.append("¿Es nuevo o usado? (define el último dígito del código)")
            
            if strategic_questions:
                res["missing_fields"] = strategic_questions
                logger.info(f"LOG_VEHICLE_MULTIPLE_QUESTIONS: Added {len(strategic_questions)} strategic questions for vehicle {candidates[0].get('code') if candidates else '?'}")
            elif motor_asked_in_previous_turn and not has_motor_type:
                logger.info(f"LOG_FORCE_MOTOR_SKIP: Motor already asked in previous turn, user chose not to answer - not repeating")
            else:
                # Usuario YA respondió motor en historial - remover la pregunta si está en missing_fields
                res["missing_fields"] = [
                    f for f in (res.get("missing_fields") or [])
                    if "motor" not in _normalize_text(f)
                ]
        
        return res
    
    # Get defaults - now pass conversation_history so it can detect previous context
    res["missing_fields"] = _default_missing_fields(blob, conversation_history)
    
    # Aplicar normalización de espacios a los campos generados
    if res.get("missing_fields"):
        res["missing_fields"] = [_fix_missing_field(f) for f in res["missing_fields"]]
    
    # Prune defaults based on conversation history to avoid re-asking
    # This is critical because _aggressive_missing_fields_cleanup may have cleared all fields
    res = _prune_missing_fields(res, blob, conversation_history or [])
    
    # Apply text normalization to fix merged words in fallback text
    if res.get("missing_fields"):
        res["missing_fields"] = [_fix_missing_field(f) for f in res["missing_fields"]]
    
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
    
    # Aplicar limpieza de palabras pegadas usando la función global
    if res.get("missing_fields"):
        original_count = len(res["missing_fields"])
        logger.debug(f"[NORMALIZE_FIELDS] Before fix: {res['missing_fields'][:2]}")
        res["missing_fields"] = [_fix_missing_field(f) for f in res["missing_fields"]]
        logger.debug(f"[NORMALIZE_FIELDS] After fix: {res['missing_fields'][:2]}")
    
    # Extraer años de evidencia si está disponible
    years_from_evidence = set()
    if evidence:
        for ev in evidence:
            year = ev.get("year")
            if year and isinstance(year, int):
                years_from_evidence.add(year)
    
    # Si no hay años en evidencia, usar años activos por defecto
    default_years = sorted(list(years_from_evidence)) if years_from_evidence else [2025, 2026]
    
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
        
        # Agregar años al candidato si no los tiene
        if "years" not in candidate:
            candidate["years"] = default_years

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
    """Remove missing_fields that were already answered in the query or history.
    IMPORTANT: Also removes motor question if it was asked in the previous turn without being answered.
    IMPORTANT: Does NOT remove critical fields for high-impact categories (textiles, vehicles, metals) if confidence is low.
    """
    # Get the text blob - now returns already normalized text
    text_blob_norm = _text_blob_from_query_history(query_text, conversation_history, include_assistant=False)
    
    logger.info(f"LOG_PRUNE_START: text_blob_norm='{text_blob_norm[:200]}...', missing_fields_count={len(res.get('missing_fields', []))}")
    
    if not res.get("missing_fields"):
        return res
    
    # CRÍTICO: Si es categoría de alto impacto (textil, vehículo, metal) con baja confianza, 
    # NO ELIMINAR missing_fields - son críticos para clasificación
    candidates = res.get("top_candidates") or []
    if candidates:
        top = candidates[0]
        code = top.get("code", "")
        confidence = float(top.get("confidence", 0))
        
        code_str = str(code).replace(".", "").replace(" ", "")
        is_critical_category = (
            code_str.startswith(("50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63")) or  # Textiles
            code_str.startswith(("8702", "8703", "8704")) or  # Vehicles
            code_str.startswith("72")  # Metals
        )
        
        if is_critical_category and confidence <= 0.85:
            # Si es categoría crítica con baja confianza, PRESERVAR todos los missing_fields
            logger.info(f"LOG_PRUNE_SKIP_CRITICAL: Skipping prune for critical category {code} (conf={confidence:.0%}) - preserve all fields")
            return res
    
    # EARLY PRUNE: Remove motor question if it was already asked in the previous turn
    # This prevents repetitive/inconsistent questions (user already saw it and chose not to answer)
    motor_asked_in_previous_turn = _was_motor_question_asked_in_previous_turn(conversation_history)
    if motor_asked_in_previous_turn:
        original_missing = res.get("missing_fields", [])
        res["missing_fields"] = [
            f for f in original_missing
            if "motor" not in _normalize_text(f).lower()
        ]
        logger.info(f"LOG_PRUNE_MOTOR_REPEAT: Motor was asked in previous turn - removing from current missing_fields")
        if len(res["missing_fields"]) < len(original_missing):
            logger.info(f"LOG_PRUNE_MOTOR_REMOVED: Removed motor question ({len(original_missing)} → {len(res['missing_fields'])} fields)")
    
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
        ("nuevo", "usado", "condicion"): ["nuevo", "nueva", "usado", "usada", "seminuevo", "recondicionado"],
        # Tipo de Combustible (NOT cilindrada) - incluir variantes comunes de typos
        ("tipo de motor", "combustible", "fuel"): ["gasolina", "diesel", "diedel", "diessel", "electrico", "electrica", "electrico", "hibrido", "hibrida", "nafta"],
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
        # Propósito/Uso (INCLUYE doméstico/comercial)
        ("proposito", "uso", "comercial", "particular", "domestico", "industrial"): ["comercial", "particular", "privado", "publico", "transporte", "domestico", "domestica", "industrial", "industria", "hogar", "doméstico"],
        # Material
        ("material", "madera", "metal", "plastico", "aluminio", "acero", "vidrio"): ["madera", "metal", "plastico", "plastica", "aluminio", "acero", "vidrio"],
        # Textiles: aceptar variantes sin tilde y sinónimos
        ("material", "algodon", "poliester", "seda", "mezcla", "textil", "tela"): [
            "algodon", "poliester", "seda", "mezcla", "sintetico", "sintetico", "fibra", "synthetic"
        ],
        # Tipo de tejido (tejido plano / punto / no tejido)
        ("tejido", "punto", "no tejido", "tejido plano"): ["tejido", "punto", "notejido", "no tejido", "plano"],
        # Recubrimiento / acabado superficial (galvanizado, pintado, sin recubrimiento)
        ("recubrimiento", "galvanizado", "pintado", "zincado", "galvanizacion", "galvanizacion por inmersion"): [
            "galvanizado",
            "galvanizacion",
            "galvanizacion",
            "zincado",
            "pintado",
            "sin recubrimiento",
            "sinrecubrimiento",
            "sin recubrir",
            "no recubrimiento",
            "no tiene recubrimiento",
            "no tienen recubrimiento",
            "recubierto",
        ],
        # CRÍTICO: Tipo de dispositivo (laptop vs desktop)
        ("portatil", "tipo de dispositivo", "tipo de computadora", "desktop", "escritorio"): ["laptop", "portatil", "notebook", "netbook", "desktop", "escritorio", "computadora de escritorio"],
        # Funciones adicionales (convección, grill, etc.)
        ("conveccion", "grill", "funcion", "funciones"): ["conveccion", "convección", "grill", "función", "funciones"],
        # Capacidad en litros
        ("litro", "capacidad"): ["litro", "litros", "l", "capacidad"],
    }

    # Augmentar dinámicamente field_satisfaction_map con materiales/recubrimientos desde JSON
    try:
        materials_cfg = _load_materials_keywords() or {}
        for m in materials_cfg.get("materials", []):
            key = ("material", m.get("id", ""), m.get("canonical", ""))
            vals = [_normalize_text(str(s)) for s in (m.get("synonyms", []) or [])]
            if vals:
                field_satisfaction_map[key] = vals
        for c in materials_cfg.get("coatings", []) or []:
            key = ("recubrimiento", c.get("id", ""), c.get("canonical", ""))
            vals = [_normalize_text(str(s)) for s in (c.get("synonyms", []) or [])]
            if vals:
                field_satisfaction_map[key] = vals
    except Exception:
        pass
    
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
        
        # DETECCIÓN CRÍTICA: Si dice "describe el producto con más detalle" pero el usuario
        # ya ha dado detalles específicos (watts, dimensiones, características), eliminar
        if "describe el producto" in field_norm or "describe con mas detalle" in field_norm:
            # Revisar si ya tiene detalles técnicos específicos
            has_technical_details = bool(
                re.search(r'\d+\s*(watts?|watt|w|kg|litro|litros|cm|mm|pulgadas)', text_blob_norm, re.IGNORECASE) or
                any(kw in text_blob_norm for kw in ["conveccion", "convección", "grill", "función", "doméstico", "domestico", "comercial", "industrial"])
            )
            if has_technical_details:
                logger.info(f"LOG_PRUNE_FIELD: User provided technical details (watts, capacidad, etc.) - removing generic 'describe' field")
                continue
        
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
    """DEPRECATED: Rule-based fallback disabled. LLM+RAG should handle all classifications.
    This function now does nothing and returns the result unchanged."""
    # NO hardcoding - LLM+RAG must handle all classification
    return res


def _apply_device_overrides(res: Dict[str, Any], query: str, conversation_history: list | None) -> Dict[str, Any]:
    """Lightweight safety overrides for known short follow-ups (e.g., microondas).
    Keeps classification stable when context is clear but query is minimal."""
    # Construir contexto combinado (query + historial del usuario)
    combined = (query or "").lower()
    if conversation_history:
        for turn in conversation_history:
            if isinstance(turn, dict):
                user_msg = turn.get("user", "")
            elif isinstance(turn, (list, tuple)) and len(turn) >= 1:
                user_msg = turn[0]
            else:
                user_msg = ""
            if user_msg:
                combined += " " + str(user_msg).lower()

    # MICROONDAS: evitar regresión a 9999.00 o capítulos incorrectos en turnos cortos
    is_microondas = any(kw in combined for kw in ["microondas", "microonda", "horno microonda", "horno de microondas"])
    if is_microondas:
        candidates = res.get("top_candidates") or []
        top = candidates[0] if candidates else None
        code = (top.get("code") if top else "") or ""
        conf = float(top.get("confidence", 0)) if top else 0.0

        if (not candidates) or code in ("", "9999.00"):
            res["top_candidates"] = [{
                "code": "8516.60",
                "description": "Hornos de microondas",
                "confidence": max(conf, 0.85),
                "level": "HS6",
                "years": [2025, 2026],
            }]
            res.setdefault("warnings", []).append("Código ajustado por contexto de microondas")
            return res

        if not str(code).startswith("8516") and conf < 0.60:
            res["top_candidates"] = [{
                "code": "8516.60",
                "description": "Hornos de microondas",
                "confidence": max(conf, 0.85),
                "level": "HS6",
                "years": [2025, 2026],
            }]
            res.setdefault("warnings", []).append("Código ajustado por contexto de microondas")
            return res

    # LAPTOP/COMPUTADORA: estabilizar cuando el contexto es claro pero el turno es corto/específico
    is_laptop = any(
        kw in combined
        for kw in [
            "laptop", "portátil", "computadora", "computador", "notebook", "pc",
            "ram", "ssd", "nvme", "ddr5", "ddr4", "procesador", "intel", "ryzen",
            "i7", "i9", "pantalla", "oled", "4k", "batería", "almacenamiento"
        ]
    )
    if is_laptop:
        candidates = res.get("top_candidates") or []
        top = candidates[0] if candidates else None
        code = (top.get("code") if top else "") or ""
        conf = float(top.get("confidence", 0)) if top else 0.0

        if (not candidates) or code in ("", "9999.00"):
            res["top_candidates"] = [{
                "code": "8471.30",
                "description": "Máquinas automáticas para tratamiento o procesamiento de datos, portátiles",
                "confidence": max(conf, 0.85),
                "level": "HS6",
                "years": [2025, 2026],
            }]
            res.setdefault("warnings", []).append("Código ajustado por contexto de laptop")
            return res

        if not str(code).startswith("8471") and conf < 0.60:
            res["top_candidates"] = [{
                "code": "8471.30",
                "description": "Máquinas automáticas para tratamiento o procesamiento de datos, portátiles",
                "confidence": max(conf, 0.85),
                "level": "HS6",
                "years": [2025, 2026],
            }]
            res.setdefault("warnings", []).append("Código ajustado por contexto de laptop")
            return res

    return res


def _aggressive_missing_fields_cleanup(res: Dict[str, Any], query: str, conversation_history: list | None = None) -> Dict[str, Any]:
    """
    Post-process missing_fields aggressively when we have sufficient classification.
    
    Strategy:
    - HS6+ (6+ digits) with confidence >= 75% → clear most missing_fields EXCEPT critical ones
    - HS4 (4 digits) with confidence >= 85% → clear most missing_fields EXCEPT critical ones
    - Critical fields (nuevo/usado for vehicles, etc.) are NEVER auto-removed
    - Otherwise, keep missing_fields for further refinement
    
    IMPORTANTE: Respetar el historial de conversación para no re-preguntar lo ya respondido.
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

    # NO limpiar si el código es genérico (.90/.00/.10) o si son preguntas críticas de acero/textiles
    is_generic_code = str(code).endswith((".90", ".00", ".10"))
    code_str_clean = str(code).replace(".", "").replace(" ", "")
    is_critical_category = (
        code_str_clean.startswith(("50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63"))  # Textiles
        or code_str_clean.startswith("72")  # Metals
        or code_str_clean.startswith(("8702", "8703", "8704"))  # Vehicles
    )
    
    missing_fields_text = _normalize_text(" ".join(original_missing or []))
    has_steel_questions = any(
        kw in missing_fields_text
        for kw in ["espesor", "lamina", "laminas", "galvanizado", "recubrimiento", "laminado en caliente", "laminado en frio"]
    )
    has_textile_questions = any(
        kw in missing_fields_text
        for kw in ["tipo de tela", "tejido", "punto", "material", "algodon", "poliester", "lana", "uso final", "prenda"]
    )
    
    if is_generic_code or (str(code).startswith("72") and has_steel_questions) or (str(code).startswith("5") and has_textile_questions):
        logger.info(f"LOG_AGGRESSIVE_CLEANUP_SKIP: Generic code ({is_generic_code}) or steel questions ({has_steel_questions}) or textile questions ({has_textile_questions}) detected → preserve missing_fields")
        should_cleanup = False
    elif is_critical_category:
        # Para categorías críticas (textiles, metales, vehículos), ser MÁS conservador - necesitamos 95%+ de confianza
        if digit_count >= 6 and confidence >= 0.95:
            should_cleanup = True
            logger.info(f"LOG_AGGRESSIVE_CLEANUP: CRITICAL category HS{digit_count} code with {confidence:.0%} confidence (very high) → removing non-critical missing_fields")
        elif digit_count == 4 and confidence >= 0.98:
            should_cleanup = True
            logger.info(f"LOG_AGGRESSIVE_CLEANUP: CRITICAL category HS4 code with {confidence:.0%} confidence (extremely high) → removing non-critical missing_fields")
        else:
            logger.info(f"LOG_AGGRESSIVE_CLEANUP_SKIP: CRITICAL category code {code} with {confidence:.0%} confidence - preserve fields")
            should_cleanup = False
    elif digit_count >= 6 and confidence >= 0.75:
        # HS6 or more with 75%+ confidence
        should_cleanup = True
        logger.info(f"LOG_AGGRESSIVE_CLEANUP: HS{digit_count} code with {confidence:.0%} confidence → removing non-critical missing_fields")
    elif digit_count == 4 and confidence >= 0.85:
        # HS4 with very high confidence (85%+)
        should_cleanup = True
        logger.info(f"LOG_AGGRESSIVE_CLEANUP: HS4 code with {confidence:.0%} confidence (high) → removing non-critical missing_fields")
    
    if should_cleanup:
        # Get critical fields dynamically from templates based on HS code
        # This makes it scalable - just add new categories to missing_fields_templates.json
        critical_patterns = _get_critical_fields_for_code(code)
        
        # Keep only critical fields
        kept_fields = []
        for field in original_missing:
            field_lower = field.lower()
            is_critical = any(pattern in field_lower for pattern in critical_patterns)
            if is_critical:
                kept_fields.append(field)
                logger.info(f"LOG_AGGRESSIVE_CLEANUP: Keeping critical field: '{field}'")
        
        # SPECIAL: Para vehículos (8702, 8703, 8704), FORZAR pregunta de motor si no está especificado
        # PERO: VERIFICAR que el usuario YA NO respondió sobre motor en la conversación previa
        is_vehicle = any(str(cand.get("code", "")).startswith(("8702", "8703", "8704")) for cand in candidates)
        if is_vehicle:
            has_motor_question = any("motor" in f.lower() for f in kept_fields)
            has_motor_in_code_desc = "motor" in code.lower() or "motor" in top.get("description", "").lower()
            
            # CRÍTICO: Verificar si el usuario YA respondió sobre tipo de motor en el historial
            text_blob_with_history = _text_blob_from_query_history(query, conversation_history or [], include_assistant=False)
            motor_types = ["gasolina", "diesel", "diedel", "diessel", "electrico", "electrica", "hibrido", "hibrida", "nafta"]
            user_already_specified_motor = any(motor_type in text_blob_with_history for motor_type in motor_types)
            
            if not has_motor_question and not has_motor_in_code_desc and not user_already_specified_motor:
                # No preguntó por motor, no está en la descripción, y el usuario NO respondió previamente
                # FORZAR la pregunta
                kept_fields.append("¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)")
                logger.info(f"LOG_AGGRESSIVE_CLEANUP: FORCING motor question for vehicle code {code}")
            elif user_already_specified_motor:
                logger.info(f"LOG_AGGRESSIVE_CLEANUP: User already specified motor type in conversation - NOT forcing motor question")
        
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
    
    Estrategia REVISADA:
    - Base: 0.45 (categoría identificada)
    - +0.10 por cada detalle crítico respondido
    - Distingue entre campos CRÍTICOS (afectan HS6) y OPCIONALES (solo refinan a HS8/HS10)
    - Escala:
      * 0.45: Solo categoría identificada
      * 0.55: Categoría + 1 detalle crítico
      * 0.65: Categoría + 2 detalles críticos
      * 0.75: Categoría + 3+ detalles, campos críticos completos
      * 0.85: HS6 completo, solo faltan opcionales (nuevo/usado, cilindrada)
      * 0.95: HS10 completo (todos los detalles incluyendo opcionales)
    - Máximo: 0.95
    """
    import logging
    logger = logging.getLogger(__name__)
    
    base_confidence = 0.45
    
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
    
    # Ajuste por completitud: distinguir campos críticos vs opcionales
    fields_remaining = len(missing_fields_original)
    
    # Identificar si los campos faltantes son CRÍTICOS o solo refinamientos
    optional_keywords = [
        "nuevo", "usado", "usada", "seminuevo", "condición",  # Estado (solo HS10)
        "cilindrada", "cc", "cm3", "centímetros cúbicos",  # Cilindrada (solo HS10)
        "capacidad en litros", "litros", "capacidad",  # Capacidad exacta (opcional para HS6)
        "color", "marca", "modelo"  # Atributos no arancelarios
    ]
    
    critical_fields_remaining = 0
    optional_fields_remaining = 0
    for field in (missing_fields_original or []):
        field_lower = field.lower()
        is_optional = any(kw in field_lower for kw in optional_keywords)
        if is_optional:
            optional_fields_remaining += 1
        else:
            critical_fields_remaining += 1
    
    # Escala más precisa:
    # Base (0.45) + detalles respondidos (0.10 cada uno, máx 0.40)
    confidence = base_confidence + min(answered_details * 0.10, 0.40)
    
    # Penalizar SOLO por campos CRÍTICOS faltantes
    if critical_fields_remaining > 3:
        confidence *= 0.75  # Muchos campos críticos → máx ≈0.64
    elif critical_fields_remaining > 1:
        confidence *= 0.85  # Algunos campos críticos → máx ≈0.72
    elif critical_fields_remaining == 1:
        confidence *= 0.95  # Un campo crítico → máx ≈0.80
    elif critical_fields_remaining == 0 and optional_fields_remaining > 0:
        # HS6 completo, solo faltan opcionales → alta confianza fija
        confidence = 0.85  # HS6 clasificado correctamente, solo refinamiento pendiente
    # else: 0 campos faltantes (ya manejado arriba con 0.95)
    
    # Cap en 0.95, floor en 0.45
    final_confidence = min(0.95, max(0.45, confidence))
    
    logger.info(
        f"[CONFIDENCE_CALC] answered_details={answered_details}, "
        f"fields_remaining={fields_remaining} (critical={critical_fields_remaining}, optional={optional_fields_remaining}), "
        f"confidence={final_confidence:.2f}"
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





def _validate_category_consistency(result: Dict[str, Any], query: str, conversation_history: list | None = None) -> Dict[str, Any]:
    """Valida que la categoría sugerida sea consistente con el contexto de la conversación.
    
    PROBLEMA DETECTADO: Cuando hay poco contexto en la query actual pero mucho en el historial,
    el LLM puede confundirse y cambiar a categoría de vehículos (especialmente si hay palabras
    ambiguas como "capacidad").
    
    SOLUCIÓN: Si detectamos un cambio de categoría ilegítimo (ej: de laptop a vehículos),
    rechazamos los missing_fields de vehículos y mantenemos la categoría anterior.
    
    IMPORTANTE: Funcionará SIN historial también, detectando categoría solo del query/blob actual.
    """
    try:
        # Detectar categoría del query ACTUAL (lo que el usuario acaba de decir)
        query_lower = (query or "").lower()
        is_laptop_query = any(kw in query_lower for kw in [
            "laptop", "portátil", "computadora", "notebook", "ssd", "ram", "gb", "512", "16gb", 
            "intel", "core", "procesador", "dell", "xps", "almacenamiento", "ddr5", "nvme",
            "datos", "procesamiento", "batería", "pantalla", "4k", "oled", "i9", "ryzen", "cpu"
        ])
        is_electrodomestico_query = any(kw in query_lower for kw in ["lavadora", "microondas", "nevera", "horno", "voltaje", "kg", "carga frontal", "automática"])
        is_textil_query = any(kw in query_lower for kw in ["camiseta", "textil", "tela", "tejido", "prenda", "ropa", "algodon", "algodón", "poliester", "poliéster", "lana"])
        is_metal_query = any(kw in query_lower for kw in ["acero", "lamina", "lámina", "plancha", "chapa", "galvanizado", "bobina", "metal", "hierro"])
        
        # Detectar categoría del historial SI EXISTE
        history_is_laptop = False
        history_is_electrodomestico = False
        history_is_textil = False
        history_is_metal = False
        history_is_vehicle = False
        if conversation_history and len(conversation_history) > 0:
            history_text = _text_blob_from_query_history("", conversation_history, include_assistant=False).lower()
            history_text_norm = _normalize_text(history_text)
            history_is_laptop = any(kw in history_text for kw in ["laptop", "portátil", "computadora", "notebook", "dell", "xps", "ssd", "ram"])
            history_is_electrodomestico = any(kw in history_text for kw in ["lavadora", "automática", "carga frontal", "microondas"])
            history_is_textil = any(kw in history_text_norm for kw in ["camiseta", "textil", "tela", "tejido", "prenda", "ropa", "algodon", "poliester", "lana"])
            history_is_metal = any(kw in history_text_norm for kw in ["acero", "lamina", "plancha", "chapa", "galvanizado", "bobina", "metal", "hierro"])
            history_is_vehicle = any(kw in history_text_norm for kw in ["vehiculo", "auto", "camion", "camión", "bus", "autobus", "autobús", "moto"])
        
        # Detectar categoría sugerida por resultado
        missing_fields = result.get("missing_fields", [])
        missing_text = " ".join(missing_fields).lower()
        
        is_vehicle_suggestion = any(
            kw in missing_text 
            for kw in ["tipo de vehículo", "autobus", "automóvil", "camión", "cuántas personas", "personas puede transportar", "que tipo de vehiculo", "vehiculo"]
        )

        # Detectar categoría sugerida por código principal
        top = (result.get("top_candidates") or [{}])[0]
        code = str(top.get("code", ""))
        code_clean = code.replace(".", "")
        suggested_is_vehicle = code_clean.startswith("87")
        suggested_is_metal = code_clean.startswith(("72", "73", "74", "75", "76"))
        suggested_is_textil = (len(code_clean) >= 2 and code_clean[:2].isdigit() and 50 <= int(code_clean[:2]) <= 63)
        
        # EXTENSIÓN: Si el query es laptop, eliminar CUALQUIER pregunta de motor/vehículos
        # incluso si es genérica
        if is_laptop_query and "tipo de motor" in missing_text:
            logger.warning(f"LOG_VALIDATE_MOTOR_FILTER: Query is laptop, removing generic motor question")
            filtered_fields = [
                f for f in missing_fields
                if not any(kw in f.lower() for kw in ["tipo de motor", "motor", "gasolina", "diesel", "electrico", "hibrido"])
            ]
            result["missing_fields"] = filtered_fields if filtered_fields else []
            logger.warning(f"LOG_VALIDATE_MOTOR_FILTERED: Removed motor questions, kept {len(filtered_fields)} fields")
            return result
        
        logger.warning(f"LOG_VALIDATE: query_laptop={is_laptop_query}, history_laptop={history_is_laptop}, vehicle_sugg={is_vehicle_suggestion}")
        
        # VALIDACIÓN 1: Si el QUERY ACTUAL es claramente laptop/electrodoméstico, rechazar vehículos
        if (is_laptop_query or history_is_laptop) and is_vehicle_suggestion:
            logger.warning(f"LOG_CATEGORY_MISMATCH_DETECTED_QUERY_LEVEL: Query/History=laptop but suggestion=vehículos. Rejecting.")
            # Limpiar missing_fields de preguntas de vehículos
            filtered_fields = [
                f for f in missing_fields
                if not any(kw in f.lower() for kw in ["vehículo", "vehiculo", "autobus", "automovil", "automóvil", "camion", "camión", "personas puede transportar"])
            ]
            logger.warning(f"LOG_CATEGORY_FILTERED: Removed {len(missing_fields) - len(filtered_fields)} vehicle fields")
            result["missing_fields"] = filtered_fields if filtered_fields else []
            result["warnings"] = result.get("warnings", []) + ["⚠️ Detectado cambio de categoría - manteniendo contexto actual (laptop)"]
            return result
        
        # VALIDACIÓN 2: Si el QUERY ACTUAL es claramente electrodoméstico, rechazar vehículos
        if (is_electrodomestico_query or history_is_electrodomestico) and is_vehicle_suggestion:
            logger.warning(f"LOG_CATEGORY_MISMATCH_DETECTED_APPLIANCE_LEVEL: Query/History=appliance but suggestion=vehículos. Rejecting.")
            filtered_fields = [
                f for f in missing_fields
                if not any(kw in f.lower() for kw in ["vehículo", "vehiculo", "autobus", "automovil", "automóvil", "camion", "camión", "personas puede transportar"])
            ]
            logger.warning(f"LOG_CATEGORY_FILTERED: Removed {len(missing_fields) - len(filtered_fields)} vehicle fields")
            result["missing_fields"] = filtered_fields if filtered_fields else []
            result["warnings"] = result.get("warnings", []) + ["⚠️ Detectado cambio de categoría - manteniendo contexto actual (electrodoméstico)"]
            return result
        
        # VALIDACIÓN 3: Si el historial es textil y el resultado sugiere vehículos/otros, forzar preguntas textiles
        if (is_textil_query or history_is_textil) and (is_vehicle_suggestion or suggested_is_vehicle) and not history_is_vehicle:
            result["top_candidates"] = [{
                "code": "9999.00",
                "description": "Clasificación pendiente - Necesita más información",
                "confidence": min(float(top.get("confidence", 0.45)), 0.45),
                "level": "HS6",
                "years": top.get("years", [2025, 2026])
            }]
            result["missing_fields"] = [
                "¿De qué material está hecha la prenda? (algodón, poliéster, lana, mezcla)",
                "¿Es tejido de punto o tejido plano?",
                "¿Es camiseta u otra prenda específica?"
            ]
            result["warnings"] = result.get("warnings", []) + ["⚠️ Cambio de categoría detectado - manteniendo contexto textil"]
            return result

        # VALIDACIÓN 4: Si el historial es metal y el resultado sugiere vehículos/otros, forzar preguntas de metal
        if (is_metal_query or history_is_metal) and (is_vehicle_suggestion or suggested_is_vehicle) and not history_is_vehicle:
            result["top_candidates"] = [{
                "code": "9999.00",
                "description": "Clasificación pendiente - Necesita más información",
                "confidence": min(float(top.get("confidence", 0.45)), 0.45),
                "level": "HS6",
                "years": top.get("years", [2025, 2026])
            }]
            result["missing_fields"] = [
                "¿Cuál es el espesor en mm?",
                "¿Está galvanizado, pintado o sin recubrimiento?",
                "¿Laminado en caliente o en frío?"
            ]
            result["warnings"] = result.get("warnings", []) + ["⚠️ Cambio de categoría detectado - manteniendo contexto de metal"]
            return result

        logger.warning(f"LOG_VALIDATE_NO_MISMATCH: No category mismatch detected")
        return result
    except Exception as e:
        logger.error(f"Error in _validate_category_consistency: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return result


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
            
            # Soportar ambos formatos: tupla (user, assistant) y dict {user, assistant, timestamp}
            if isinstance(turn, dict):
                user_msg = turn.get("user")
            elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                user_msg = turn[0]
            
            # SOLO incluir el mensaje del usuario, NO lo que propuso el asistente
            # Esto evita que el LLM copie el resumen anterior como código
            if user_msg:
                history_lines.append(f"Turno {i}: Usuario dijo: {user_msg}")
                logger.info(f"[HISTORY_BUILD] Turno {i}: User='{user_msg[:80]}'")
        
        if history_lines:
            history_text = "\n".join(history_lines)
            logger.info(f"[HISTORY_COMPLETE] Built {len(history_lines)} lines for prompt")
        else:
            logger.info(f"[HISTORY_EMPTY] No history to include in prompt")

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

    # Construir texto completo del usuario para contexto conversacional
    all_user_text = query.lower()
    all_assistant_text = ""
    if conversation_history:
        for turn in conversation_history:
            if isinstance(turn, dict):
                user_part = str(turn.get("user", "")).lower()
                assistant_part = str(turn.get("assistant", "")).lower()
                all_user_text += " " + user_part
                all_assistant_text += " " + assistant_part
            elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                all_user_text += " " + str(turn[0]).lower()
                all_assistant_text += " " + str(turn[1]).lower()
    
    logger.info(f"[CONTEXT_AGGREGATE] all_user_text: {all_user_text[:150]}")

    # PROMPT MEJORADO CON CONTEXTO
    has_context = context_text.strip() != ""
    
    if has_context:
        # CON DOCUMENTOS: PROPONER CÓDIGOS
        # Agregar instrucción especial si es refinamiento y el tema es claramente vehículos
        refinement_instruction = ""
        priority_guidance = ""
        
        # all_user_text y all_assistant_text ya están construidos antes del if has_context
        logger.info(f"[CONTEXT_BUILD_WITH_DOCS] all_user_text: {all_user_text[:150]}")
        
        if is_refinement and history_text:
            q_low = (query or "").lower()
            # Detectar el capítulo del último código propuesto
            last_chapter = None
            last_code_match = re.search(r'\b(8[0-9]{3}|[0-9]{4})\b', all_assistant_text[::-1])  # Buscar de atrás hacia adelante
            if last_code_match:
                last_code_str = last_code_match.group(1)[::-1]  # Revertir porque buscamos al revés
                last_chapter = last_code_str[:2]
            
            logger.info(f"LOG_REFINEMENT_CONTEXT: last_chapter={last_chapter}, query='{query[:40]}'")
            
            # INSTRUCCIÓN GENERAL: Mantener el capítulo anterior PERO permitir cambio de partida si los detalles lo exigen
            if last_chapter:
                refinement_instruction = f"""
CONTEXTO ANTERIOR (para refinamiento):
{history_text}

INSTRUCCIÓN CRÍTICA: El usuario está REFINANDO la consulta anterior con nuevos detalles.
- El último código propuesto fue del CAPÍTULO {last_chapter}
- Esta nueva información ("{query}") es un DETALLE ADICIONAL del mismo producto
- MANTÉN el capítulo {last_chapter} SALVO que los detalles exijan cambio de PARTIDA
- Si los detalles cambian características FUNDAMENTALES (ej: de <10 plazas a ≥10 plazas en vehículos), DEBES cambiar la partida (8703→8702)
- Lee TODO el historial conversacional para acumular TODOS los detalles (plazas, motor, peso, etc.)

EJEMPLOS:
- Usuario: "vehículo" → Bot: "8703?" → Usuario: "es para 50 personas" → Bot DEBE cambiar a 8702 (autobús ≥10 plazas)
- Usuario: "vehículo" → Bot: "8703?" → Usuario: "es a diesel" → Bot mantiene 8703 pero ajusta subdivisión (.32 diesel)
- Usuario: "lavadora" → Bot: "8450?" → Usuario: "es de carga frontal" → Bot mantiene 8450 y ajusta subdivisión
"""
                
            # GUÍA ESPECÍFICA SOLO PARA VEHÍCULOS (capítulo 87) por su complejidad
            vehicle_terms = ["vehiculo", "vehículo", "vehiculos", "vehículos", "camion", "camión", "camioneta", "pickup", "remolque", "semirremolque", "bus", "autobus", "autobús", "microbus", "microbús", "tractor"]
            vehicle_context = any(t in all_user_text for t in vehicle_terms) or last_chapter == "87"
            
            if vehicle_context and last_chapter == "87":
                # Agregar guía específica para vehículos (subdivisiones complejas)
                refinement_instruction += """

GUÍA CRÍTICA PARA VEHÍCULOS (Capítulo 87):
Lee TODO el historial para acumular: plazas, motor, peso, uso.

PARTIDAS (código base según número de plazas):
- 8702: Autobuses, microbuses (≥10 plazas incluido conductor) ← Si tiene ≥10 plazas, DEBE ser 8702
- 8703: Automóviles de turismo (<10 plazas) ← Solo si tiene <10 plazas
- 8704: Camiones y vehículos de carga (diseñados para transporte de mercancías)
- 8711: Motocicletas

SUBDIVISIONES por tipo de motor (después de definir partida):
- .21/.31: Gasolina con encendido por chispa
- .22/.32: Diesel
- .23/.33: Eléctrico puro
- .24/.34: Híbrido

PROCESO:
1. PRIMERO: Determina PARTIDA correcta (8702 si ≥10 plazas, 8703 si <10 plazas, 8704 si carga)
2. SEGUNDO: Ajusta SUBDIVISIÓN según motor (gasolina, diesel, eléctrico)
3. TERCERO: Ajusta dígitos finales según nuevo/usado

EJEMPLO CORRECTO:
- Usuario: "vehículo" → Bot: "¿Cuántas plazas?"
- Usuario: "50 personas, diesel, nuevo" → Bot DEBE clasificar: 8702.xx (autobús ≥10 plazas, NO 8703)
"""
        
        # Extraer contexto acumulado del historial - SOLO MENSAJES DEL USUARIO
        accumulated_context = ""
        if conversation_history and len(conversation_history) > 0:
            user_messages = []
            for turn in conversation_history:
                if isinstance(turn, dict):
                    user_msg = turn.get("user", "")
                elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                    user_msg = turn[0]
                else:
                    user_msg = ""
                if user_msg:
                    user_messages.append(str(user_msg))
            
            if user_messages:
                accumulated_context = " + ".join(user_messages)
                logger.info(f"[ACCUMULATED_CONTEXT] {accumulated_context}")
        
        # Detectar si la query es sobre vehículos para incluir lógica específica
        query_norm = _normalize_text(query)
        history_text_norm = _normalize_text(_text_blob_from_query_history(query, conversation_history, include_assistant=False))
        
        is_vehicle_query = any(kw in query_norm or kw in history_text_norm 
                               for kw in ["vehiculo", "auto", "coche", "camion", "bus", "autobus", "motocicleta", "carro"])
        
        vehicle_logic = ""
        if is_vehicle_query:
            vehicle_logic = """
LÓGICA DE CLASIFICACIÓN PARA VEHÍCULOS (Capítulo 87):
- Si dice "vehículo" O "auto" O "coche" O "camión" O "bus" O "autobús":
  * Si menciona ≥10 personas/plazas (ej: "50 personas", "40 asientos") → INMEDIATAMENTE 8702.xx (autobús)
  * Si menciona <10 personas/plazas (ej: "5 personas") → INMEDIATAMENTE 8703.xx (automóvil)
  * Si menciona carga/mercancías → INMEDIATAMENTE 8704.xx (camión)

IMPORTANTE - PASOS ORDENADOS:
1. PRIMERO: Determina PARTIDA (8702, 8703, 8704) basado en plazas/personas
   - Si dice "50 personas" → 8702 (PUNTO)
   - Si dice "4 personas" → 8703 (PUNTO)
   - NO ESPERES CILINDRADA PARA ESTO
2. SEGUNDO: Refina SUBDIVISIÓN (.21, .22, .23, .24) con motor si lo menciona
   - "diesel" → .22 o .32
   - "gasolina" → .21 o .31
   - Sin motor → usa .90 genérico
3. CILINDRADA: Opcional, solo refina dígitos finales, NO determina 8702 vs 8703

REGLA CRÍTICA: "Si el usuario mencionó plazas/personas, CLASIFICA YA. No esperes cilindrada."

INSTRUCCIONES ESPECÍFICAS PARA VEHÍCULOS:
1. Lee información completa sobre el vehículo
2. Extrae: tipo_vehículo, plazas, motor, cilindrada
3. Si tienes plazas → determina partida inmediatamente
4. Si tienes motor → añade subdivisión
5. PROPÓN CÓDIGO SIEMPRE (incluso si no tienes todos los detalles)

EJEMPLO CORRECTO DE RESPUESTA:
Input: "Vehículo para 50 personas, motor diesel, nuevo"
Output JSON:
{{
  "top_candidates": [
    {{
      "code": "8702.32",
      "description": "Autobús nuevo",
      "confidence": 0.85,
      "level": "HS6"
    }}
  ],
  "missing_fields": [],
  "applied_rgi": ["RGI 1"],
  "inclusions": [],
  "exclusions": [],
  "warnings": []
}}
"""
        
        prompt = f"""Eres experto en clasificación arancelaria (Sistema Armonizado - HS).

═══════════════════════════════════════════════════════════════════════════════
🚨 PRODUCTO A CLASIFICAR (INFORMACIÓN COMPLETA):
{accumulated_context + " + " + query if accumulated_context else query}
═══════════════════════════════════════════════════════════════════════════════

DOCUMENTOS ARANCELARIOS DE REFERENCIA:
{context_text}
{vehicle_logic}
**INSTRUCCIÓN CRÍTICA SOBRE DESCRIPCIONES:**
- NO incluyas detalles que NO hayan sido EXPLÍCITAMENTE mencionados por el usuario
- Si tienes duda sobre un detalle (ej: tipo de motor), NO lo escribas en la descripción
- La descripción debe ser GENÉRICA cuando falten confirmaciones: "Autobús" (NO "Autobús con motor diesel")
- Solo incluye en descripción lo que el usuario confirmó DIRECTAMENTE

NOTA IMPORTANTE:
- El campo "code" DEBE contener SOLO el código arancelario (ej: "8702.32", "9999.00", "8703.21")
- El campo "code" NUNCA debe contener "Código:" o "Preguntó:" o descripción
- La descripción completa va en el campo "description"

FORMATO JSON (RESPUESTA OBLIGATORIA):
{{
  "top_candidates": [{{"code": "XXXX.XX", "description": "...", "confidence": 0.XX, "level": "HS6"}}],
  "missing_fields": ["Si falta información crítica para clasificar"],
  "applied_rgi": ["RGI 1"],
  "inclusions": [],
  "exclusions": [],
  "warnings": []
}}"""
        logger.info(f"LOG_PROMPT: Refinement={is_refinement}, Context_len={len(context_text)}, Query={query[:80]}")
        logger.info(f"[PROMPT_FULL] ==========\n{prompt}\n==========")
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
        logger.info(f"[PROMPT_TO_LLM] ===INICIO===\n{prompt}\n===FIN===")
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
        logger.info(f"LOG_LLM_RESPONSE_FULL: {choice}")  # Log completo para debug
        
        # Intentar parsear JSON
        try:
            parsed = json.loads(choice or "{}")
        except json.JSONDecodeError as e:
            logger.error(f"LOG_LLM_JSON_ERROR: Failed to parse LLM response: {e}")
            logger.error(f"LOG_LLM_RAW_RESPONSE: {choice}")
            parsed = {}
        
        logger.info(f"LOG_LLM_PARSED: top_candidates={len(parsed.get('top_candidates', []))} items, missing_fields={len(parsed.get('missing_fields', []))} items")
        
        # Debugging: Log candidatos si existen
        if parsed.get('top_candidates'):
            for idx, cand in enumerate(parsed['top_candidates']):
                logger.info(f"LOG_LLM_CANDIDATE_{idx}: code={cand.get('code')}, confidence={cand.get('confidence')}, desc={cand.get('description', '')[:50]}")
        else:
            logger.warning(f"LOG_LLM_NO_CANDIDATES_IN_RESPONSE: LLM returned no candidates!")
            logger.warning(f"LOG_LLM_MISSING_FIELDS: {parsed.get('missing_fields', [])}")
            logger.warning(f"LOG_LLM_WARNINGS: {parsed.get('warnings', [])}")
        
        # Normalizar y procesar respuesta
        norm = _normalize_result_fields(parsed, evidence)
        
        # VALIDACIÓN CRÍTICA: Si el LLM no devolvió candidatos, forzar un fallback inteligente
        if not norm.get("top_candidates") or len(norm.get("top_candidates", [])) == 0:
            logger.warning(f"LOG_LLM_NO_CANDIDATES: LLM returned empty candidates list!")
            blob = _text_blob_from_query_history(query, conversation_history, include_assistant=False)
            norm = _apply_rule_based_fallback(norm, query, conversation_history)
            
            # Si AÚN no hay candidatos después del fallback, crear uno genérico
            if not norm.get("top_candidates") or len(norm.get("top_candidates", [])) == 0:
                logger.error(f"LOG_EMERGENCY_FALLBACK: Creating emergency generic candidate")
                norm["top_candidates"] = [{
                    "code": "9999.00",
                    "description": "Clasificación pendiente - Necesita más información",
                    "confidence": 0.10,
                    "level": "HS6",
                    "years": [2025, 2026]
                }]
                norm.setdefault("warnings", []).append("No se pudo determinar clasificación automática")
        
        norm = _apply_device_overrides(norm, query, conversation_history)
        norm = _ensure_missing_fields(norm, query, conversation_history)
        norm = _apply_device_overrides(norm, query, conversation_history)
        norm = _aggressive_missing_fields_cleanup(norm, query, conversation_history)
        norm = _prune_missing_fields(norm, query, conversation_history)
        
        # Refinar confianza y códigos basados en detalles respondidos
        # CRÍTICO: Calcular confianza DESPUÉS de _ensure_missing_fields para usar los campos finales
        blob = _text_blob_from_query_history(query, conversation_history, include_assistant=False)
        candidates = norm.get("top_candidates") or []
        if candidates:
            top_cand = candidates[0]
            
            # Usar missing_fields FINALES (después de _ensure_missing_fields que agrega campos de microondas)
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
                        assistant_text = None
                        if isinstance(turn, dict):
                            assistant_text = turn.get("assistant") or ""
                        elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
                            assistant_text = turn[1] or ""
                        
                        # Extraer código del formato "Código: 8516.60 (...)" o similar
                        if assistant_text:
                            import re as _re
                            code_match = _re.search(r"(?:código|code):\s*([0-9.]+)", assistant_text, re.IGNORECASE)
                            if code_match:
                                prev_code = code_match.group(1)
                                break
                
                if prev_code:
                    # Normalizar y comparar especificidad (cantidad de dígitos sin puntos)
                    import re as _re
                    def _digits(c: str):
                        return ''.join(_re.findall(r"\d", c or ""))
                    prev_digits = _digits(prev_code)
                    curr_digits = _digits(top_cand.get("code") or "")
                    # Si pertenecen al mismo capítulo y el previo es más largo O IGUAL (mismo código), conservarlo
                    # Esto evita cambios de código cuando el sistema está correcto
                    if prev_digits[:4] == curr_digits[:4] and len(prev_digits) >= len(curr_digits):
                        logger.info(f"LOG_PRESERVE_SPECIFIC: Keeping previous code {prev_code} over {top_cand.get('code')}")
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
        
        # Guard final: asegurar pregunta de capacidad para microondas si falta
        try:
            final_blob = _text_blob_from_query_history(query, conversation_history, include_assistant=False)
            is_microondas = any(kw in final_blob for kw in ["microondas", "microonda", "horno microonda", "horno de microondas"])
            has_liters = (
                bool(re.search(r"\b\d+(?:[\.,]\d+)?\s*(l|litros?)\b", final_blob))
                or any(kw in final_blob for kw in ["litro", "litros", "capacidad"])
            )
            missing_fields = norm.get("missing_fields") or []
            already_asks_liters = any(
                "litro" in _normalize_text(f) or "capacidad" in _normalize_text(f)
                for f in missing_fields
            )
            if is_microondas and not has_liters and not already_asks_liters:
                norm["missing_fields"] = ["¿Cuál es la capacidad en litros?"] + missing_fields
        except Exception:
            pass

        logger.info(f"LOG_LLM_FINAL: top_candidates={len(norm.get('top_candidates', []))} items")
        
        # VALIDACIÓN DEFENSIVA: Detectar y prevenir cambios de categoría ilegítimos
        norm = _validate_category_consistency(norm, query, conversation_history)
        
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
