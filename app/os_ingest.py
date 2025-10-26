from typing import List, Dict, Any
from opensearchpy import helpers
from .os_index import get_os_client
from .embedder_gemini import GeminiEmbedder
from .config import get_settings

def bulk_ingest_fragments(fragments: List[Dict[str, Any]], index_name: str | None = None):
    s = get_settings()
    index = index_name or s.opensearch_index
    texts = [f["text"] for f in fragments]
    embed = GeminiEmbedder()
    vectors = embed.embed_texts(texts)
    actions = []
    for f, v in zip(fragments, vectors):
        src = dict(f)
        src["embedding"] = v
        actions.append({"_index": index, "_id": src["fragment_id"], "_source": src})
    client = get_os_client()
    helpers.bulk(client, actions)