"""
app/os_ingest.py
Bulk indexing de fragmentos en OpenSearch.
"""

import os
import json
from typing import List, Dict, Any, Iterable
from opensearchpy import helpers
from .os_index import get_os_client, ensure_index
from .embedder_gemini import GeminiEmbedder
from .config import get_settings

def _flatten_metadata(src: Dict[str, Any]) -> Dict[str, Any]:
    """Eleva claves de metadata al nivel raíz para coincidir con el mapeo.
    Conserva el objeto 'metadata' original.
    """
    clean_src = json.loads(json.dumps(src, default=str))
    meta = clean_src.get("metadata") or {}
    for key in (
        "source",
        "bucket",
        "doc_id",
        "chapter",
        "heading",
        "subheading",
        "unit",
        "edition",
        "validity_from",
        "validity_to",
        "partida",
        "hs6",
        "codigo_producto",
    ):
        if key not in clean_src and key in meta:
            clean_src[key] = meta[key]
    return clean_src


def _batched(iterable: Iterable[Any], n: int) -> Iterable[List[Any]]:
    batch: List[Any] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch


def bulk_ingest_fragments(
    fragments: List[Dict[str, Any]],
    index_name: str | None = None,
    *,
    embed: bool | None = None,
    batch_size: int | None = None,
):
    """Ingesta en lote de fragmentos en OpenSearch.

    - embed: si False, omite embeddings (solo BM25). Control por env NO_EMBED.
    - batch_size: tamaño de lote para embeddings/ingesta. Env OPENSEARCH_EMBED_BATCH (por defecto 64).
    """
    s = get_settings()
    index = index_name or s.opensearch_index
    client = get_os_client()

    # Flags desde parámetros o entorno
    embed_flag = embed if embed is not None else not str(os.getenv("NO_EMBED", "0")) in ("1", "true", "True")
    bsize = int(batch_size if batch_size is not None else os.getenv("OPENSEARCH_EMBED_BATCH", 64))

    # Asegurar índice con mapeo esperado
    ensure_index(index)

    total = 0
    embedder = GeminiEmbedder() if embed_flag else None

    for frag_batch in _batched(fragments, max(1, int(bsize))):
        texts = [f.get("text", "") for f in frag_batch]
        vectors = None
        if embedder is not None:
            vectors = embedder.embed_texts(texts)

        actions = []
        for i, src in enumerate(frag_batch):
            clean_src = _flatten_metadata(src)
            if vectors is not None:
                clean_src["embedding"] = vectors[i]
            actions.append({
                "_index": index,
                "_id": clean_src["fragment_id"],
                "_source": clean_src,
            })

        helpers.bulk(client, actions)
        total += len(actions)

    print(f"✅ Ingestados {total} fragmentos en {index} (embed={'on' if embed_flag else 'off'})")