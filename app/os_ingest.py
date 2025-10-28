"""
app/os_ingest.py
Bulk indexing de fragmentos en OpenSearch.
"""

import json
from typing import List, Dict, Any
from opensearchpy import helpers
from .os_index import get_os_client
from .embedder_gemini import GeminiEmbedder
from .config import get_settings

def bulk_ingest_fragments(fragments: List[Dict[str, Any]], index_name: str | None = None):
    s = get_settings()
    index = index_name or s.opensearch_index
    client = get_os_client()
    embed = GeminiEmbedder()
    texts = [f.get("text", "") for f in fragments]
    vectors = embed.embed_texts(texts)

    actions = []
    for src, vec in zip(fragments, vectors):
        # Forzar serialización limpia: convertir a dict primitivo
        clean_src = json.loads(json.dumps(src, default=str))
        clean_src["embedding"] = vec
        actions.append({
            "_index": index,
            "_id": clean_src["fragment_id"],
            "_source": clean_src
        })
    
    helpers.bulk(client, actions)
    print(f"✅ Ingestados {len(actions)} fragmentos en {index}")