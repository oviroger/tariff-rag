import os
import requests
import gradio as gr
from typing import Tuple, List, Dict, Any

API_URL = os.getenv("RAG_API_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = int(os.getenv("GRADIO_TIMEOUT", "120"))

def format_error(error_type: str, detail: str) -> Dict[str, str]:
    """Formatea errores de manera user-friendly"""
    return {
        "error": error_type,
        "detail": detail,
        "sugerencia": "Intenta con una descripción más detallada o verifica que los servicios estén activos."
    }

def classify(desc: str, hs_edition: str) -> Tuple[Any, Any, Any, Any, Any]:
    """
    Llama al endpoint /classify y maneja errores de forma robusta.
    Retorna 5 valores para los 5 paneles JSON de Gradio.
    """
    # Validación local
    if not desc or not desc.strip():
        err = format_error("input_vacio", "Por favor ingresa una descripción del producto.")
        return [], [], [], [], err
    
    if len(desc.strip()) < 10:
        err = format_error("input_corto", "La descripción debe tener al menos 10 caracteres.")
        return [], [], [], [], err

    # Preparar payload
    payload = {
        "text": desc.strip(),
        "versions": {"hs_edition": hs_edition.strip() or "HS_2022"},
        "top_k": 5,
        "debug": False
    }

    # Llamada a API con manejo de errores
    try:
        r = requests.post(
            f"{API_URL}/classify",
            json=payload,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        r.raise_for_status()
        data = r.json()
        
        # Extraer campos con fallbacks
        cands = data.get("top_candidates", [])
        evid  = data.get("evidence", [])
        rgi   = data.get("applied_rgi", [])
        miss  = data.get("missing_fields", [])
        warn  = data.get("warnings", [])
        
        # Si hay debug_info, agregarlo a warnings
        if data.get("debug_info"):
            warn.append(f"Debug: {data['debug_info']}")
        
        return cands, evid, rgi, miss, warn or ["Sin advertencias"]
        
    except requests.Timeout:
        err = format_error(
            "timeout",
            f"La solicitud tardó más de {TIMEOUT}s. El servidor puede estar procesando muchas peticiones."
        )
        return [], [], [], [], err
        
    except requests.HTTPError as e:
        status = e.response.status_code
        try:
            detail = e.response.json().get("detail", str(e))
        except:
            detail = str(e)
        
        if status == 400:
            err = format_error("validacion", f"Error de validación: {detail}")
        elif status == 500:
            err = format_error("servidor", f"Error interno del servidor: {detail}")
        else:
            err = format_error(f"http_{status}", detail)
        
        return [], [], [], [], err
        
    except requests.ConnectionError:
        err = format_error(
            "conexion",
            f"No se pudo conectar al API ({API_URL}). Verifica que el servicio esté corriendo."
        )
        return [], [], [], [], err
        
    except Exception as ex:
        err = format_error("desconocido", f"Error inesperado: {str(ex)}")
        return [], [], [], [], err

# === INTERFAZ GRADIO ===
with gr.Blocks(
    title="Tariff RAG (Gradio)",
    theme=gr.themes.Soft()
) as demo:
    gr.Markdown(
        """
        # 🧭 Clasificación Arancelaria — RAG
        ### OpenSearch (BM25 + kNN) + Gemini Embeddings
        
        Ingresa una descripción detallada del producto y obtén candidatos de clasificación con evidencia.
        """
    )
    
    with gr.Row():
        with gr.Column(scale=2):
            desc = gr.Textbox(
                lines=10,
                label="📝 Descripción del producto",
                placeholder="Ejemplo: Resina epoxi en escamas de color ámbar, con endurecedor por separado en envase de 5kg, para uso industrial en recubrimientos de pisos y pinturas protectoras...",
                info="Mínimo 10 caracteres, máximo 4000"
            )
        with gr.Column(scale=1):
            hs = gr.Textbox(
                value="HS_2022",
                label="📅 Edición HS",
                info="Ej: HS_2022, HS_2017"
            )
    
    run = gr.Button("🚀 Clasificar", variant="primary", size="lg")
    
    gr.Markdown("---")
    gr.Markdown("### Resultados")
    
    with gr.Tabs():
        with gr.Tab("🏷️ Candidatos"):
            cands = gr.JSON(label="Top candidatos con confianza")
        
        with gr.Tab("🔎 Evidencia"):
            evid = gr.JSON(label="Fragmentos recuperados del corpus")
        
        with gr.Tab("⚖️ RGI Aplicadas"):
            rgi = gr.JSON(label="Reglas Generales de Interpretación")
        
        with gr.Tab("🧩 Campos Faltantes"):
            miss = gr.JSON(label="Información adicional requerida")
        
        with gr.Tab("⚠️ Advertencias"):
            warn = gr.JSON(label="Warnings y mensajes del sistema")
    
    # Footer
    gr.Markdown(
        f"""
        ---
        **API Endpoint**: `{API_URL}`  
        **Timeout**: {TIMEOUT}s  
        **Versión**: 0.1.0
        """
    )
    
    # Event handler
    run.click(
        fn=classify,
        inputs=[desc, hs],
        outputs=[cands, evid, rgi, miss, warn]
    )

if __name__ == "__main__":
    demo.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
        show_api=False,
        share=False
    )