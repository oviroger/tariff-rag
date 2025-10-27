"""
app/os_retrieval.py
Recuperación semántica desde OpenSearch usando embeddings.
"""
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
