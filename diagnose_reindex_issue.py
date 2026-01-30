#!/usr/bin/env python3
"""
🔍 DIAGNÓSTICO: Por qué se detiene la reindexación
"""

from opensearchpy import OpenSearch
import json

OS_HOST = "http://localhost:9200"

os_client = OpenSearch(
    hosts=[OS_HOST],
    verify_certs=False,
    timeout=30
)

print("=" * 80)
print("🔍 DIAGNÓSTICO DE REINDEXACIÓN")
print("=" * 80)

# 1. Verificar conteos
print("\n1️⃣  CONTEOS DE ÍNDICES:")
for idx in ['tariff_fragments_2025', 'tariff_fragments_2025_v2']:
    try:
        count = os_client.cat.count(index=idx, format='json')[0]['count']
        print(f"   {idx}: {count} docs")
    except Exception as e:
        print(f"   {idx}: ERROR - {e}")

# 2. Verificar estructura del índice original
print("\n2️⃣  ESTRUCTURA DE DOCUMENTOS ORIGINALES:")
try:
    result = os_client.search(
        index='tariff_fragments_2025',
        body={
            "query": {"match_all": {}},
            "size": 3,
            "sort": [{"_id": "asc"}]
        }
    )
    
    hits = result['hits']['hits']
    print(f"   Total hits: {result['hits']['total']['value']}")
    print(f"   Docs retornados: {len(hits)}")
    
    if hits:
        doc = hits[0]
        print(f"\n   Ejemplo documento:")
        print(f"   - ID: {doc['_id']}")
        print(f"   - Keys: {list(doc['_source'].keys())}")
        print(f"   - Sort: {doc.get('sort', 'N/A')}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

# 3. Probar búsqueda con paginación
print("\n3️⃣  PRUEBA DE PAGINACIÓN:")
try:
    # Primera página
    result1 = os_client.search(
        index='tariff_fragments_2025',
        body={
            "query": {"match_all": {}},
            "size": 100,
            "sort": [{"_id": "asc"}]
        }
    )
    
    hits1 = result1['hits']['hits']
    print(f"   Página 1: {len(hits1)} docs")
    
    if hits1:
        last_sort = hits1[-1].get('sort')
        print(f"   Último sort: {last_sort}")
        
        # Segunda página
        result2 = os_client.search(
            index='tariff_fragments_2025',
            body={
                "query": {"match_all": {}},
                "size": 100,
                "sort": [{"_id": "asc"}],
                "search_after": last_sort
            }
        )
        
        hits2 = result2['hits']['hits']
        print(f"   Página 2: {len(hits2)} docs")
        
        if not hits2:
            print(f"   ⚠️  No hay más documentos después de página 1")
        elif len(hits1) == len(hits2):
            print(f"   ⚠️  Misma cantidad - posible problema de paginación")
            
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# 4. Verificar qué se escribió en el índice nuevo
print("\n4️⃣  DOCUMENTOS EN ÍNDICE NUEVO:")
try:
    result = os_client.search(
        index='tariff_fragments_2025_v2',
        body={
            "query": {"match_all": {}},
            "size": 2
        }
    )
    
    hits = result['hits']['hits']
    print(f"   Total: {result['hits']['total']['value']}")
    
    if hits:
        doc = hits[0]['_source']
        print(f"\n   Ejemplo documento enriquecido:")
        print(f"   - hs_code: {doc.get('hs_code', 'N/A')}")
        print(f"   - category: {doc.get('category', 'N/A')}")
        print(f"   - description: {doc.get('description', 'N/A')[:50]}...")
        print(f"   - version: {doc.get('version', 'N/A')}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

# 5. Verificar configuración del índice
print("\n5️⃣  CONFIGURACIÓN DE ÍNDICE ORIGINAL:")
try:
    settings = os_client.indices.get_settings(index='tariff_fragments_2025')
    num_shards = settings['tariff_fragments_2025']['settings']['index']['number_of_shards']
    print(f"   Shards: {num_shards}")
except Exception as e:
    print(f"   ⚠️  {e}")

print("\n" + "=" * 80)
