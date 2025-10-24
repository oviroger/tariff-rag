import os, json, requests, pandas as pd
import streamlit as st

API_URL = os.getenv("RAG_API_URL", "http://api:8000")
st.set_page_config(page_title="Tariff RAG", layout="wide")

def badge(text: str, ok: bool | None):
    color = "#16a34a" if ok is True else ("#dc2626" if ok is False else "#6b7280")
    return f"""<span style="
        display:inline-block;padding:0.15rem 0.5rem;border-radius:0.5rem;
        background:{color};color:white;font-weight:600;font-size:0.8rem;">
        {text}
    </span>"""

def fetch_health(api_url: str) -> dict:
    try:
        r = requests.get(f"{api_url}/health", timeout=3)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"status": "down", "error": str(e)}

def health_cards(health: dict):
    col1, col2, col3, col4 = st.columns(4)
    status = health.get("status")
    os_ok = health.get("opensearch")
    my_ok = health.get("mysql")
    ge_ok = health.get("gemini_key_present")
    with col1:
        st.markdown("**Estado general**")
        st.markdown(badge(status.upper() if status else "N/A", status == "ok"), unsafe_allow_html=True)
    with col2:
        st.markdown("**OpenSearch**")
        st.markdown(badge("UP" if os_ok else "DOWN", bool(os_ok)), unsafe_allow_html=True)
    with col3:
        st.markdown("**MySQL**")
        st.markdown(badge("UP" if my_ok else "DOWN", bool(my_ok)), unsafe_allow_html=True)
    with col4:
        st.markdown("**Gemini key**")
        st.markdown(badge("PRESENT" if ge_ok else "MISSING", bool(ge_ok)), unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ Config")
    api = st.text_input("API URL", API_URL)
    refresh_secs = st.slider("Refresco (seg)", 5, 60, 10)
    st.caption("Este panel consulta /health de la API.")

st.header("🩺 Estado del sistema")
st.markdown(
    f'<script>setTimeout(function() {{ window.location.reload(); }}, {refresh_secs*1000});</script>',
    unsafe_allow_html=True
)
health = fetch_health(api)
health_cards(health)
with st.expander("Ver JSON de /health"):
    st.json(health)

st.divider()
st.header("🧭 Clasificación (se habilitará en la Parte 2)")
st.info("En la siguiente parte agregaremos el retriever híbrido, Gemini y endpoints de clasificación.")
