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
