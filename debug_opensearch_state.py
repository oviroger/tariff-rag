#!/usr/bin/env python3
"""
DEBUG: Revisar qué hay en OpenSearch para microondas
"""

import requests
from opensearchpy import OpenSearch

os_client = OpenSearch(
    hosts=["http://localhost:9200"],
    verify_certs=False,
    timeout=10
)

# 1. Ver estado de índices
print("=" * 80)
print("📊 ESTADO DE ÍNDICES")
print("=" * 80)

indices = os_client.cat.indices(format='json')
for idx in indices:
    if 'tariff' in idx['index'].lower():
        status = idx['status']
        docs = idx['docs.count']
        size = idx['store.size']
        print(f"\n✅ {idx['index']}")
        print(f"   Status: {status} | Docs: {docs} | Size: {size}")

# 2. Ver estructura de un documento
print("\n\n" + "=" * 80)
print("📄 ESTRUCTURA DE DOCUMENTOS")
print("=" * 80)

for idx_name in ['tariff_fragments_2026', 'tariff_fragments_2025', 'tariff_fragments']:
    try:
        # Get one document
        result = os_client.search(index=idx_name, body={
            "query": {"match_all": {}},
            "size": 1,
            "_source": True
        })
        
        if result['hits']['hits']:
            doc = result['hits']['hits'][0]['_source']
            print(f"\n✅ {idx_name}:")
            print(f"   Keys: {list(doc.keys())}")
            
            # Show one example
            if 'text' in doc:
                print(f"   Ejemplo text: {doc['text'][:80]}...")
            if 'hs_code' in doc:
                print(f"   Ejemplo hs_code: {doc['hs_code']}")
    except Exception as e:
        print(f"\n❌ {idx_name}: {e}")

# 3. Buscar específicamente "8516" o "microondas"
print("\n\n" + "=" * 80)
print("🔍 BÚSQUEDA: MICROONDAS Y 8516")
print("=" * 80)

search_terms = [
    ("microondas", {"match": {"text": "microondas"}}),
    ("8516", {"match": {"hs_code": "8516"}}),
    ("hornos eléctricos", {"match": {"text": "hornos eléctricos"}}),
]

for term, query in search_terms:
    for idx_name in ['tariff_fragments_2026']:
        try:
            result = os_client.search(index=idx_name, body={
                "query": query,
                "size": 3,
                "_source": ["text", "hs_code"]
            })
            
            hits = result['hits']['hits']
            if hits:
                print(f"\n✅ '{term}' en {idx_name}: {len(hits)} resultados")
                for hit in hits[:2]:
                    source = hit['_source']
                    code = source.get('hs_code', 'N/A')
                    text = source.get('text', 'N/A')[:60]
                    print(f"   - {code}: {text}...")
            else:
                print(f"\n❌ '{term}' en {idx_name}: 0 resultados")
        except Exception as e:
            print(f"\n❌ '{term}' en {idx_name}: {e}")

# 4. Ver qué busca el API en su config
print("\n\n" + "=" * 80)
print("⚙️  CONFIGURACIÓN DEL API")
print("=" * 80)

resp = requests.get("http://localhost:8000/health")
if resp.status_code == 200:
    print(resp.json())
