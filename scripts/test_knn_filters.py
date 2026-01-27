#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba: búsqueda kNN con filtro de capítulo
"""
import json
import os
from opensearchpy import OpenSearch
from app.embedder_gemini import GeminiEmbedder

# Detectar si estamos en Docker o local
os_host = "opensearch" if os.path.exists("/.dockerenv") else "localhost"

# Conectar a OpenSearch
client = OpenSearch(
    hosts=[{'host': os_host, 'port': 9200}],
    http_auth=('admin', 'admin'),
    use_ssl=False,
    verify_certs=False
)

embedder = GeminiEmbedder()

def knn_with_filter(index, query_text, chapter_filter=None, k=10):
    """Búsqueda kNN con filtro de capítulo opcional."""
    qvec = embedder.embed_texts([query_text])[0]
    
    # Construir query base
    knn_query = {
        "knn": {
            "embedding": {
                "vector": qvec,
                "k": k
            }
        }
    }
    
    # Si hay filtro de capítulo, añadirlo
    if chapter_filter:
        body = {
            "size": k,
            "query": {
                "bool": {
                    "must": [knn_query],
                    "filter": [{"term": {"chapter": chapter_filter}}]
                }
            },
            "_source": ["text", "chapter", "heading", "subheading", "year"]
        }
    else:
        body = {
            "size": k,
            "query": knn_query,
            "_source": ["text", "chapter", "heading", "subheading", "year"]
        }
    
    resp = client.search(index=index, body=body)
    hits = resp.get("hits", {}).get("hits", [])
    return hits

print("\n" + "="*80)
print("KNN SEARCH CON Y SIN FILTRO DE CAPITULO")
print("="*80)

query = "neumaticos radiales para automovil 205/55R16"

# Búsqueda sin filtro (situación actual)
print(f"\n1. SIN FILTRO (current behavior):")
print(f"Query: {query}")
for idx in ["tariff_fragments_2025", "tariff_fragments_2026"]:
    print(f"\n  INDEX: {idx}")
    hits = knn_with_filter(idx, query, chapter_filter=None, k=5)
    print(f"  Found: {len(hits)} hits")
    for i, h in enumerate(hits, 1):
        src = h["_source"]
        text = src.get("text", "")[:60]
        ch = src.get("chapter", "N/A")
        heading = src.get("heading", "N/A")
        print(f"    {i}. Chapter={ch} | Heading={heading} | Text: {text}...")

# Búsqueda con filtro de capítulo 40 (caucho)
print(f"\n\n2. CON FILTRO CAPITULO 40 (solution):")
print(f"Query: {query}")
for idx in ["tariff_fragments_2025", "tariff_fragments_2026"]:
    print(f"\n  INDEX: {idx}")
    hits = knn_with_filter(idx, query, chapter_filter=40, k=5)
    print(f"  Found: {len(hits)} hits")
    for i, h in enumerate(hits, 1):
        src = h["_source"]
        text = src.get("text", "")[:60]
        ch = src.get("chapter", "N/A")
        heading = src.get("heading", "N/A")
        print(f"    {i}. Chapter={ch} | Heading={heading} | Text: {text}...")

# Búsqueda BM25 de referencia
print(f"\n\n3. BM25 LEXICAL (reference):")
print(f"Query: {query}")
for idx in ["tariff_fragments_2025", "tariff_fragments_2026"]:
    print(f"\n  INDEX: {idx}")
    body = {
        "size": 5,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["text"],
                "type": "best_fields"
            }
        },
        "_source": ["text", "chapter", "heading", "subheading", "year"]
    }
    resp = client.search(index=idx, body=body)
    hits = resp.get("hits", {}).get("hits", [])
    print(f"  Found: {len(hits)} hits")
    for i, h in enumerate(hits, 1):
        src = h["_source"]
        text = src.get("text", "")[:60]
        ch = src.get("chapter", "N/A")
        heading = src.get("heading", "N/A")
        print(f"    {i}. Chapter={ch} | Heading={heading} | Text: {text}...")
