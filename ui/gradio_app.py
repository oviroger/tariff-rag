import os, json, requests, gradio as gr

# Lee el backend desde env (útil si corres con docker-compose)
API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")

def classify(desc: str, hs_edition: str):
    if not desc.strip():
        return "Por favor ingresa una descripción.", "", "", "", ""
    payload = {"description": desc, "versions": {"hs_edition": hs_edition}}
    r = requests.post(f"{API_URL}/classify", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    cands = data.get("top_candidates", [])
    evid  = data.get("evidence", [])
    rgi   = data.get("applied_rgi", [])
    miss  = data.get("missing_fields", [])
    warn  = data.get("warnings", [])
    # Retorna cada bloque para mostrarlos como JSONs
    return cands, evid, rgi, miss, warn

with gr.Blocks(title="Tariff RAG (Gradio)") as demo:
    gr.Markdown("## 🧭 Clasificación arancelaria — RAG (OpenSearch + Gemini)")

    with gr.Row():
        desc = gr.Textbox(lines=8, label="Descripción del producto", placeholder="Resina epoxi en escamas, endurecedor aparte, uso industrial...")
        hs   = gr.Textbox(value="HS_2022", label="HS Edition")

    run = gr.Button("Clasificar")

    cands = gr.JSON(label="🏷️ Candidatos")
    evid  = gr.JSON(label="🔎 Evidencia")
    rgi   = gr.JSON(label="⚖️ RGI aplicadas")
    miss  = gr.JSON(label="🧩 Campos faltantes")
    warn  = gr.JSON(label="⚠️ Advertencias")

    run.click(fn=classify, inputs=[desc, hs], outputs=[cands, evid, rgi, miss, warn])

if __name__ == "__main__":
    # Para exponer en red o contenedor: server_name="0.0.0.0"
    demo.launch(server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
                server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")))