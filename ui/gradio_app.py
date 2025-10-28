"""
Gradio UI for Tariff RAG system.
Provides both static form and conversational chatbot interfaces.
"""

import gradio as gr
import requests
from typing import Any, Tuple, Dict, Optional
import json

API_BASE_URL = "http://api:8000"

class ConversationState:
    """Manages conversation history and context."""
    def __init__(self):
        self.last_classification: Optional[Dict[str, Any]] = None
        self.last_query: str = ""
    
    def update(self, query: str, result: Dict[str, Any]):
        self.last_query = query
        self.last_classification = result
    
    def has_context(self) -> bool:
        return self.last_classification is not None

# Global conversation state
conv_state = ConversationState()

def classify(desc: str, hs_edition: str) -> Tuple[Any, Any, Any, Any, Any]:
    """
    Call the RAG classification API.
    Returns: (candidates, evidence, rgi, missing, warnings)
    """
    try:
        payload = {"text": desc, "query": desc, "top_k": 5}
        resp = requests.post(f"{API_BASE_URL}/classify", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        # Handle both field name variations
        candidates = data.get("top_candidates", data.get("candidates", []))
        evidence = data.get("evidence", [])
        rgi = data.get("applied_rgi", [])
        missing = data.get("missing_fields", [])
        warnings = data.get("warnings", [])
        
        return candidates, evidence, rgi, missing, warnings
    
    except requests.RequestException as e:
        error_msg = f"❌ Error: {str(e)}"
        return [], [], [], [], [error_msg]

def format_classification_markdown(result: Dict[str, Any]) -> str:
    """Format classification results as readable markdown."""
    md = "## 🎯 Clasificación Arancelaria\n\n"
    
    # Candidates - Handle both 'top_candidates' and 'candidates' field names
    candidates = result.get("top_candidates", result.get("candidates", []))
    if candidates and len(candidates) > 0:
        md += "### 📊 Códigos HS Candidatos\n\n"
        for i, cand in enumerate(candidates, 1):
            # Handle both 'code' and 'hs_code' field names
            hs_code = cand.get('code', cand.get('hs_code', 'N/A'))
            confidence = cand.get('confidence', 0)
            description = cand.get('description', 'Sin descripción')
            level = cand.get('level', '')
            
            # Format confidence with color indicator
            if confidence > 0.7:
                conf_emoji = "🟢"
            elif confidence > 0.5:
                conf_emoji = "🟡"
            else:
                conf_emoji = "🔴"
            
            md += f"{conf_emoji} **{i}. {hs_code}** (Confianza: {confidence:.1%})\n"
            md += f"   - {description}\n"
            if level:
                md += f"   - 📊 Nivel: *{level}*\n"
            md += "\n"
        
        # Inclusions/Exclusions (at root level)
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
    
    # Applied RGI
    applied_rgi = result.get("applied_rgi", [])
    if applied_rgi:
        md += "### ⚖️ Reglas Aplicadas\n\n"
        md += ", ".join(applied_rgi) + "\n\n"
    
    # Missing fields
    missing_fields = result.get("missing_fields", [])
    if missing_fields:
        md += "### 🔍 Información Adicional Requerida\n\n"
        for field in missing_fields[:5]:
            md += f"- {field}\n"
        md += "\n"
    
    # Evidence count
    evidence = result.get("evidence", [])
    if evidence:
        md += f"### 📚 Evidencia: {len(evidence)} fragmentos recuperados\n\n"
        # Show snippet from top evidence
        if len(evidence) > 0:
            top_ev = evidence[0]
            md += f"**Fragmento más relevante** (score: {top_ev.get('score', 0):.3f}):\n"
            md += f"> {top_ev.get('text', '')[:200]}...\n\n"
    
    # Warnings
    warnings = result.get("warnings", [])
    if warnings:
        md += "### ⚠️ Advertencias\n\n"
        for warning in warnings:
            md += f"- {warning}\n"
        md += "\n"
    
    return md

def is_tariff_related(text: str) -> tuple[bool, str]:
    """
    Validate if query is related to tariff classification.
    Returns: (is_valid, reason_or_suggestion)
    """
    text_lower = text.lower().strip()
    
    # Too short
    if len(text.split()) < 2:
        return False, "Por favor, proporciona más detalles sobre el producto o tu consulta."
    
    # Tariff-related keywords (positive indicators)
    tariff_keywords = [
        "clasificar", "clasificación", "código hs", "partida arancelaria",
        "sistema armonizado", "tariff", "hs code", "harmonized system",
        "arancel", "aduana", "importación", "exportación",
        "rgi", "reglas generales", "general rules"
    ]
    
    has_tariff_keyword = any(kw in text_lower for kw in tariff_keywords)
    
    # Product indicators (positive for classification)
    product_indicators = [
        # Materials
        "acero", "steel", "aluminio", "plástico", "madera", "textil",
        "algodón", "cuero", "vidrio", "cerámica", "papel",
        # Product types
        "lámina", "plancha", "tubo", "cable", "máquina", "dispositivo",
        "aparato", "equipo", "vehículo", "neumático", "batería",
        # Product attributes
        "laminado", "fundido", "tejido", "procesado", "manufacturado",
        "galvanizado", "recubierto", "pintado"
    ]
    
    has_product_indicator = any(ind in text_lower for ind in product_indicators)
    
    # Explicit non-tariff topics (negative indicators)
    off_topic_patterns = [
        # People
        "quién es", "quien es", "quiénes son", "biografía de",
        # General questions
        "qué es python", "qué es javascript", "cómo programar",
        # Sports/entertainment
        "quién ganó", "partido de", "resultado del",
        # News/current events
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
                "- *Smartphone con pantalla OLED, 128GB*\n"
                "- *¿Qué es la RGI 3?*"
            )
    
    # Check for famous names (people, not products)
    famous_names = [
        "messi", "ronaldo", "maradona", "pelé", "neymar",
        "einstein", "newton", "tesla", "curie",
        "biden", "trump", "macron"
    ]
    
    # Only reject if it's ONLY a name (not "camiseta de Messi")
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
    
    # If has tariff keywords or product indicators, accept
    if has_tariff_keyword or has_product_indicator:
        return True, ""
    
    # Ambiguous case: allow but might get poor results
    return True, ""

def is_followup_question(message: str) -> bool:
    """Detect if message is a follow-up question."""
    followup_keywords = [
        # Original keywords
        "por qué", "porque", "por que",
        "qué falta", "que falta", "información adicional",
        "alternativas", "otras opciones",
        "explica", "detalla", "más información",
        "diferencia", "comparar",
        
        # Translation and formatting requests
        "traduc", "español", "inglés", "english",
        "resume", "resumen", "simplifica",
        
        # Clarification requests
        "cuál", "cual", "cómo", "como",
        "significa", "quiere decir",
        "ejemplo", "caso",
        
        # References to previous result
        "este código", "ese código", "estos códigos",
        "el resultado", "la respuesta", "lo anterior"
    ]
    message_lower = message.lower()
    
    # Short questions are likely follow-ups
    if len(message.split()) <= 8 and any(kw in message_lower for kw in followup_keywords):
        return True
    
    return any(kw in message_lower for kw in followup_keywords)

def handle_followup_question(question: str, last_result: Dict[str, Any]) -> str:
    """Handle follow-up questions about the last classification."""
    question_lower = question.lower()
    
    # Get candidates with both possible field names
    candidates = last_result.get("top_candidates", last_result.get("candidates", []))
    
    # Translation request
    if "traduc" in question_lower or "español" in question_lower:
        response = "### 🌐 Resumen en Español\n\n"
        if candidates:
            response += "**📊 Códigos HS:**\n\n"
            for i, cand in enumerate(candidates[:3], 1):
                hs_code = cand.get('code', cand.get('hs_code', 'N/A'))
                confidence = cand.get('confidence', 0)
                
                conf_emoji = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.5 else "🔴"
                response += f"{conf_emoji} **{i}. {hs_code}** ({confidence:.0%} confianza)\n\n"
        
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
            for i, cand in enumerate(candidates[1:4], 2):
                hs_code = cand.get('code', cand.get('hs_code', 'N/A'))
                confidence = cand.get('confidence', 0)
                description = cand.get('description', '')
                response += f"**{i}. {hs_code}** ({confidence:.1%})\n"
                response += f"   {description}\n\n"
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

def chat_response(message: str, history: list) -> str:
    """
    Main chatbot response function.
    Handles both classification requests and follow-up questions.
    """
    message = message.strip()
    
    # Check if it's a follow-up question about previous classification
    if conv_state.has_context() and is_followup_question(message):
        return handle_followup_question(message, conv_state.last_classification)
    
    # Validate input is tariff-related
    is_valid, validation_msg = is_tariff_related(message)
    if not is_valid:
        return validation_msg
    
    # Otherwise, treat it as a new classification request
    try:
        payload = {"text": message, "query": message, "top_k": 5}
        resp = requests.post(f"{API_BASE_URL}/classify", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        # Update conversation state
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
        
        return response
    
    except requests.RequestException as e:
        return f"❌ **Error al clasificar:** {str(e)}\n\nPor favor, intenta de nuevo o verifica que el servicio API esté funcionando."

# === INTERFAZ GRADIO ===
with gr.Blocks(
    title="Tariff RAG System",
    theme=gr.themes.Soft()
) as demo:
    gr.Markdown(
        """
        # 🌐 Sistema RAG de Clasificación Arancelaria
        
        Clasifica productos según el Sistema Armonizado (HS) usando IA y recuperación de información.
        """
    )
    
    with gr.Tabs():
        # TAB 1: CHATBOT
        with gr.Tab("💬 Chatbot"):
            gr.Markdown(
                """
                ### Conversación Inteligente
                
                Describe tu producto en lenguaje natural y haz preguntas de seguimiento.
                """
            )
            
            chatbot = gr.ChatInterface(
                fn=chat_response,
                examples=[
                    "Láminas de acero laminadas en caliente, 2mm de espesor, para construcción",
                    "Smartphone con pantalla OLED de 6.5 pulgadas, 128GB almacenamiento",
                    "Café tostado en grano, origen colombiano, sin descafeinar",
                    "Neumáticos radiales nuevos para automóvil de pasajeros, tamaño 205/55R16",
                    "¿Cuáles son las reglas generales de interpretación?",
                ],
                title=None,
                description=None,
                retry_btn="🔄 Reintentar",
                undo_btn="↩️ Deshacer",
                clear_btn="🗑️ Limpiar",
            )
        
        # TAB 2: FORMULARIO CLÁSICO
        with gr.Tab("📝 Formulario"):
            gr.Markdown("### Interfaz Tradicional")
            
            with gr.Row():
                with gr.Column(scale=2):
                    desc = gr.Textbox(
                        lines=10,
                        label="Descripción del Producto",
                        placeholder="Describe el producto con el mayor detalle posible..."
                    )
                with gr.Column(scale=1):
                    hs = gr.Textbox(
                        value="HS_2022",
                        label="Edición HS",
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
                
                ### Consejos para Mejores Resultados
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
        ⚙️ *Powered by Azure Document Intelligence + Google Gemini + OpenSearch*
        """
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )