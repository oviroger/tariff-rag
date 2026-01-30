#!/usr/bin/env python3
"""Listar doc_id ingeridos por índice."""
from opensearchpy import OpenSearch

client = OpenSearch(hosts=["http://localhost:9200"], verify_certs=False, timeout=30)
indices = ["tariff_fragments_2025", "tariff_fragments_2026"]

for idx in indices:
    print(f"\n=== {idx} doc_id ===")
    body = {
        "size": 0,
        "aggs": {
            "docs": {
                "terms": {
                    "field": "doc_id",
                    "size": 50
                }
            }
        }
    }
    try:
        res = client.search(index=idx, body=body)
        buckets = res.get("aggregations", {}).get("docs", {}).get("buckets", [])
        if buckets:
            for b in buckets:
                print(f"{b['key']} -> {b['doc_count']}")
        else:
            print("No hay doc_id agregable")
    except Exception as e:
        print(f"Error en {idx}: {e}")
