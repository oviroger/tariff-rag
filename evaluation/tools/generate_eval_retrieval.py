"""
Genera eval_retrieval.csv ejecutando búsquedas híbridas en OpenSearch.
Deja relevance vacío para anotación manual posterior (0 o 1 por doc).

Uso:
  python evaluation/tools/generate_eval_retrieval.py \
      --os-host https://localhost:9200 \
      --index tariff_docs \
      --queries "Smartphone OLED" "Plátanos" \
      --top-k 5 \
      --output evaluation/templates/eval_retrieval.csv

O desde archivo:
  python evaluation/tools/generate_eval_retrieval.py \
      --os-host https://localhost:9200 \
      --index tariff_docs \
      --queries-file evaluation/test_queries.txt \
      --top-k 5 \
      --output evaluation/templates/eval_retrieval.csv
"""
import argparse
import csv
import sys
from typing import List
from opensearchpy import OpenSearch


def hybrid_search(client: OpenSearch, index: str, query: str, k: int = 5) -> List[dict]:
    """Ejecuta búsqueda híbrida y retorna hits."""
    try:
        # BM25
        bm25_body = {
            "query": {"match": {"text": {"query": query}}},
            "size": k
        }
        bm25_resp = client.search(index=index, body=bm25_body)
        bm25_hits = bm25_resp.get("hits", {}).get("hits", [])
        
        # KNN (si hay vector_emb)
        knn_hits = []
        # Aquí podrías agregar lógica KNN si tienes embeddings, por ahora omito
        
        # Simplificado: devolver top BM25 hits
        results = []
        for h in bm25_hits:
            results.append({
                "doc_id": h.get("_id"),
                "score": h.get("_score"),
                "text": h.get("_source", {}).get("text", "")[:200]  # Snippet
            })
        return results
    except Exception as e:
        print(f"Error en búsqueda para '{query}': {e}", file=sys.stderr)
        return []


def main():
    ap = argparse.ArgumentParser(description="Genera eval_retrieval.csv desde búsquedas en OpenSearch")
    ap.add_argument("--os-host", default="https://localhost:9200", help="OpenSearch host")
    ap.add_argument("--index", default="tariff_docs", help="Índice de OpenSearch")
    ap.add_argument("--queries", nargs="*", help="Queries en línea de comandos")
    ap.add_argument("--queries-file", help="Archivo con queries (una por línea)")
    ap.add_argument("--top-k", type=int, default=5, help="Documentos a recuperar por query")
    ap.add_argument("--output", default="evaluation/templates/eval_retrieval.csv", help="CSV de salida")
    args = ap.parse_args()

    queries = []
    if args.queries:
        queries.extend(args.queries)
    if args.queries_file:
        with open(args.queries_file, "r", encoding="utf-8") as f:
            queries.extend(line.strip() for line in f if line.strip())
    
    if not queries:
        print("No se proporcionaron queries. Usa --queries o --queries-file.", file=sys.stderr)
        sys.exit(1)

    # Conectar OpenSearch
    client = OpenSearch(
        hosts=[args.os_host],
        http_auth=None,
        use_ssl=False,
        verify_certs=False,
        timeout=10
    )

    rows = []
    for i, q in enumerate(queries, start=1):
        print(f"[{i}/{len(queries)}] Buscando: {q}")
        hits = hybrid_search(client, args.index, q, args.top_k)
        
        for rank, h in enumerate(hits, start=1):
            row = {
                "query_id": i,
                "query": q,
                "doc_id": h["doc_id"],
                "rank": rank,
                "score": round(h["score"], 4),
                "relevance": "",  # Dejar vacío para anotación manual (0 o 1)
                "snippet": h["text"]
            }
            rows.append(row)

    # Escribir CSV
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["query_id", "query", "doc_id", "rank", "score", "relevance", "snippet"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nGenerado: {args.output} ({len(rows)} docs recuperados)")
    print("NOTA: Llena la columna 'relevance' con 0 (no relevante) o 1 (relevante) antes de evaluar.")


if __name__ == "__main__":
    main()
