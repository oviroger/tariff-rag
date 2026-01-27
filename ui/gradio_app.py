"""
Gradio UI for Tariff RAG system.
Provides both static form and conversational chatbot interfaces.
"""

import gradio as gr
import requests
from typing import Any, Tuple, Dict, Optional
import json
import re
from uuid import uuid4

API_URL = "http://api:8000"

class ConversationState:
    """Manages conversation history and context."""
    def __init__(self):
        self.last_classification: Optional[Dict[str, Any]] = None
        self.last_query: str = ""
        self.history: list[tuple[str, str]] = []  # NUEVO: historial completo (user, assistant)
    
    def update(self, query: str, result: Dict[str, Any]):
        self.last_query = query
        self.last_classification = result

    def add_turn(self, user_message: str, assistant_message: str):
        self.history.append((user_message, assistant_message))

    def add_classification_summary(self, user_message: str, result: Dict[str, Any]):
        cand = (result.get("top_candidates") or result.get("candidates") or [])
        top = cand[0] if cand else {}
        code = top.get("code") or top.get("hs_code") or "N/A"
        msg = f"Código sugerido: {code}."
        self.add_turn(user_message, msg)

    def has_context(self) -> bool:
        return bool(self.last_classification or self.last_query or self.history)
    
    def get_history_for_api(self) -> list:
        """Convierte historial de tuplas a formato que espera el backend."""
        from datetime import datetime
        return [
            {"user": user, "assistant": assistant, "timestamp": datetime.now().isoformat()}
            for user, assistant in self.history
        ]

    def reset(self):
        self.last_classification = None
        self.last_query = ""
        self.history = []

# Store conversation states indexed by conversation_id
# This ensures each conversation has its own context, preventing cross-contamination
_conversation_states: Dict[str, ConversationState] = {}

def get_conversation_state(conv_id: str) -> ConversationState:
    """Get or create a ConversationState for the given conversation_id."""
    if conv_id not in _conversation_states:
        _conversation_states[conv_id] = ConversationState()
    return _conversation_states[conv_id]

def reset_conversation_state(conv_id: str):
    """Reset the conversation state for the given conversation_id."""
    if conv_id in _conversation_states:
        _conversation_states[conv_id].reset()
    else:
        _conversation_states[conv_id] = ConversationState()

# Legacy: for backward compatibility with chat_response() function
conv_state = ConversationState()


def _history_to_api_format(history: list) -> list:
    """Convierte historial de Gradio [(user, assistant), ...] a formato esperado por la API."""
    from datetime import datetime
    formatted = []
    for turn in history or []:
        if isinstance(turn, (list, tuple)) and len(turn) >= 2:
            u, a = turn[0], turn[1]
        else:
            continue
        formatted.append({
            "user": u or "",
            "assistant": a or "",
            "timestamp": datetime.now().isoformat()
        })
    return formatted


def _strip_accents_ui(s: str) -> str:
    try:
        import unicodedata
        return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode('utf-8')
    except Exception:
        return s or ""


def _prune_missing_fields_ui(result: Dict[str, Any], message: str, history: list) -> Dict[str, Any]:
    """Prune missing_fields in UI when the user already provided data in the latest turn/history."""
    text_parts = [message or ""]
    for turn in history or []:
        if isinstance(turn, (list, tuple)) and len(turn) >= 2:
            text_parts.append(turn[0] or "")
            # No agregamos la respuesta del asistente para evitar reinsertar las preguntas
    blob = _strip_accents_ui(" ".join(text_parts).lower())

    motor_keywords = [
        "diesel", "diesl", "diessel", "diseel", "dieesl", "disel",
        "gasolina", "electrico", "electrica", "electric", "electr",
        "hibrido", "hibrida", "hibrid"
    ]
    has_motor = any(k in blob for k in motor_keywords)
    has_seats = bool(
        re.search(r"\b\d{1,3}\s*(pasajero|pasajeros|plaza|plazas)\b", blob)
        or re.search(r"\b(un|una|uno)\s+(pasajero|pasajeros|plaza|plazas)\b", blob)
        or re.search(r"para\s+(un|una|uno)\s+(pasajero|pasajeros|plaza|plazas)\b", blob)
    )

    pruned = []
    for field in result.get("missing_fields", []) or []:
        f_norm = _strip_accents_ui(str(field)).lower()
        if has_motor and "motor" in f_norm:
            continue
        if has_seats and ("plaza" in f_norm or "pasajero" in f_norm):
            continue
        pruned.append(field)

    result["missing_fields"] = pruned
    return result

def is_tariff_related(text: str) -> Tuple[bool, str]:
    """Valida si el texto parece relacionado con clasificación arancelaria. Devuelve (ok, mensaje)."""
    text_lower = (text or "").lower().strip()

    if len(text_lower.split()) < 2:
        return False, "Por favor, proporciona más detalles sobre el producto o tu consulta."

    tariff_keywords = [
        "clasificar", "clasificación", "código hs", "partida arancelaria",
        "sistema armonizado", "tariff", "hs code", "harmonized system",
        "arancel", "aduana", "importación", "exportación",
        "rgi", "reglas generales", "general rules"
    ]
    has_tariff_keyword = any(kw in text_lower for kw in tariff_keywords)

    product_indicators = [
        "acero", "steel", "aluminio", "plástico", "madera", "textil",
        "algodón", "cuero", "vidrio", "cerámica", "papel",
        "lámina", "plancha", "tubo", "cable", "máquina", "dispositivo",
        "aparato", "equipo", "vehículo", "neumático", "batería",
        "laminado", "fundido", "tejido", "procesado", "manufacturado",
        "galvanizado", "recubierto", "pintado"
    ]
    has_product_indicator = any(ind in text_lower for ind in product_indicators)

    off_topic_patterns = [
        "quién es", "quien es", "quiénes son", "biografía de",
        "qué es python", "qué es javascript", "cómo programar",
        "quién ganó", "partido de", "resultado del",
        "últimas noticias", "qué pasó con", "actualidad",
    ]
    for pattern in off_topic_patterns:
        if pattern in text_lower:
            return False, (
                "❌ **Esta pregunta no está relacionada con clasificación arancelaria.**\n\n"
                "**Este sistema se especializa en:**\n"
                "- Clasificar productos según el Sistema Armonizado (HS)\n"
                "- Asignar códigos arancelarios\n"
                "- Explicar reglas de interpretación (RGI)\n"
                "- Identificar partidas y subpartidas\n\n"
                "**Ejemplos válidos:**\n"
                "- *Láminas de acero laminadas en caliente, 2mm*\n"
                "- *¿Cuáles son las reglas generales de clasificación?*\n"
                "- *Smartphone con pantalla OLED, 128GB almacenamiento*\n"
                "- *¿Qué es la RGI 3?*"
            )

    famous_names = [
        "messi", "ronaldo", "maradona", "pelé", "neymar",
        "einstein", "newton", "tesla", "curie",
        "biden", "trump", "macron"
    ]
    words = text_lower.split()
    if len(words) <= 3 and any(name in text_lower for name in famous_names):
        return False, (
            f"❌ **'{text}' parece referirse a una persona, no a un producto.**\n\n"
            "**¿Buscas clasificar productos relacionados?**\n"
            "- Camisetas deportivas con logos\n"
            "- Libros o biografías impresas\n"
            "- Fotografías o posters\n"
            "- Artículos deportivos\n\n"
            "Describe el **producto físico** que necesitas clasificar."
        )

    if has_tariff_keyword or has_product_indicator:
        return True, ""

    return True, ""

