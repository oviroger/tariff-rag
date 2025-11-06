"""
Genera eval_clasificador_hs6.csv consultando /classify con queries de prueba.
Deja true_hs6 vacío para anotación manual posterior.

Uso:
  python evaluation/tools/generate_eval_clasificador.py \
      --base-url http://localhost:8000 \
      --queries "Smartphone OLED 128GB" "Plátanos frescos" "Neumáticos radiales 205/55R16" \
      --output evaluation/templates/eval_clasificador_hs6.csv

O usa un archivo de queries (una por línea):
  python evaluation/tools/generate_eval_clasificador.py \
      --base-url http://localhost:8000 \
      --queries-file evaluation/test_queries.txt \
      --output evaluation/templates/eval_clasificador_hs6.csv
"""
import argparse
import csv
import sys
from typing import List
import requests


def classify_query(base_url: str, query: str, timeout: float = 30.0) -> dict:
    """Llama a /classify y retorna el resultado."""
    url = f"{base_url.rstrip('/')}/classify"
    try:
        resp = requests.post(url, json={"query": query}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error clasificando '{query}': {e}", file=sys.stderr)
        return {}


def extract_top_codes(result: dict, top_n: int = 3) -> List[str]:
    """Extrae los top N códigos HS de la respuesta."""
    candidates = result.get("top_candidates") or result.get("candidates") or []
    codes = []
    for c in candidates[:top_n]:
        code = c.get("code") or c.get("hs_code") or ""
        codes.append(code)
    return codes


def main():
    ap = argparse.ArgumentParser(description="Genera eval_clasificador_hs6.csv desde /classify")
    ap.add_argument("--base-url", default="http://localhost:8000", help="URL base de la API")
    ap.add_argument("--queries", nargs="*", help="Queries directas en línea de comandos")
    ap.add_argument("--queries-file", help="Archivo con queries (una por línea)")
    ap.add_argument("--output", default="evaluation/templates/eval_clasificador_hs6.csv", help="CSV de salida")
    ap.add_argument("--top-n", type=int, default=3, help="Número de candidatos top a registrar")
    ap.add_argument("--timeout", type=float, default=30.0, help="Timeout para /classify")
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

    rows = []
    for i, q in enumerate(queries, start=1):
        print(f"[{i}/{len(queries)}] Clasificando: {q}")
        result = classify_query(args.base_url, q, args.timeout)
        codes = extract_top_codes(result, args.top_n)
        
        # Rellenar con vacíos si hay menos de top_n
        while len(codes) < args.top_n:
            codes.append("")
        
        row = {
            "query_id": i,
            "query": q,
            "true_hs6": "",  # Dejar vacío para anotación manual
            "pred_top1": codes[0] if len(codes) > 0 else "",
            "pred_top2": codes[1] if len(codes) > 1 else "",
            "pred_top3": codes[2] if len(codes) > 2 else "",
            "score_top1": "",  # Opcional: extraer scores si quieres
            "score_top2": "",
            "score_top3": ""
        }
        rows.append(row)

    # Escribir CSV
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["query_id", "query", "true_hs6", "pred_top1", "pred_top2", "pred_top3", 
                      "score_top1", "score_top2", "score_top3"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nGenerado: {args.output} ({len(rows)} queries)")
    print("NOTA: Llena la columna 'true_hs6' con los códigos correctos antes de evaluar.")


if __name__ == "__main__":
    main()
