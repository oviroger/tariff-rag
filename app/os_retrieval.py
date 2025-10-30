"""
app/os_retrieval.py
Recuperación semántica desde OpenSearch usando embeddings.
"""
from typing import List, Dict
from app.os_index import get_os_client
from app.config import get_settings
from app.metrics import RETRIEVAL_K
from app.embedder_gemini import GeminiEmbedder

def retrieve_fragments(query_text: str, top_k: int = 5, index: str = None) -> list:
    """
    Recupera fragmentos relevantes usando búsqueda semántica (kNN + embeddings).
    """
    if index is None:
        settings = get_settings()
        index = settings.opensearch_index
    
    client = get_os_client()
    embedder = GeminiEmbedder()
    
    # Actualizar métrica de retrieval_k
    RETRIEVAL_K.labels(strategy="hybrid").set(top_k)
    
    # Generar embedding para la query
    query_vector = embedder.embed_texts([query_text])[0]

    # Búsqueda kNN nativa de OpenSearch
    body = {
        "size": top_k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": top_k
                }
            }
        },
        "_source": ["fragment_id", "text", "doc_id", "bucket", "unit", "validity_from", "filename"]
    }
    
    try:
        response = client.search(index=index, body=body)
        hits = response.get("hits", {}).get("hits", [])
        # Return raw OpenSearch hits to match chain_rag expectations:
        # each hit has: "_id", "_score", and "_source" with "text", etc.
        return hits
    except Exception as e:
        raise RuntimeError(f"Error en recuperación: {e}")

def _hs_variants(code: str) -> List[str]:
    """
    Genera variantes comunes del código HS para buscar en texto crudo.
    4011.10 -> ["4011.10","401110","4011 10","4011-10","4011 .10","4011. 10","4011 . 10"]
    """
    c = (code or "").strip()
    if not c:
        return []
    no_dot = c.replace(".", "")
    with_space = c.replace(".", " ")
    with_dash = c.replace(".", "-")
    with_space_after = c.replace(".", ". ")
    with_space_before = c.replace(".", " .")
    spaced_both = c.replace(".", " . ")
    return list({c, no_dot, with_space, with_dash, with_space_after, with_space_before, spaced_both})

def retrieve_support_for_code(os_client, index_name: str, code: str, k: int = 5) -> List[Dict]:
    """
    Recupera evidencia textual que soporte el código HS elegido (BM25 léxico).
    """
    if not code:
        return []
    heading = code.split(".")[0]  # '4011' de '4011.10'
    terms = _hs_variants(code) + [heading, "neumático", "neumáticos", "tire", "tires", "tyre", "tyres", "pneumatic"]
    # Construimos 'should' con boosts más altos al match exacto del código y el heading
    should = [
        {"match_phrase": {"text": {"query": code, "boost": 8.0}}},
        {"match_phrase": {"text": {"query": heading, "boost": 6.0}}},
    ] + [{"match": {"text": {"query": t, "boost": 3.0}}} for t in terms]

    body = {
        "size": k,
        "query": {"bool": {"should": should, "minimum_should_match": 1}},
        "_source": ["fragment_id", "text", "bucket", "unit", "doc_id"],
    }
    resp = os_client.search(index=index_name, body=body)
    hits = resp.get("hits", {}).get("hits", [])
    results = []
    for h in hits:
        src = h.get("_source", {})
        results.append({
            "fragment_id": src.get("fragment_id"),
            "score": h.get("_score", 0.0),
            "text": src.get("text", ""),
            "bucket": src.get("bucket"),
            "unit": src.get("unit"),
            "doc_id": src.get("doc_id"),
            "reason": "support_for_code",
        })
    return results

def knn_semantic_search(os_client, index: str, query_text: str, k: int = 5) -> List[Dict]:
    """
    Busca semánticamente con embeddings en el campo 'embedding' (knn_vector).
    Requiere que el índice tenga el mapping con knn_vector (ver os_index.ensure_index).
    """
    if not query_text:
        return []
    embedder = GeminiEmbedder()
    qvec = embedder.embed_texts([query_text])[0]
    body = {
        "size": k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": qvec,
                    "k": k
                }
            }
        },
        "_source": ["fragment_id","text","bucket","unit","doc_id","chapter","heading","subheading"]
    }
    resp = os_client.search(index=index, body=body)
    return resp.get("hits", {}).get("hits", [])


def _bm25_body(query_text: str, k: int = 5) -> Dict:
    """
    BM25 léxico con leves boosts a términos del dominio y variantes HS si aplica.
    """
    terms = ["neumático", "neumáticos", "llanta", "llantas", "caucho", "pneumatic", "tyre", "tyres", "tire", "tires"]
    should = [
        {"match": {"text": {"query": query_text, "boost": 3.0}}},
    ] + [{"match": {"text": {"query": t, "boost": 2.0}}} for t in terms]

    # Si el usuario ya menciona un código tipo 4011.10, añade variantes y boost
    import re
    m = re.search(r"\b(\d{4})(?:\.(\d{2}))?(?:\.(\d{2}))?\b", query_text)
    if m:
        code = ".".join([p for p in m.groups() if p]) if m.groups() else m.group(1)
        for v in _hs_variants(code):
            should.append({"match_phrase": {"text": {"query": v, "boost": 6.0}}})
        should.append({"match_phrase": {"text": {"query": code.split('.')[0], "boost": 4.0}}})

    return {
        "size": k,
        "query": {"bool": {"should": should, "minimum_should_match": 1}},
        "_source": ["fragment_id","text","bucket","unit","doc_id","chapter","heading","subheading"],
    }


def bm25_search(os_client, index: str, query_text: str, k: int = 5) -> List[Dict]:
    body = _bm25_body(query_text, k=k)
    resp = os_client.search(index=index, body=body)
    return resp.get("hits", {}).get("hits", [])


def ensure_index_exists(os_client, index_name: str):
    """Crea el índice si no existe."""
    if os_client.indices.exists(index=index_name):
        return
    
    emb_dim = int(os.getenv('OPENSEARCH_EMB_DIM', '768'))
    knn_space = os.getenv('OPENSEARCH_KNN_SPACE', 'cosinesimil')
    
    mapping = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100
            }
        },
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": emb_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": knn_space,
                        "engine": "nmslib"
                    }
                },
                "metadata": {"type": "object", "enabled": False}
            }
        }
    }
    
    os_client.indices.create(index=index_name, body=mapping)
    logger.info(f"Created index: {index_name}")

def hybrid_search_with_fallback(os_client, index: str, query_text: str, k: int = 5) -> List[Dict]:
    """
    1) Intenta KNN semántico con embeddings.
    2) Si vacío o falla, cae a BM25 con boosts de dominio.
    """
    # Asegurar que el índice existe
    ensure_index_exists(os_client, index)

    try:
        hits = knn_semantic_search(os_client, index, query_text, k)
        if hits:
            return hits
    except Exception:
        # log outside if you prefer; silence to fall back
        pass

    return bm25_search(os_client, index, query_text, k)
