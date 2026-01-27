#!/usr/bin/env python3
"""Investigar qué pasó con los fragmentos de 2026 en OpenSearch."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.os_index import get_os_client
from app.embedder_gemini import GeminiEmbedder

client = get_os_client()
embedder = GeminiEmbedder()

print("=== INVESTIGACIÓN DE ÍNDICES ===\n")

# Ver estadísticas básicas
for idx_name in ["tariff_fragments_2025", "tariff_fragments_2026"]:
    try:
        count = client.count(index=idx_name)["count"]
        print(f"{idx_name}: {count} documentos")
    except Exception as e:
        print(f"{idx_name}: ERROR - {e}")

# Buscar "electrodoméstico" en ambos índices
print("\n=== BÚSQUEDA: 'electrodoméstico' ===")
for idx_name in ["tariff_fragments_2025", "tariff_fragments_2026"]:
    try:
        result = client.search(index=idx_name, body={
            "query": {"match": {"text": "electrodoméstico"}},
            "size": 1
        })
        hits = result["hits"]["total"]["value"]
        print(f"{idx_name}: {hits} documentos encontrados")
    except Exception as e:
        print(f"{idx_name}: ERROR - {e}")

# Buscar documentos con capítulo 84
print("\n=== BÚSQUEDA: Capítulo 84 ===")
for idx_name in ["tariff_fragments_2025", "tariff_fragments_2026"]:
    try:
        result = client.search(index=idx_name, body={
            "query": {"term": {"chapter": "84"}},
            "size": 3
        })
        hits = result["hits"]["hits"]
        count = result["hits"]["total"]["value"]
        print(f"{idx_name}: {count} documentos")
        if hits:
            for h in hits[:2]:
                src = h["_source"]
                text_preview = src.get("text", "")[:100]
                print(f"  - ID: {h['_id']}, Text: {text_preview}...")
    except Exception as e:
        print(f"{idx_name}: ERROR - {e}")

# Prueba de embedding
print("\n=== PRUEBA DE EMBEDDINGS ===")
try:
    query = "electrodomésticos de cocina"
    vector = embedder.embed_texts([query])[0]
    print(f"Query: '{query}'")
    print(f"Vector generado: {len(vector)} dimensiones")
    
    # Buscar documentos por KNN en ambos índices
    for idx_name in ["tariff_fragments_2025", "tariff_fragments_2026"]:
        try:
            result = client.search(index=idx_name, body={
                "size": 3,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": vector,
                            "k": 3
                        }
                    }
                },
                "_source": ["text", "chapter", "year"]
            })
            hits = result["hits"]["hits"]
            print(f"\n{idx_name} - Resultados KNN (top 3):")
            for h in hits:
                score = h["_score"]
                text = h["_source"]["text"][:80]
                chapter = h["_source"].get("chapter")
                year = h["_source"].get("year")
                print(f"  Score={score:.3f}, Cap={chapter}, Year={year}, Text={text}...")
        except Exception as e:
            print(f"  ERROR: {e}")
            
except Exception as e:
    print(f"ERROR en embedding: {e}")
