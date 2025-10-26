import google.generativeai as genai
from app.config import SET

genai.configure(api_key=SET.google_api_key)
gen_model = genai.GenerativeModel(SET.gemini_gen_model)

def generate_structured(query: str, docs: list[dict], versions: dict) -> dict:
    """
    Usa Gemini con forzado de JSON, pasando contexto (evidencias).
    """
    evid = []
    for d in docs:
        evid.append({
            "fragment_id": d.metadata.get("fragment_id",""),
            "source": d.metadata.get("source",""),
            "unit": d.metadata.get("unit",""),
            "edition": d.metadata.get("edition",""),
            "text": d.page_content
        })
    prompt = {
      "query": query,
      "versions": versions,
      "evidence": evid
    }
    resp = gen_model.generate_content(
        contents=[{"role":"user","parts":[prompt]}],
        generation_config={
            "response_mime_type":"application/json",
            "response_schema": {"type":"object", **{"properties":{**{}}, "allOf":[ ]}}, # placeholder
        }
    )
    # Nota: LangChain también permite PydanticOutputParser; aquí forzamos JSON puro
    return resp.parsed if hasattr(resp, "parsed") and resp.parsed else resp.text  # dict o JSON string
