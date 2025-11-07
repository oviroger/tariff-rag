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

def ensure_index(index_name: str | None = None, dim: int | None = None, space: str | None = None):
    """Crea el índice si no existe, con campo knn_vector y 'text' para BM25.
    index_name: permite sobreescribir el índice por defecto de settings.
    """
    s = get_settings()
    client = get_os_client()
    index = index_name or s.opensearch_index
    if client.indices.exists(index):
        return
    dim_val = int(dim or getattr(s, "opensearch_emb_dim", 768))
    space_val = str(space or getattr(s, "opensearch_knn_space", "cosinesimil"))
    body = {
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "fragment_id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "bucket": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
                "chapter": {"type": "keyword"},
                "heading": {"type": "keyword"},
                "subheading": {"type": "keyword"},
                "unit": {"type": "keyword"},
                "text": {"type": "text"},
                "edition": {"type": "keyword"},
                "validity_from": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                "validity_to": {"type": "date", "format": "strict_date_optional_time||epoch_millis"},
                "partida": {"type": "keyword"},
                "hs6": {"type": "keyword"},
                "codigo_producto": {"type": "keyword"},
                "metadata": {"type": "object", "enabled": True},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dim_val,
                    "method": {"name": "hnsw", "space_type": space_val, "engine": "nmslib"},
                },
            }
        },
    }
    client.indices.create(index=index, body=body)