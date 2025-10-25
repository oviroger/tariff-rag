from typing import Any, Dict, List, Optional

# OCR best-effort
try:
    from .ocr_formrec import extract_text_best_effort as _extract_text_best_effort
except Exception:
    def _extract_text_best_effort(text: Optional[str], file_url: Optional[str]) -> str:
        return text or ""

# Truncado/guardrails
try:
    from .guardrails import truncate as _truncate
except Exception:
    def _truncate(s: str, max_chars: int = 5000) -> str:
        return (s or "")[:max_chars]

# Reglas rápidas (opcional)
try:
    from .rules import rule_based_label as _rule_based_label
except Exception:
    def _rule_based_label(_: str) -> Optional[str]:
        return None

# Embeddings (opcional)
try:
    from .embedder_gemini import GeminiEmbedder as _GeminiEmbedder
except Exception:
    _GeminiEmbedder = None

# Retriever (opcional)
try:
    from .lc_retriever import retrieve as _retrieve
except Exception:
    def _retrieve(_: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        return []

# Generación LLM (opcional)
try:
    from .generator_gemini import generate_label as _generate_label
except Exception:
    def _generate_label(query: str, context_chunks: List[str]) -> Dict[str, Any]:
        return {"label": "UNKNOWN", "score": 0.0, "reasons": ["Generador no disponible."]}

# Estado global simple para el embedder
_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is None and _GeminiEmbedder is not None:
        _embedder = _GeminiEmbedder()
    return _embedder

def classify(text: Optional[str], file_url: Optional[str], top_k: int = 5, debug: bool = False) -> Dict[str, Any]:
    # 1) Obtener texto de consulta
    query = _extract_text_best_effort(text, file_url)
    query = _truncate(query, max_chars=5000)
    if not query.strip():
        return {"label": "EMPTY", "score": 0.0, "reasons": ["No se recibió texto."], "citations": []}

    # 2) Reglas rápidas
    rule_label = _rule_based_label(query)

    # 3) Recuperación (si hay embedder y retriever)
    hits: List[Dict[str, Any]] = []
    context_chunks: List[str] = []
    emb = _get_embedder()
    if emb is not None:
        try:
            qv = emb.embed_query(query)
            hits = _retrieve(qv, top_k=top_k) or []
            context_chunks = [h.get("content", "") for h in hits]
        except Exception as e:
            hits = []
            context_chunks = []

    # 4) LLM para etiqueta (o fallback)
    llm_out = _generate_label(query, context_chunks)
    label = llm_out.get("label") or rule_label or "UNKNOWN"
    try:
        score = float(llm_out.get("score") or 0.0)
    except Exception:
        score = 0.0
    reasons = list(llm_out.get("reasons") or [])
    citations = [
        {"id": h.get("id") or "", "score": float(h.get("score") or 0.0), "snippet": (h.get("content") or "")[:240]}
        for h in hits
    ]

    result: Dict[str, Any] = {"label": label, "score": score, "reasons": reasons, "citations": citations}
    if debug:
        result["debug"] = {"retrieved_top3": hits[:3], "context_count": len(context_chunks)}
    return result
