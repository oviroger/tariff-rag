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
    
    # Determinar qué índices usar
    indices_to_search = []
    if index is None:
        settings = get_settings()
        # Si se especifican años, mapear años a índices específicos
        if years:
            year_to_index = {
                2025: "tariff_fragments_2025",
                2026: "tariff_fragments_2026"
            }
            indices_to_search = [year_to_index[y] for y in years if y in year_to_index]
            if not indices_to_search:
                indices_to_search = [settings.opensearch_index]
            logger.info(f"Year filter: {years} -> indices: {indices_to_search}")
        else:
            # Usar opensearch_indices si está configurado (múltiples), sino opensearch_index
            if hasattr(settings, 'opensearch_indices') and settings.opensearch_indices:
                indices_to_search = settings.opensearch_indices.split(",")
            else:
                indices_to_search = [settings.opensearch_index]
            logger.info(f"No year filter -> indices: {indices_to_search}")
    else:
        # Índice especificado: puede ser uno solo o múltiples separados por coma
        indices_to_search = [idx.strip() for idx in index.split(",")]
        logger.info(f"Specified index -> indices: {indices_to_search}")
    
    # Actualizar métrica de retrieval_k
    RETRIEVAL_K.labels(strategy="hybrid").set(top_k)
    
    # Generar embedding para la query
    query_vector = embedder.embed_texts([query_text])[0]
    
    # Construir query kNN
    query_obj = {
        "knn": {
            "embedding": {
                "vector": query_vector,
                "k": top_k
            }
        }
    }
    
    # Body de búsqueda
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
        # Usar OpenSearch native cross-index search
        index_str = ",".join(indices_to_search)
        
        # Si hay múltiples índices, solicitar más hits para balanceo entre índices
        k_adjusted = top_k
        if len(indices_to_search) > 1:
            # Solicitar al menos 2x para garantizar representación de cada índice
            k_adjusted = top_k * len(indices_to_search)
            logger.info(f"Multi-index search: requested {k_adjusted} hits to balance {len(indices_to_search)} indices")
        
        body["size"] = k_adjusted
        response = client.search(index=index_str, body=body)
        all_hits = response.get("hits", {}).get("hits", [])
        logger.info(f"OpenSearch returned {len(all_hits)} total hits from {index_str}")
        
        # LOG: Mostrar distribución de hits por índice
        hits_distribution = {}
        for hit in all_hits:
            idx = hit.get("_index")
            year = hit.get("_source", {}).get("year")
            hits_distribution[idx] = hits_distribution.get(idx, 0) + 1
        logger.info(f"Hits distribution: {hits_distribution}")
        
        # Si hay múltiples índices, balancear para asegurar representación de cada uno
        if len(indices_to_search) > 1 and len(all_hits) > 0:
            # Agrupar por índice
            hits_by_index = {}
            for hit in all_hits:
                idx = hit.get("_index")
                if idx not in hits_by_index:
                    hits_by_index[idx] = []
                hits_by_index[idx].append(hit)
            
            # Redistribuir para que cada índice tenga representación proporcional
            final_hits = []
            slots_per_index = {}
            for idx in indices_to_search:
                slots_per_index[idx] = max(1, top_k // len(indices_to_search))
            
            # Llenar slots usando round-robin por score
            available = {idx: list(hits_by_index.get(idx, [])) for idx in indices_to_search}
            while len(final_hits) < top_k:
                filled_any = False
                for idx in indices_to_search:
                    if len(final_hits) >= top_k:
                        break
                    if available[idx] and slots_per_index[idx] > 0:
                        final_hits.append(available[idx].pop(0))
                        slots_per_index[idx] -= 1
                        filled_any = True
                if not filled_any:
                    break
            
            logger.info(f"Balanced result: {len(final_hits)} hits with representation from {len([i for i in indices_to_search if i in hits_by_index])} indices")
            return final_hits
        
        logger.info(f"Retrieved {len(all_hits[:top_k])} hits from {len(indices_to_search)} indices")
        return all_hits[:top_k]
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
    """
    BM25 léxico sobre uno o múltiples índices.
    Si index contiene múltiples índices (separados por coma), usa OpenSearch native cross-index search.
    """
    body = _bm25_body(query_text, k=k)
    
    try:
        # OpenSearch soporta búsquedas cross-index directamente con coma
        resp = os_client.search(index=index, body=body)
        hits = resp.get("hits", {}).get("hits", [])
        logger.info(f"BM25: Retrieved {len(hits)} hits from indices '{index}'")
        return hits
    except Exception as e:
        logger.warning(f"BM25 search failed for index '{index}': {e}")
        return []


def ensure_index_exists(os_client, index_name: str):
    """Crea el índice si no existe."""
    emb_dim = int(os.getenv('OPENSEARCH_EMB_DIM', '1536'))
    knn_space = os.getenv('OPENSEARCH_KNN_SPACE', 'cosinesimil')
    if os_client.indices.exists(index=index_name):
        try:
            mapping = os_client.indices.get(index_name)
            props = mapping.get(index_name, {}).get("mappings", {}).get("properties", {})
            current_dim = props.get("embedding", {}).get("dimension")
            if current_dim and int(current_dim) != emb_dim:
                raise RuntimeError(
                    f"Index {index_name} has embedding dim {current_dim}, expected {emb_dim}. "
                    "Recreate the index with the correct dimension and reingest documents."
                )
        except Exception:
            raise
        return
    
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
    ESTRATEGIA MEJORADA:
    1) Ejecuta BM25 y kNN en paralelo
    2) Combina resultados usando Reciprocal Rank Fusion (RRF)
    3) Si ambos fallan, intenta con un solo método
    
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

    # Determinar el índice para búsqueda usando la misma lógica que retrieve_fragments
    if index is None:
        settings = get_settings()
        if years:
            year_to_index = {
                2025: "tariff_fragments_2025",
                2026: "tariff_fragments_2026"
            }
            selected_indices = [year_to_index[y] for y in years if y in year_to_index]
            search_index = ",".join(selected_indices) if selected_indices else settings.opensearch_index
        else:
            search_index = settings.opensearch_indices if hasattr(settings, 'opensearch_indices') and settings.opensearch_indices else settings.opensearch_index
    else:
        search_index = index
    
    logger.info(f"Hybrid search on index: {search_index} with years: {years}")
    
    # Ejecutar BM25 y kNN en paralelo (pedir más resultados para fusión)
    k_retrieval = k * 3  # Pedir 3x para tener pool más grande
    
    bm25_hits = []
    knn_hits = []
    
    # 1. BM25
    try:
        bm25_hits = bm25_search(os_client, search_index, query_text, k=k_retrieval)
        logger.info(f"BM25 returned {len(bm25_hits)} hits")
    except Exception as e:
        logger.warning(f"BM25 failed: {e}")
    
    # 2. kNN
    try:
        knn_hits = retrieve_fragments(query_text, top_k=k_retrieval, index=search_index, years=years)
        logger.info(f"kNN returned {len(knn_hits)} hits")
    except Exception as e:
        logger.warning(f"kNN failed: {e}")
    
    # 3. Si ambos fallan, devolver lista vacía
    if not bm25_hits and not knn_hits:
        logger.warning("Both BM25 and kNN failed to return results")
        return []
    
    # 4. Reciprocal Rank Fusion (RRF)
    # Score = 1 / (rank + k) donde k=60 es estándar
    RRF_K = 60
    scores = {}
    
    for rank, hit in enumerate(bm25_hits, 1):
        doc_id = hit.get("_id")
        scores[doc_id] = scores.get(doc_id, {"hit": hit, "score": 0})
        scores[doc_id]["score"] += 1.0 / (rank + RRF_K)
        scores[doc_id]["bm25_rank"] = rank
    
    for rank, hit in enumerate(knn_hits, 1):
        doc_id = hit.get("_id")
        if doc_id not in scores:
            scores[doc_id] = {"hit": hit, "score": 0}
        scores[doc_id]["score"] += 1.0 / (rank + RRF_K)
        scores[doc_id]["knn_rank"] = rank
    
    # Ordenar por score RRF y tomar top-k
    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
    final_hits = [item["hit"] for item in ranked[:k]]
    
    logger.info(f"RRF fusion: Combined {len(bm25_hits)} BM25 + {len(knn_hits)} kNN -> {len(final_hits)} final results")
    
    return final_hits
