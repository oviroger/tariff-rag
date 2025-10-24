from fastapi import FastAPI
from sqlalchemy import create_engine, text
import google.generativeai as genai
import os

from app.os_index import os_client

app = FastAPI(title="Tariff RAG — Infra (Parte 1)")

@app.get("/health")
def health():
    # --- OpenSearch ---
    try:
        cl = os_client()
        st = cl.cluster.health(wait_for_status="yellow", timeout="1s")
        os_ok = st.get("status") in ("yellow", "green")
    except Exception:
        os_ok = False

    # --- MySQL ---
    try:
        host = os.getenv("MYSQL_HOST","mysql")
        port = int(os.getenv("MYSQL_PORT","3306"))
        db   = os.getenv("MYSQL_DB","corpusdb")
        user = os.getenv("MYSQL_USER","appuser")
        pwd  = os.getenv("MYSQL_PASS","apppass")
        eng = create_engine(f"mysql+mysqlconnector://{user}:{pwd}@{host}:{port}/{db}")
        with eng.connect() as con:
            con.execute(text("SELECT 1"))
        mysql_ok = True
    except Exception:
        mysql_ok = False

    # --- Gemini: solo validamos presencia de key ---
    gemini_key = os.getenv("GOOGLE_API_KEY","")
    gemini_ok = bool(gemini_key)

    overall = os_ok and mysql_ok and gemini_ok
    return {
        "status": "ok" if overall else "degraded",
        "opensearch": os_ok,
        "mysql": mysql_ok,
        "gemini_key_present": gemini_ok
    }
