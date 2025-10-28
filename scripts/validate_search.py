# scripts/validate_search.py
import os
import sys
import json
from typing import Dict, List, Tuple

from opensearchpy import OpenSearch
import google.genai as genai

# ========= Config =========
OS_HOST  = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
OS_INDEX = os.getenv("OPENSEARCH_INDEX", "tariff_fragments")
TEXT_FLD = os.getenv("OS_TEXT_FIELD", "text")           # campo BM25
VEC_FLD  = os.getenv("OS_VECTOR_FIELD", "embedding")    # campo knn_vector
TOPK     = int(os.getenv("VALIDATE_TOPK", "5"))
RRF_K    = int(os.getenv("RRF_K", "60"))                # parámetro típico de RRF

GEMINI_MODEL = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ========= Clientes =========
os_client = OpenSearch(hosts=[OS_HOST], verify_certs=False)

if not GOOGLE_API_KEY:
    print("Falta GOOGLE_API_KEY en el entorno.", file=sys.stderr)
    sys.exit(1)

genai_client = genai.Client(api_key=GOOGLE_API_KEY)

# ========= Utilidades =========
def get_query_vector(q: str) -> List[float]:
    """Embedding de la consulta con Gemini (text-embedding-004)."""
    resp = genai_client.models.embed_content(model=GEMINI_MODEL, content=q)
    return resp.embedding.values

def search_bm25(q: str, k: int) -> List[Dict]:
    """Match query sobre el campo de texto (BM25 por defecto)."""
    body = {"size": k, "query": {"match": {TEXT_FLD: q}}}
    res = os_client.search(index=OS_INDEX, body=body)
    hits = []
    for h in res["hits"]["hits"]:
        hits.append({
            "id": h["_id"],
            "score": float(h["_score"]),
            "source": h["_source"].get("source", ""),
            "preview": h["_source"].get(TEXT_FLD, "")[:160].replace("\n", " ")
        })
    return hits

def search_knn(vec: List[float], k: int) -> List[Dict]:
    """Consulta k-NN sobre el campo de vectores."""
    body = {
        "size": k,
        "query": {
            "knn": {
                VEC_FLD: {
                    "vector": vec,
                    "k": k
                }
            }
        }
    }
    res = os_client.search(index=OS_INDEX, body=body)
    hits = []
    for h in res["hits"]["hits"]:
        hits.append({
            "id": h["_id"],
            "score": float(h["_score"]),
            "source": h["_source"].get("source", ""),
            "preview": h["_source"].get(TEXT_FLD, "")[:160].replace("\n", " ")
        })
    return hits

def rrf_fusion(bm25: List[Dict], knn: List[Dict], k_rrf: int = RRF_K) -> List[Dict]:
    """Reciprocal Rank Fusion de dos listas (BM25 y kNN)."""
    # Índices por id
    ranks_bm = {doc["id"]: i+1 for i, doc in enumerate(bm25)}
    ranks_kn = {doc["id"]: i+1 for i, doc in enumerate(knn)}
    ids = set(ranks_bm) | set(ranks_kn)

    fused = []
    for _id in ids:
        r_bm = ranks_bm.get(_id)
        r_kn = ranks_kn.get(_id)
        score = 0.0
        if r_bm is not None:
            score += 1.0 / (k_rrf + r_bm)
        if r_kn is not None:
            score += 1.0 / (k_rrf + r_kn)
        # Toma metadatos desde cualquiera de las listas (prefiere BM25 si existe)
        meta = next((d for d in bm25 if d["id"] == _id), None) or next((d for d in knn if d["id"] == _id), {})
        fused.append({
            "id": _id,
            "rrf_score": score,
            "source": meta.get("source", ""),
            "bm25_rank": r_bm,
            "knn_rank": r_kn,
            "preview": meta.get("preview", "")
        })
    # Mayor score primero
    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    return fused

def pretty_print(title: str, rows: List[Dict], cols: List[Tuple[str, str]], limit: int):
    print(f"\n== {title} ==")
    for i, r in enumerate(rows[:limit], start=1):
        parts = [f"{label}: {r.get(key)}" for key, label in cols]
        print(f"{i:>2}. " + " | ".join(parts))

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/validate_search.py \"<consulta de ejemplo>\"")
        sys.exit(1)

    query = sys.argv[1]
    print(f"Consulta: {query}")
    qvec = get_query_vector(query)

    bm = search_bm25(query, TOPK)
    kn = search_knn(qvec, TOPK)
    fused = rrf_fusion(bm, kn, RRF_K)

    pretty_print(
        "Top-5 BM25",
        bm,
        cols=[("id","fragment_id"), ("score","score"), ("source","source")],
        limit=TOPK
    )
    pretty_print(
        "Top-5 k-NN",
        kn,
        cols=[("id","fragment_id"), ("score","score"), ("source","source")],
        limit=TOPK
    )
    pretty_print(
        "Fusión (RRF) — Top-5",
        fused,
        cols=[("id","fragment_id"), ("rrf_score","rrf"), ("bm25_rank","bm25_r"), ("knn_rank","knn_r"), ("source","source")],
        limit=TOPK
    )

if __name__ == "__main__":
    main()