def ensure_conv_id(conv_id: Optional[str]) -> str:
    """Genera un nuevo conversation_id si no existe."""
    if not conv_id or conv_id.strip() == "":
        return uuid4().hex
    return conv_id

def is_followup_question(message: str) -> bool:
    """Detecta si el mensaje es una pregunta de seguimiento o aporta datos que completan la clasificación."""
    message_lower = message.lower().strip()

    followup_patterns = [
        "por qué", "porque", "razón", "justifica", "explica",
        "traduc", "inglés", "español",
        "resumen", "resume", "sintetiza",
        "alternativa", "otro código", "otras opciones",
        "qué falta", "qué información falta", "información falta",
        "información adicional", "más detalles", "detalles faltantes", "campos faltantes",
    ]
    if any(p in message_lower for p in followup_patterns):
        return True

    vehicle_info_patterns = [
        r"\btipo de veh[ií]culo\b|\bes una moto\b|\bes una motocicleta\b|\bes un autom[oó]vil\b|\bes un camion\b|\bes un cami[oó]n\b",
        r"\buso del veh[ií]culo\b|\btransporte de personas\b|\btransporte de mercanc[ií]as\b|\buso especial\b",
        r"\bcilindrada\b|\bpotencia\b|\btipo de motor\b|\bgasolina\b|\bd[ií]esel\b|\bh[ií]brido\b|\bhev\b|\bphev\b|\bel[eé]ctrico\b|\bev\b",
        r"\bpeso\b|\bpeso bruto\b|\bmasa\b|\bcarga [uú]til\b",
        r"\bcompleto\b|\bincompleto\b|\bchasis\b|\bcabina\b|\bsidecar\b",
        r"\bnuevo\b|\bnueva\b|\busado\b|\busada\b",
    ]
    import re
    for pat in vehicle_info_patterns:
        if re.search(pat, message_lower):
            return True

    if conv_state.has_context():
        word_count = len(message.split())
        if word_count <= 12:
            last_missing = (conv_state.last_classification or {}).get("missing_fields", [])
            if last_missing:
                return True

        last_missing_text = " ".join((conv_state.last_classification or {}).get("missing_fields", [])).lower()
        keywords = ["tipo", "uso", "cilindrada", "motor", "peso", "nuevo", "nueva", "usado", "usada", "completo", "incompleto", "sidecar"]
        if any(k in message_lower for k in keywords) and any(k in last_missing_text for k in keywords):
            return True

    return False

def handle_followup_question(question: str, last_result: Dict) -> str:
    """
    Genera respuestas a preguntas de seguimiento basadas en la última clasificación.
    """
    question_lower = question.lower()
    
    # Get candidates with both possible field names
    candidates = last_result.get("top_candidates", last_result.get("candidates", []))
    
    # Translation request
    if "traduc" in question_lower or "español" in question_lower:
        response = "### 🌐 Resumen en Español\n\n"
        if candidates:
            response += "**📊 Códigos HS:**\n\n"
            incisos = ['a', 'b', 'c', 'd', 'e']
            for idx, cand in enumerate(candidates[:3]):
                hs_code = cand.get('code', cand.get('hs_code', 'N/A'))
                confidence = cand.get('confidence', 0)
                
                conf_emoji = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.5 else "🔴"
                inciso = incisos[idx] if idx < len(incisos) else str(idx + 1)
                response += f"{conf_emoji} **{inciso}) {hs_code}** ({confidence:.0%} confianza)\n\n"
        
        if last_result.get("inclusions"):
            response += "**✅ Incluye:**\n"
            for inc in last_result["inclusions"]:
                response += f"- {inc}\n"
            response += "\n"
        
        if last_result.get("missing_fields"):
            response += "**🔍 Información requerida:**\n"
            for field in last_result["missing_fields"][:3]:
                response += f"- {field}\n"
        
        return response
    
    # Why this code?
    elif "por qué" in question_lower or "porque" in question_lower:
        response = "### 🤔 ¿Por qué estos códigos?\n\n"
        if last_result.get("applied_rgi"):
            response += f"Se aplicaron las reglas: **{', '.join(last_result['applied_rgi'])}**\n\n"
        if candidates:
            top = candidates[0]
            hs_code = top.get('code', top.get('hs_code', 'N/A'))
            response += f"El código principal **{hs_code}** se eligió porque:\n\n"
            if last_result.get("inclusions"):
                response += "**✅ Incluye:**\n"
                response += "- " + "\n- ".join(last_result["inclusions"]) + "\n\n"
            if last_result.get("exclusions"):
                response += "**❌ Excluye:**\n"
                response += "- " + "\n- ".join(last_result["exclusions"]) + "\n"
        return response
    
    # What's missing?
    elif "falta" in question_lower or "adicional" in question_lower:
        response = "### 🔍 Información Faltante\n\n"
        if last_result.get("missing_fields"):
            for field in last_result["missing_fields"]:
                response += f"- {field}\n"
            response += "\n💡 Proporciona estos detalles para una clasificación más precisa."
        else:
            response += "✅ No se identificaron campos faltantes críticos."
        return response
    
    # Alternatives?
    elif "alternativa" in question_lower or "otras opciones" in question_lower:
        response = "### 🔄 Códigos Alternativos\n\n"
        if candidates and len(candidates) > 1:
            incisos = ['b', 'c', 'd', 'e', 'f']  # Empezar desde 'b' porque 'a' es el principal
            for idx, cand in enumerate(candidates[1:4]):
                hs_code = cand.get('code', cand.get('hs_code', 'N/A'))
                confidence = cand.get('confidence', 0)
                description = cand.get('description', '')
                inciso = incisos[idx] if idx < len(incisos) else str(idx + 2)
                response += f"**{inciso}) {hs_code}** ({confidence:.1%})\n"
                # Solo mostrar descripción si no está vacía
                if description and description.strip():
                    response += f"   {description}\n\n"
                else:
                    response += "\n"
        else:
            response += "No se encontraron alternativas con suficiente confianza."
        return response
    
    # Summary/simplification
    elif "resume" in question_lower or "simplifica" in question_lower:
        response = "### 📝 Resumen Simplificado\n\n"
        if candidates:
            top = candidates[0]
            hs_code = top.get('code', top.get('hs_code', 'N/A'))
            confidence = top.get('confidence', 0)
            response += f"**Código recomendado: {hs_code}** ({confidence:.0%} confianza)\n\n"
            
            # Extract key info from inclusions
            if last_result.get("inclusions") and len(last_result["inclusions"]) > 0:
                response += "**Criterio principal:** " + last_result["inclusions"][0]
            
        return response
    
    # Default: show summary
    else:
        return ("🤔 No entendí tu pregunta. Intenta:\n"
                "- ¿Por qué este código?\n"
                "- ¿Qué información falta?\n"
                "- ¿Hay alternativas?\n"
                "- Dame un resumen")

