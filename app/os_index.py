# app/os_index.py
from opensearchpy import OpenSearch
from .config import get_settings

def get_os_client() -> OpenSearch:
    """Crea el cliente de OpenSearch usando variables de entorno/config."""
    s = get_settings()
    # Si usas usuario/contraseña, añade:
    # auth = (s.opensearch_username, s.opensearch_password) if getattr(s, "opensearch_username", None) else None
    client = OpenSearch(
        hosts=[s.opensearch_host],
        # http_auth=auth,  # descomenta si tienes autenticación
        verify_certs=False
    )
    return client

def ensure_index(dim: int | None = None, space: str | None = None):
    """Crea el índice si no existe, con campo knn_vector y 'text' para BM25."""
    s = get_settings()
    client = get_os_client()
    index = s.opensearch_index
    if client.indices.exists(index):
        return
    dim = dim or getattr(s, "opensearch_emb_dim", 768)
    space = space or getattr(s, "opensearch_knn_space", "cosinesimil")
    body = {
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "fragment_id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
                "chapter": {"type": "keyword"},
                "heading": {"type": "keyword"},
                "subheading": {"type": "keyword"},
                "unit": {"type": "keyword"},
                "text": {"type": "text"},
                "edition": {"type": "keyword"},
                "validity_from": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                "validity_to": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                "metadata": {"type": "object", "enabled": True},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": int(dim),
                    "method": {"name": "hnsw", "space_type": space, "engine": "nmslib"},
                },
            }
        },
    }
    client.indices.create(index=index, body=body)