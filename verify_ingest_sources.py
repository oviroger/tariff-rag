#!/usr/bin/env python3
"""Listar fuentes (source/doc_id) ingeridas en índices 2025 y 2026."""
from opensearchpy import OpenSearch

client = OpenSearch(hosts=["http://localhost:9200"], verify_certs=False, timeout=30)
indices = ["tariff_fragments_2025", "tariff_fragments_2026"]

for idx in indices:
    print(f"\n=== {idx} ===")
    body = {
        "size": 0,
        "aggs": {
            "sources": {
                "terms": {
                    "field": "source",
                    "size": 50
                }
            }
        }
    }
    try:
        res = client.search(index=idx, body=body)
        buckets = res.get("aggregations", {}).get("sources", {}).get("buckets", [])
        if buckets:
            for b in buckets:
                print(f"{b['key']} -> {b['doc_count']}")
        else:
            print("No hay agregación en source; mostrando ejemplos...")
            res2 = client.search(index=idx, body={"query": {"match_all": {}}, "size": 10, "_source": ["source", "doc_id", "bucket"]})
            for h in res2.get("hits", {}).get("hits", []):
                print(h.get("_source"))
    except Exception as e:
        print(f"Error en {idx}: {e}")