def format_classification_markdown(result: Dict[str, Any]) -> str:
    """Construye un markdown detallado a partir del resultado de /classify."""
    md = ""
    candidates = result.get("top_candidates") or result.get("candidates") or []
    
    # Recolectar TODOS los años únicos de las evidencias Y del campo years directo
    years_found = set()
    
    # Opción 1: Usar el campo 'years' directo de la respuesta
    if result.get("years"):
        years_found.update(result.get("years"))
    
    # Opción 2: Buscar en support_evidence
    for ev in (result.get("support_evidence") or []):
        y = ev.get("year")
        if y:
            years_found.add(y)
    
    # Opción 3: Buscar en evidence/context_docs
    for ev in (result.get("evidence") or result.get("context_docs") or []):
        y = ev.get("year") or (ev.get("_source", {}) or {}).get("year")
        if y:
            years_found.add(y)
    
    # Opción 4: Buscar en años de candidatos
    for cand in candidates:
        if cand.get("years"):
            years_found.update(cand.get("years"))
    
    # Formatear años ordenados
    years_str = ""
    if years_found:
        sorted_years = sorted(years_found)
        years_str = f" | 📅 Referencia: {', '.join(map(str, sorted_years))}"
    
    if candidates:
        md += "## 🎯 Clasificación sugerida\n\n"
        incisos = ["a", "b", "c"]
        for idx, cand in enumerate(candidates[:3]):
            hs_code = cand.get('code') or cand.get('hs_code') or 'N/A'
            confidence = float(cand.get('confidence', 0.0))
            description = (
                cand.get('description')
                or cand.get('desc')
                or cand.get('product_description')
                or ''
            )
            level = cand.get('level', '')

            if confidence > 0.7:
                conf_emoji = "🟢"
            elif confidence > 0.5:
                conf_emoji = "🟡"
            else:
                conf_emoji = "🔴"

            inciso = incisos[idx] if idx < len(incisos) else str(idx + 1)
            md += f"{conf_emoji} **{inciso}) {hs_code}**{years_str} (Confianza: {confidence:.1%})\n"
            if description and description.strip():
                md += f"   *{description}*\n"
            if level:
                md += f"   📊 Nivel: {level}\n"
            md += "\n"

        inclusions = result.get("inclusions", [])
        exclusions = result.get("exclusions", [])
        if inclusions or exclusions:
            md += "### 📋 Criterios de Clasificación\n\n"
            if inclusions:
                md += "**✅ Incluye:**\n"
                for inc in inclusions:
                    md += f"- {inc}\n"
                md += "\n"
            if exclusions:
                md += "**❌ Excluye:**\n"
                for exc in exclusions:
                    md += f"- {exc}\n"
                md += "\n"
    else:
        md += "⚠️ No se generaron códigos candidatos. La consulta puede ser demasiado general.\n\n"

    if result.get("applied_rgi"):
        md += "### ⚖️ RGI Aplicadas\n\n"
        md += "- " + "\n- ".join(result["applied_rgi"]) + "\n\n"

    if result.get("missing_fields"):
        md += "### 🔍 Información adicional requerida\n\n"
        for m in result["missing_fields"][:5]:
            md += f"- {m}\n"
        md += "\n"

    if result.get("warnings"):
        md += "### ⚠️ Advertencias\n\n"
        for w in result["warnings"][:5]:
            md += f"- {w}\n"
        md += "\n"

    ev_md = render_evidence_markdown(result)
    if ev_md:
        md += "\n" + ev_md

    return md or "Sin resultados."

