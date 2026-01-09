"""
app/os_retrieval.py
Recuperación semántica desde OpenSearch usando embeddings.
"""
from typing import List, Dict, Optional
import os
import logging
from app.os_index import get_os_client
from app.config import get_settings
from app.metrics import RETRIEVAL_K
from app.embedder_gemini import GeminiEmbedder

logger = logging.getLogger(__name__)

def retrieve_fragments(query_text: str, top_k: int = 5, index: Optional[str] = None, years: Optional[List[int]] = None) -> list:
    """
    Recupera fragmentos relevantes usando búsqueda semántica (kNN + embeddings).
    
    Args:
        query_text: Texto de la consulta
        top_k: Número de resultados a retornar
        index: Índice específico (si es None, usa opensearch_indices para multi-año)
        years: Años a filtrar (ej: [2025, 2026]). Si es None, busca en todos los disponibles
    
    Returns:
        Lista de hits con metadata de año incluida
    """
    client = get_os_client()
    embedder = GeminiEmbedder()
    
    # Si no se especifica índice, usar la lista de índices configurada
    if index is None:
        settings = get_settings()
        # Si se especifican años, mapear años a índices específicos
        if years:
            year_to_index = {
                2025: "tariff_fragments",
                2026: "tariff_fragments_2026"
            }
            selected_indices = [year_to_index[y] for y in years if y in year_to_index]
            index = ",".join(selected_indices) if selected_indices else settings.opensearch_index
            logger.info(f"[DEBUG] Years provided: {years} → Selected indices: {index}")
        else:
            # Usar opensearch_indices si está configurado, sino opensearch_index
            index = settings.opensearch_indices if hasattr(settings, 'opensearch_indices') and settings.opensearch_indices else settings.opensearch_index
            logger.info(f"[DEBUG] No years provided → Using all indices: {index}")
    else:
        logger.info(f"[DEBUG] Index already specified: {index}")
    
    # Actualizar métrica de retrieval_k
    RETRIEVAL_K.labels(strategy="hybrid").set(top_k)
    
    # Generar embedding para la query
    query_vector = embedder.embed_texts([query_text])[0]
    
    # Construir query kNN (el filtro de años se maneja vía selección de índices)
    query_obj = {
        "knn": {
            "embedding": {
                "vector": query_vector,
                "k": top_k
            }
        }
    }
    
    # Búsqueda kNN nativa de OpenSearch
    body = {
        "size": top_k,
        "query": query_obj,
        "_source": [
            "fragment_id",
            "text",
            "doc_id",
            "bucket",
            "unit",
            "validity_from",
            "filename",
            "chapter",
            "heading",
            "subheading",
            "year"  # Incluir año en resultados
        ]
    }
    
    try:
        logger.info(f"[DEBUG] Executing OpenSearch query on index: '{index}' with years: {years}")
        response = client.search(index=index, body=body)
        logger.info(f"[DEBUG] OpenSearch response: {len(response.get('hits', {}).get('hits', []))} hits found")
        hits = response.get("hits", {}).get("hits", [])
        logger.info(f"[DEBUG] Results from years {years}: {[h.get('_source', {}).get('fragment_id') + ':' + str(h.get('_source', {}).get('year')) for h in hits[:3]]}")
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

def retrieve_support_for_code(os_client, index_name: str, code: str, k: int = 5, query_text: str | None = None) -> List[Dict]:
    """
    Recupera evidencia textual que soporte el código HS elegido.

    Estrategia:
      1) BM25 léxico contra variantes del código/heading.
      2) Si no hay resultados y tenemos query_text, fallback semántico (kNN) con la consulta del usuario.
    """
    if not code:
        return []
    heading = code.split(".")[0]  # '4011' de '4011.10'
    # Solo buscar variantes del código y su heading para evitar arrastrar evidencia de otros dominios (ej: neumáticos)
    terms = _hs_variants(code) + [heading]
    should = [
        {"match_phrase": {"text": {"query": code, "boost": 8.0}}},
        {"match_phrase": {"text": {"query": heading, "boost": 6.0}}},
    ] + [{"match_phrase": {"text": {"query": t, "boost": 4.0}}} for t in terms]

    body = {
        "size": k,
        "query": {"bool": {"should": should, "minimum_should_match": 1}},
        "_source": ["fragment_id", "text", "bucket", "unit", "doc_id", "year"],
    }
    try:
        resp = os_client.search(index=index_name, body=body)
        hits = resp.get("hits", {}).get("hits", [])
    except Exception:
        hits = []

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

    # Fallback semántico si no hay evidencia y tenemos la consulta del usuario
    if not results and query_text:
        try:
            sem_k = min(k, 2)  # limitar a top-2 para mantener conciso
            sem_hits = knn_semantic_search(os_client, index_name, query_text, k=sem_k)
            for h in sem_hits:
                src = h.get("_source", {})
                results.append({
                    "fragment_id": src.get("fragment_id"),
                    "score": h.get("_score", 0.0),
                    "text": src.get("text", ""),
                    "bucket": src.get("bucket"),
                    "unit": src.get("unit"),
                    "doc_id": src.get("doc_id"),
                    "reason": "semantic_support",
                })
        except Exception:
            pass

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
        "_source": ["fragment_id","text","bucket","unit","doc_id","chapter","heading","subheading","year"]
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
        "_source": ["fragment_id","text","bucket","unit","doc_id","chapter","heading","subheading","year"],
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

def hybrid_search_with_fallback(os_client, index: Optional[str], query_text: str, k: int = 5, years: Optional[List[int]] = None) -> List[Dict]:
    """
    1) Intenta KNN semántico con embeddings.
    2) Si vacío o falla, cae a BM25 con boosts de dominio.
    
    Args:
        os_client: Cliente OpenSearch
        index: Nombre del índice o índices (puede ser "index1,index2" para múltiples). Si es None, se usa la lógica de años.
        query_text: Texto a buscar
        k: Número de resultados
        years: Lista de años para filtrar (ej: [2025, 2026])
    """
    # Asegurar que el índice existe (solo si no es None)
    if index and "," not in index:  # Si es un solo índice, verificar que existe
        ensure_index_exists(os_client, index)

    try:
        hits = retrieve_fragments(query_text, top_k=k, index=index, years=years)
        if hits:
            return hits
    except Exception as e:
        logger.warning(f"KNN search failed: {e}. Falling back to BM25.")
        # Fallback a BM25
        pass

    # Fallback a BM25 léxico
    # Determinar el índice para BM25 usando la misma lógica que retrieve_fragments
    if index is None:
        settings = get_settings()
        if years:
            year_to_index = {
                2025: "tariff_fragments",
                2026: "tariff_fragments_2026"
            }
            selected_indices = [year_to_index[y] for y in years if y in year_to_index]
            bm25_index = ",".join(selected_indices) if selected_indices else settings.opensearch_index
        else:
            bm25_index = settings.opensearch_indices if hasattr(settings, 'opensearch_indices') and settings.opensearch_indices else settings.opensearch_index
        logger.info(f"[BM25 FALLBACK] Using index: {bm25_index} for years: {years}")
    else:
        bm25_index = index
        
    return bm25_search(os_client, bm25_index, query_text, k)