def classify(description: str, hs: str):
    """Wrapper para el formulario clásico: llama a /classify y retorna JSONs separados."""
    try:
        query = (description or "").strip()
        payload = {"user_query": query, "top_k": 5, "conversation_history": conv_state.get_history_for_api()}
        resp = requests.post(f"{API_URL}/classify", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        cands = data.get("top_candidates") or data.get("candidates") or []
        evid = data.get("evidence") or data.get("context_docs") or []
        rgi = data.get("applied_rgi", [])
        miss = data.get("missing_fields", [])
        warn = data.get("warnings", [])
        return cands, evid, rgi, miss, warn
    except requests.RequestException as e:
        err = str(e)
        return [], [], [], [], [f"Error al llamar API: {err}"]

def chat_response(message: str, history: list, years: Optional[list] = None) -> str:
    """
    Main chatbot response function.
    Handles both classification requests and follow-up questions.
    """
    if not message or not message.strip():
        return "Por favor, escribe una consulta sobre clasificación arancelaria."
    
    message = message.strip()
    message_lower = message.lower()
    
    # Convertir años de string a int si es necesario (Gradio pasa como strings)
    years_list = None
    if years:
        try:
            years_list = [int(y) if isinstance(y, str) else y for y in years if str(y).strip()]
            if not years_list:  # Si la lista quedó vacía, buscar en todos los años
                years_list = None
        except (ValueError, TypeError):
            years_list = None
    
    # Detectar comandos de reset/nueva conversación
    reset_keywords = [
        "olvida", "olvidar", "olvida todo", "borra", "borrar",
        "nueva conversación", "nueva consulta", "empezar de nuevo",
        "reiniciar", "reset", "clear", "limpiar", "iniciar nueva",
        "quiero iniciar", "vamos a iniciar"
    ]
    
    if any(keyword in message_lower for keyword in reset_keywords):
        conv_state.reset()
        return (
            "✅ **Conversación reiniciada**\n\n"
            "He borrado el contexto anterior. Ahora puedes hacer una nueva consulta sobre "
            "clasificación arancelaria.\n\n"
            "**Ejemplos de consultas:**\n"
            "- Láminas de acero laminadas en caliente, 2mm de espesor\n"
            "- Neumáticos radiales para automóvil 205/55R16\n"
            "- Smartphones con pantalla OLED, 128GB\n"
        )

    # Check if it's a follow-up question about previous classification
    if is_followup_question(message) and conv_state.last_classification:
        try:
            last_result = conv_state.last_classification or {}
            msg_l = message.lower()

            # 1) Pregunta explícita sobre información faltante: responder directo sin reclasificar
            if any(k in msg_l for k in ["qué falta", "que falta", "información", "faltante", "detalles", "adicional"]):
                missing = last_result.get("missing_fields", [])
                if missing:
                    reply = "### 🔍 Información Adicional Requerida\n\n" + "\n".join(f"- {m}" for m in missing)
                else:
                    reply = "✅ No se identificaron campos faltantes críticos."
                conv_state.add_turn(message, reply)
                return reply

            # 2) Pregunta de justificación/por qué
            if any(k in msg_l for k in ["por qué", "porque", "razón", "justifica", "explica"]):
                applied = last_result.get("applied_rgi", [])
                inclusions = last_result.get("inclusions", [])
                parts = []
                if applied:
                    parts.append(f"Se aplicaron: {', '.join(applied)}.")
                if inclusions:
                    parts.append("Incluye:\n" + "\n".join(f"- {i}" for i in inclusions))
                reply = "### 🤔 ¿Por qué estos códigos?\n\n" + ("\n\n".join(parts) or "La descripción coincide con la partida propuesta.")
                conv_state.add_turn(message, reply)
                return reply

            # 3) Alternativas
            if any(k in msg_l for k in ["alternativa", "otras opciones", "otro código", "otro codigo"]):
                candidates = last_result.get("top_candidates") or last_result.get("candidates") or []
                if len(candidates) > 1:
                    lines = []
                    for c in candidates[1:]:
                        code = c.get("code") or c.get("hs_code")
                        conf = float(c.get("confidence", 0)) * 100
                        lines.append(f"- {code} (Confianza: {conf:.0f}%)")
                    reply = "### 🔄 Códigos Alternativos\n\n" + "\n".join(lines)
                else:
                    reply = "No hay alternativas con suficiente confianza."
                conv_state.add_turn(message, reply)
                return reply

            # 4) Resumen
            if any(k in msg_l for k in ["resumen", "resume", "simplifica", "sintetiza"]):
                candidates = last_result.get("top_candidates") or last_result.get("candidates") or []
                if candidates:
                    main = candidates[0]
                    code = main.get("code") or main.get("hs_code")
                    conf = float(main.get("confidence", 0)) * 100
                    reply = f"### 📝 Resumen\n\nCódigo recomendado: {code} (Confianza: {conf:.0f}%)."
                else:
                    reply = "No hay resumen disponible."
                conv_state.add_turn(message, reply)
                return reply

            # 5) Caso general: parece que el usuario aportó nuevos datos -> reclasificar con query enriquecida
            last_missing = last_result.get("missing_fields", [])
            if last_missing and len(message.split()) <= 12:
                improved_query = (
                    f"{conv_state.last_query}. Info adicional del usuario: {message}. "
                    f"Antes faltaba: {', '.join(last_missing)}."
                )
            else:
                improved_query = f"{conv_state.last_query}. {message}"

            payload = {
                "user_query": improved_query, 
                "top_k": 5,
                "conversation_history": _history_to_api_format(history)
            }
            if years_list:
                payload["years"] = years_list
            resp = requests.post(f"{API_URL}/classify", json=payload, timeout=60)
            resp.raise_for_status()
            data = _prune_missing_fields_ui(resp.json(), message, history)

            conv_state.update(improved_query, data)
            response = format_classification_markdown(data)
            conv_state.add_classification_summary(message, data)
            return response

        except Exception as e:
            error_msg = (
                f"⚠️ No pude procesar la pregunta de seguimiento: {e}\n\n"
                "Intenta repetir tu consulta con más detalle o vuelve a clasificar desde cero."
            )
            conv_state.add_turn(message, error_msg)
            return error_msg

    # Validate input is tariff-related
    is_valid, validation_msg = is_tariff_related(message)
    if not is_valid:
        conv_state.add_turn(message, validation_msg)
        return validation_msg

    # Nueva consulta completa: "Neumáticos radiales nuevos... Es caucho natural, es de China, diseño mixto"
    if conv_state.last_query:
        improved_query = f"{conv_state.last_query}. {message}"
    else:
        improved_query = message
    # Llamar a /classify con improved_query
    try:
        payload = {
            "user_query": improved_query, 
            "top_k": 5,
            "conversation_history": _history_to_api_format(history)
        }
        if years_list:
            payload["years"] = years_list
        resp = requests.post(f"{API_URL}/classify", json=payload, timeout=60)
        resp.raise_for_status()
        data = _prune_missing_fields_ui(resp.json(), message, history)

        # Update conversation state (global)
        conv_state.update(message, data)

        # Format response
        response = format_classification_markdown(data)

        # Add helpful tips
        response += "\n---\n"
        response += "💡 **Puedes preguntar:**\n"
        response += "- ¿Por qué se eligió este código?\n"
        response += "- ¿Qué información falta?\n"
        response += "- ¿Hay alternativas?\n"
        response += "- Dame un resumen\n"
        
        # Guardar turno en el historial con el texto completo para mantener contexto
        conv_state.add_turn(message, response)

        return response

    except requests.RequestException as e:
        error_msg = f"❌ **Error al clasificar:** {str(e)}\n\nPor favor, intenta de nuevo o verifica que el servicio API esté funcionando."
        conv_state.add_turn(message, error_msg)
        return error_msg

def _is_vehicle_query(text: str) -> bool:
    # Deprecated: kept for compatibility but no longer used for UI overrides.
    t = (text or "").lower()
    vehicle_terms = [
        "vehículo", "vehiculo", "vehículos", "vehiculos",
        "auto", "autos", "automóvil", "automovil", "carro", "coche",
        "camión", "camion", "camioneta", "pickup",
        "motocicleta", "moto", "bus", "autobús", "autobus", "microbús", "microbus",
    ]
    return any(term in t for term in vehicle_terms)


def _detect_category(text: str) -> Optional[str]:
    """Heurística simple para detectar la categoría del producto de la consulta."""
    t = (text or "").lower()
    # Vehículos
    vehicle_terms = [
        "vehículo", "vehiculo", "vehículos", "vehiculos",
        "auto", "automóvil", "automovil", "coche", "carro",
        "camión", "camion", "camioneta", "pickup",
        "motocicleta", "moto", "bus", "autobús", "autobus", "microbús", "microbus",
        "tranvía", "tranvia", "trolebús", "trolebus", "tren", "locomotora", "vagón", "vagon",
    ]
    if any(w in t for w in vehicle_terms):
        return "vehicle"
    # Metales / acero
    metal_terms = [
        "acero", "steel", "hierro", "aluminio", "cobre", "inox", "inoxidable",
        "lámina", "lamina", "plancha", "chapa", "bobina", "galvanizado", "recubierto",
        "titanio", "níquel", "niquel", "zinc", "estaño", "estano", "plomo", "plata", "oro",
        "latón", "laton", "bronce", "magnesio", "molibdeno", "vanadio",
    ]
    if any(w in t for w in metal_terms):
        return "metal"
    # Textil
    textile_terms = [
        "textil", "tela", "tejido", "prenda", "ropa", "algodón", "algodon", "poliéster", "poliester", "lana", "seda",
        "fibra", "hilo", "trama", "urdimbre", "tinta", "tinte", "teñido", "tenido", "acrílico", "acrilico",
        "poliamida", "nylon", "spandex", "elástico", "elastico", "botón", "boton", "cremallera", "cierre",
    ]
    if any(w in t for w in textile_terms):
        return "textile"
    # Electrónica
    elec_terms = [
        "electrón", "electron", "dispositivo", "aparato", "equipo", "smartphone", "teléfono", "telefono", "laptop", "notebook", "computadora", "pc",
        "monitor", "teclado", "ratón", "raton", "mouse", "pantalla", "oled", "lcd", "batería", "bateria",
        "cargador", "adaptador", "cable", "usb", "hdmi", "wifi", "procesador", "memoria", "ram", "disco", "ssd", "hdd",
        "placa", "circuito", "chip", "microprocesador", "transistor", "diodo", "condensador", "resistencia",
    ]
    if any(w in t for w in elec_terms):
        return "electronics"
    # Alimentos
    food_terms = [
        "alimento", "comida", "carne", "fruta", "verdura", "pescado", "café", "cafe", "azúcar", "azucar", "cereal",
        "plátano", "platano", "banana", "mango", "piña", "pina", "naranja", "manzana", "pera", "uva", "arándano",
        "arandano", "melocotón", "melocoton", "durazno", "ciruela", "kiwi", "sandía", "sandia", "melón", "melon",
        "papaya", "cacao", "chocolate", "trigo", "arroz", "maíz", "maiz", "frijol", "frijoles", "lenteja", "pollo",
        "leche", "queso", "yogur", "huevo", "huevos", "pan", "pasta", "aceite", "mantequilla", "sal", "pimienta",
    ]
    if any(w in t for w in food_terms):
        return "food"
    return None


def _format_classification_simple(result: Dict[str, Any], user_query: str = "", conv_state=None) -> str:
    """Formato breve: muestra código(s) y descripción sin confianza ni evidencia."""
    candidates = result.get("top_candidates") or result.get("candidates") or []
    missing = result.get("missing_fields", [])
    warnings = result.get("warnings", [])

    # Obtener hint de año desde la evidencia disponible
    year_hint = None
    for ev in (result.get("support_evidence") or []):
        year_hint = ev.get("year")
        if year_hint:
            break
    if not year_hint:
        for ev in (result.get("evidence") or result.get("context_docs") or []):
            year_hint = ev.get("year") or (ev.get("_source", {}) or {}).get("year")
            if year_hint:
                break

    # Filtrar mensajes técnicos de errores de LLM (en warnings Y missing_fields)
    technical_keywords = ["llm", "generador", "gemini", "finish_reason", "bloqueó", "blocked"]
    clean_warnings = [w for w in warnings if not any(x in str(w).lower() for x in technical_keywords)]
    clean_missing = [m for m in missing if not any(x in str(m).lower() for x in technical_keywords)]

    # **CRÍTICO**: Construir contexto acumulado para detectar vehículos/metales correctamente
    contextual_query = user_query or ""
    if conv_state and hasattr(conv_state, 'history') and conv_state.history:
        # Tomar las últimas 2-3 preguntas del usuario para dar contexto
        # conv_state.history es una lista de tuplas: [(user, assistant), ...]
        recent_user_queries = []
        for turn in reversed(conv_state.history[-3:]):  # Últimos 3 turnos
            if isinstance(turn, tuple) and len(turn) >= 1:
                recent_user_queries.insert(0, turn[0])  # turn[0] es el mensaje del usuario
        if recent_user_queries:
            contextual_query = " ".join(recent_user_queries + [user_query])
    
    # Prune vehicle-related missing fields if user_query already contains them
    uq = _strip_accents_ui(contextual_query).lower()  # Usar contexto completo sin acentos
    vehicle_terms = [
        "vehículo", "vehiculo", "auto", "automóvil", "automovil", "coche", "carro",
        "camión", "camion", "camioneta", "pickup", "bus", "autobús", "autobus",
        "microbús", "microbus", "moto", "motocicleta"
    ]
    has_vehicle_type = any(t in uq for t in vehicle_terms)
    has_motor_type = any(t in uq for t in ["diesel", "gasolina", "electrico", "electrica", "electric", "hibrido", "hibrida", "hev", "phev", "ev"])
    is_new_or_used = any(t in uq for t in ["nuevo", "nueva", "usado", "usada"]) 

    def _drop_if_matches(predicates):
        nonlocal clean_missing
        filtered = []
        for m in clean_missing:
            m_norm = _strip_accents_ui(str(m)).lower()
            if any(p in m_norm for p in predicates):
                continue
            filtered.append(m)
        clean_missing = filtered

    if has_vehicle_type:
        _drop_if_matches(["tipo de vehículo", "tipo de vehiculo"]) 
    if has_motor_type:
        _drop_if_matches(["tipo de motor", "motor (gasolina", "motor (diésel", "motor (diesel", "eléctrico", "híbrido", "hibrido"]) 
    if is_new_or_used:
        _drop_if_matches(["nuevo", "usado"]) 

    # Deduplicate after pruning
    clean_missing = list(dict.fromkeys(clean_missing))

    # Si no hay candidates pero SÍ hay evidencia, mostrarla
    # NOTA: El backend ya filtró evidencia relevante
    evidence = result.get("evidence") or result.get("context_docs") or []
    
    if not candidates and evidence:
        lines = ["### 📚 Información encontrada", ""]
        lines.append("Se encontró la siguiente información relacionada:")
        lines.append("")
        
        for i, ev in enumerate(evidence[:5], 1):
            score = ev.get("score") or 0
            text = ev.get("text") or ""
            year = ev.get("year")
            bucket = ev.get("bucket")
            
            year_str = f" | 📅 {year}" if year else ""
            lines.append(f"{i}. **(Score: {score:.2f})**{year_str}")
            lines.append(f"   {text[:300]}")
            if bucket:
                lines.append(f"   _Fuente: {bucket}_")
            lines.append("")
        
        if clean_missing:
            lines.append("### 🔍 Información adicional que ayudaría a clasificar")
            for m in clean_missing[:5]:
                lines.append(f"- {m}")
            lines.append("")
        
        lines.append("Por favor, proporciona más detalles para una clasificación precisa.")
        return "\n".join(lines)

    if not candidates:
        lines = ["### 🔍 Necesito más información para clasificar", ""]
        if clean_missing:
            lines += [f"- {m}" for m in clean_missing[:5]]
        lines.append("")
        lines.append("Por favor, proporciona los datos solicitados para una clasificación precisa.")
        return "\n".join(lines)

    # Extraer años de la evidence para mostrar referencias
    evidence = result.get("evidence") or result.get("context_docs") or []
    years_in_evidence = set()
    for ev in evidence:
        year = ev.get("year")
        if year:
            years_in_evidence.add(int(year) if isinstance(year, (int, str)) else year)
    years_sorted = sorted(years_in_evidence) if years_in_evidence else []
    years_str = ", ".join(str(y) for y in years_sorted) if years_sorted else ""

    # Mostrar hasta 3 códigos con año de referencia
    lines = ["## 🎯 Clasificación sugerida", ""]
    incisos = ["a", "b", "c"]
    
    # Check if top candidate is sufficiently specific to skip missing_fields
    top_cand = candidates[0] if candidates else {}
    top_code = top_cand.get("code") or top_cand.get("hs_code") or ""
    top_confidence = float(top_cand.get("confidence") or 0)
    top_code_digits = len(top_code.replace(".", "").replace(" ", ""))
    
    # Only suppress missing_fields if code is HS10 (10 digits) with 90%+ confidence
    # This ensures we keep asking guiding questions until we reach maximum precision
    should_suppress_missing = (top_code_digits >= 10 and top_confidence >= 0.90)
    
    for i, cand in enumerate(candidates[:3]):
        code = cand.get("code") or cand.get("hs_code") or "N/A"
        desc = (cand.get("description") or cand.get("desc") or "").strip()
        confidence = cand.get("confidence") or 0
        inciso = incisos[i] if i < len(incisos) else str(i + 1)
        
        # Mostrar año(s) de referencia basados en evidence
        if years_str:
            year_ref = f" | 📅 Referencia: {years_str}"
        else:
            year_ref = f" | 📅 {year_hint}" if year_hint else ""
        
        # Mostrar confianza también
        conf_str = f" | 🎯 {confidence:.0%}" if confidence else ""
        
        lines.append(f"**{inciso}) {code}**{year_ref}{conf_str}")
        if desc:
            lines.append(f"   {desc}")
        lines.append("")

    # Si faltan datos, sugerirlos de forma breve (PERO no si ya tenemos código muy refinado)
    if clean_missing and not should_suppress_missing:
        lines.append("### 🔍 Información adicional sugerida")
        for m in clean_missing[:5]:
            lines.append(f"- {m}")
        lines.append("")

    # Sugerencias de seguimiento sin detallar
    lines.append("---")
    #lines.append("Puedes preguntar: ¿Qué información falta?, ¿Por qué?, Dame un resumen.")
    return "\n".join(lines)


def _handle_followup_simple(question: str, last_result: Dict[str, Any]) -> str:
    q = (question or "").lower()
    candidates = last_result.get("top_candidates") or last_result.get("candidates") or []
    inclusions = last_result.get("inclusions", [])
    missing = last_result.get("missing_fields", [])
    applied = last_result.get("applied_rgi", [])
    
    # Filtrar mensajes técnicos de errores de LLM
    technical_keywords = ["llm", "generador", "gemini", "finish_reason", "bloqueó", "blocked"]
    clean_missing = [m for m in missing if not any(x in str(m).lower() for x in technical_keywords)]

    if any(k in q for k in ["qué falta", "que falta", "faltante", "información", "detalles", "adicional"]):
        if not clean_missing:
            return "✅ No se identificaron campos faltantes críticos."
        return "### 🔍 Información requerida\n\n" + "\n".join(f"- {m}" for m in clean_missing)

    if any(k in q for k in ["por qué", "porque", "razón", "justifica", "explica"]):
        parts = []
        if applied:
            parts.append(f"Se aplicaron: {', '.join(applied)}.")
        crit = inclusions[0] if inclusions else None
        if crit:
            parts.append(f"Criterio principal: {crit}")
        return "### 🤔 Motivo\n\n" + (" ".join(parts) or "La descripción coincide con la partida propuesta.")

    if any(k in q for k in ["alternativa", "otras opciones", "otro código", "otro codigo"]):
        if not candidates:
            return "No se encontraron alternativas claras."
        lines = ["### 🔄 Alternativas", ""]

    if any(k in q for k in ["resumen", "resume", "simplifica", "sintetiza"]):
        if candidates:
            code = candidates[0].get("code") or candidates[0].get("hs_code")
            return f"### 📝 Resumen\n\nCódigo recomendado: {code}."
        return "No hay resumen disponible."

    return "No entendí. Intenta: ¿Qué información falta?, ¿Por qué?, alternativas, resumen."


def chat_minimal_validation(message: str, history: list, conv_id: str = "", years: Optional[list] = None) -> Tuple[str, str]:
    """
    Modo simple: funciona como el chatbot, pero sin confianza, evidencia ni detalles extensos.
    Responde siempre con códigos y razones breves.
    Ahora retorna tupla (response, conversation_id) para mantener persistencia.
    
    IMPORTANTE: Usa conversation_id para obtener la ConversationState específica de esta conversación,
    evitando contaminación cruzada entre conversaciones simultáneas o secuenciales.
    """
    if not message or not message.strip():
        return "Por favor, describe tu producto para iniciar la clasificación.", conv_id

    msg = message.strip()
    msg_l = msg.lower()
    conv_id = ensure_conv_id(conv_id)
    conv_state = get_conversation_state(conv_id)  # Obtener estado específico de esta conversación

    # Detectar saludos y mensajes de bienvenida
    greetings = ["hola", "hello", "hi", "buenos días", "buenas tardes", "buenas noches", "saludos", "hey"]
    if any(g == msg_l or msg_l.startswith(g + " ") or msg_l.startswith(g + ",") for g in greetings):
        return (
            "👋 ¡Hola! Soy tu asistente de clasificación arancelaria.\n\n"
            "Describe el producto que necesitas clasificar según el Sistema Armonizado (HS).\n\n"
            "**Ejemplos:**\n"
            "- Láminas de acero laminadas en caliente, 2mm de espesor\n"
            "- Neumáticos radiales para automóvil 205/55R16\n"
            "- Smartphones con pantalla OLED, 128GB de almacenamiento"
        ), conv_id

    # Reset conversacional
    for kw in ["reset", "reiniciar", "nueva conversación", "olvida", "borrar"]:
        if kw in msg_l:
            reset_conversation_state(conv_id)
            conv_id = uuid4().hex  # Nuevo conversation_id al resetear
            return "✅ Conversación reiniciada. Describe tu producto.", conv_id

    # Detectar preguntas de seguimiento simples (solo las obvias)
    if conv_state.last_classification:
        # Preguntas explícitas sobre la clasificación anterior (meta-preguntas)
        if any(k in msg_l for k in ["qué falta", "que falta", "faltante", "por qué", "porque", 
                          "alternativa", "resumen", "resume", "explica", "justifica",
                          "10 díg", "10 dig", "diez díg", "diez dig", "código nacional", "codigo nacional",
                          "nandina", "bolivia", "colombia", "ecuador", "perú", "peru"]):
            reply = _handle_followup_simple(msg, conv_state.last_classification)
            conv_state.add_turn(msg, reply)
            return reply, conv_id
        
        # Para todo lo demás: simplemente enviar al backend con historial completo
        # El LLM es inteligente y detectará automáticamente si hubo cambio de tema
        payload = {
            "user_query": msg, 
            "top_k": 5, 
            "conversation_history": conv_state.get_history_for_api(), 
            "conversation_id": conv_id
        }
        if years:
            years_int = [int(y) for y in years if str(y).isdigit()]
            if years_int:
                payload["years"] = years_int
        sent_query = msg
    else:
        # Primera consulta o sin contexto
        payload = {"user_query": msg, "top_k": 5, "conversation_history": conv_state.get_history_for_api(), "conversation_id": conv_id}
        if years:
            years_int = [int(y) for y in years if str(y).isdigit()]
            if years_int:
                payload["years"] = years_int
        sent_query = msg

    # Clasificación normal, formato simple
    try:
        resp = requests.post(f"{API_URL}/classify", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Extraer conversation_id de la respuesta
        conv_id = data.get("conversation_id", conv_id)
        # Guardar la query real enviada para no perder contexto en los siguientes turnos
        conv_state.update(sent_query, data)
        # Usar el texto realmente enviado (incluye contexto) para personalizar missing_fields
        formatted = _format_classification_simple(data, user_query=sent_query, conv_state=conv_state)
        conv_state.add_turn(msg, formatted)
        conv_state.add_classification_summary(msg, data)
        return formatted, conv_id
    except requests.RequestException as e:
        return f"❌ Error al clasificar: {e}", conv_id

def render_evidence_markdown(result: dict) -> str:
    support = result.get("support_evidence") or []
    generic = result.get("evidence") or result.get("context_docs") or []
    lines = []

    if support:
        lines.append("### 📌 Evidencia del código principal\n")
        for ev in support:
            year = ev.get('year')
            year_str = f" | 📅 {year}" if year else ""
            lines.append(f"- ({float(ev.get('score',0)):0.3f}) {ev.get('text','')[:240]}…  \n  `frag:` {ev.get('fragment_id')}{year_str}")

    if generic:
        lines.append("\n### 📚 Evidencia recuperada por la consulta\n")
        for ev in generic:
            text = ev.get("text") or (ev.get("_source", {}) or {}).get("text", "")
            score = ev.get("score") or ev.get("_score", 0)
            frag = ev.get("fragment_id") or (ev.get("_source", {}) or {}).get("fragment_id")
            year = ev.get("year") or (ev.get("_source", {}) or {}).get("year")
            year_str = f" | 📅 {year}" if year else ""
            lines.append(f"- ({float(score):0.3f}) {text[:240]}…  \n  `frag:` {frag}{year_str}")

    if not lines:
        return "🟡 No se recuperó evidencia.\n\nSugerencias:\n- Ingerir documentos del Capítulo/Partida (e.g., 4011)\n- Aumentar top_k\n- Verificar índice con scripts/init_index.py e ingest_docs.py"

    return "\n".join(lines)

# === INTERFAZ GRADIO ===
with gr.Blocks(
    title="Tariff RAG System"
) as demo:
    gr.Markdown(
    """
        # 🌐 Sistema RAG de Clasificación Arancelaria.
    """
    )

    with gr.Tabs():

        # TAB 1: CHATBOT
        with gr.Tab("💬 Chatbot"):
            # gr.Markdown(
            #     """
            #     ### Validación de Descripción (sin códigos)
            #     
            #     Esta pestaña solo te dirá si tu consulta es demasiado genérica y qué información deberías agregar.
            #     No mostrará códigos HS, porcentajes de confianza, alternativas ni evidencia.
            #     """
            # )

            conv_id_state = gr.State(value="")
            years_selector_min = gr.CheckboxGroup(
                choices=["2025", "2026"],
                value=["2025", "2026"],
                label="Filtrar por año",
                info="Selecciona uno o ambos años; vaciar seleccion busca en todos"
            )
            
            chatbot_minimal = gr.ChatInterface(
                fn=chat_minimal_validation,
                chatbot=gr.Chatbot(height=500),
                additional_inputs=[conv_id_state, years_selector_min],
                additional_outputs=[conv_id_state],
                examples=[
                    ["¿Cuál es la partida arancelaria de los vehículos?", "", ["2025", "2026"]],
                    ["Quiero clasificar láminas de acero", "", ["2025", "2026"]],
                    ["Necesito el código HS de un ventilador", "", ["2025", "2026"]],
                ],
                title=None,
                description=None,
            )


        # TAB 1: CHATBOT COMPLETO
        with gr.Tab("✅ Validación chatbot"):

            gr.Markdown(
                """
                ### Conversación Inteligente
                
                Describe tu producto en lenguaje natural y haz preguntas de seguimiento.
                """
            )

            # Chatbot por defecto (compatible con versiones sin parámetro 'type')
            chatbot_component = gr.Chatbot()
            years_selector_full = gr.CheckboxGroup(
                choices=["2025", "2026"],
                value=["2025", "2026"],
                label="Filtrar por año",
                info="Selecciona uno o ambos años; vaciar seleccion busca en todos"
            )
            chatbot = gr.ChatInterface(
                fn=chat_response,
                chatbot=chatbot_component,
                examples=[
                    ["Láminas de acero laminadas en caliente, 2mm de espesor, para construcción", ["2025", "2026"]],
                    ["Smartphone con pantalla OLED de 6.5 pulgadas, 128GB almacenamiento", ["2025", "2026"]],
                    ["Café tostado en grano, origen colombiano, sin descafeinar", ["2025", "2026"]],
                    ["Neumáticos radiales nuevos para automóvil de pasajeros, tamaño 205/55R16", ["2025", "2026"]],
                    ["¿Cuál es la partida arancelaria de los vehículos?", ["2025", "2026"]],
                ],
                title=None,
                description=None,
                additional_inputs=[years_selector_full],
            )


        # TAB 2: FORMULARIO CLÁSICO
        with gr.Tab("📝 Formulario"):
            gr.Markdown("### Interfaz Tradicional")

            with gr.Row():
                with gr.Column(scale=2):
                    desc = gr.Textbox(
                        lines=10,
                        label="",
                        show_label=False,
                        placeholder="Descripción del Producto: detalla tipo, uso, material, medidas, estado"
                    )
                with gr.Column(scale=1):
                    hs = gr.Textbox(
                        value="HS_2022",
                        label="",
                        show_label=False,
                        interactive=False
                    )

            run = gr.Button("🎯 Clasificar", variant="primary", size="lg")

            gr.Markdown("---")
            gr.Markdown("### Resultados")

            with gr.Tabs():
                with gr.Tab("📊 Candidatos"):
                    cands = gr.JSON(label="Top candidatos con confianza")

                with gr.Tab("📄 Evidencia"):
                    evid = gr.JSON(label="Fragmentos recuperados del corpus")

                with gr.Tab("⚖️ RGI Aplicadas"):
                    rgi = gr.JSON(label="Reglas Generales de Interpretación")

                with gr.Tab("🔍 Campos Faltantes"):
                    miss = gr.JSON(label="Información adicional requerida")

                with gr.Tab("⚠️ Advertencias"):
                    warn = gr.JSON(label="Warnings y mensajes del sistema")

            run.click(
                fn=classify,
                inputs=[desc, hs],
                outputs=[cands, evid, rgi, miss, warn]
            )

        # TAB 3: DOCUMENTACIÓN
        with gr.Tab("📚 Ayuda"):
            gr.Markdown(
                """
                ## 📖 Guía de Uso
                
                ### Chatbot
                - Describe tu producto naturalmente
                - Haz preguntas de seguimiento sobre la clasificación
                - Ejemplos: "¿Por qué ese código?", "¿Qué información falta?"
                
                ### Formulario
                - Interfaz estructurada con resultados detallados
                - Ideal para análisis técnico profundo
                
                ### Consejos para Mejores Resultos
                1. **Sé específico**: Incluye material, uso, características técnicas
                2. **Menciona medidas**: Dimensiones, peso, capacidad
                3. **Indica el uso**: Comercial, industrial, doméstico
                4. **Especifica composición**: Porcentajes de materiales
                
                ### Sistema de Confianza
                - 🟢 **>70%**: Alta confianza
                - 🟡 **50-70%**: Confianza media (revisar)
                - 🔴 **<50%**: Baja confianza (información insuficiente)
                
                ---
                
                **Versión**: 1.0 | **HS Edition**: 2022
                """
            )

    # Footer
    gr.Markdown(
        """
        ---
        ⚙️ *Powered by Azure Document Intelligence + Azure OpenAI + OpenSearch + Redis*
        """
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )
