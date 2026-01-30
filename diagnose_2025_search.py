#!/usr/bin/env python3
"""
Diagnóstico: por qué 2025_v2 no retorna "microondas"
"""
from opensearchpy import OpenSearch
import json

OS_HOST = "http://localhost:9200"
INDEX = "tariff_fragments_2025_v2"

client = OpenSearch(hosts=[OS_HOST], verify_certs=False, timeout=30)

print("=" * 90)
print("🔍 DIAGNÓSTICO BUSQUEDA 2025_v2")
print("=" * 90)

# 1) Mapping del índice
try:
    mapping = client.indices.get_mapping(index=INDEX)
    props = mapping[INDEX]["mappings"]["properties"]
    print("\n1) Campos y tipos:")
    for k in sorted(props.keys()):
        print(f"   - {k}: {props[k].get('type')}")
except Exception as e:
    print(f"❌ Error obteniendo mapping: {e}")

# 2) Documento de muestra
try:
    res = client.search(index=INDEX, body={"query": {"match_all": {}}, "size": 1, "_source": True})
    hits = res.get("hits", {}).get("hits", [])
    print("\n2) Documento ejemplo (keys):")
    if hits:
        doc = hits[0]["_source"]
        print(sorted(list(doc.keys())))
        sample_text = doc.get("text") or doc.get("content") or ""
        print(f"   sample text: {sample_text[:80]}...")
    else:
        print("   ❌ Sin documentos")
except Exception as e:
    print(f"❌ Error leyendo doc: {e}")

# 3) Buscar microondas en distintos campos
queries = [
    ("text", {"match": {"text": "microondas"}}),
    ("content", {"match": {"content": "microondas"}}),
    ("description", {"match": {"description": "microondas"}}),
]

print("\n3) Búsquedas por campo:")
for label, q in queries:
    try:
        res = client.search(index=INDEX, body={"query": q, "size": 3, "_source": ["text", "content", "description", "hs_code"]})
        hits = res.get("hits", {}).get("hits", [])
        if hits:
            top = hits[0]["_source"]
            txt = (top.get("text") or top.get("content") or top.get("description") or "")
            print(f"   ✅ {label}: {len(hits)} hits | hs_code={top.get('hs_code')} | text='{txt[:50]}...'")
        else:
            print(f"   ⚠️ {label}: 0 hits")
    except Exception as e:
        print(f"   ❌ {label}: error {e}")

# 4) Consulta multi_match
print("\n4) multi_match (text, content, description)")
try:
    res = client.search(
        index=INDEX,
        body={
            "query": {
                "multi_match": {
                    "query": "microondas",
                    "fields": ["text", "content", "description"]
                }
            },
            "size": 3,
            "_source": ["text", "content", "description", "hs_code"]
        }
    )
    hits = res.get("hits", {}).get("hits", [])
    if hits:
        top = hits[0]["_source"]
        txt = (top.get("text") or top.get("content") or top.get("description") or "")
        print(f"   ✅ multi_match: {len(hits)} hits | hs_code={top.get('hs_code')} | text='{txt[:50]}...'")
    else:
        print("   ⚠️ multi_match: 0 hits")
except Exception as e:
    print(f"   ❌ multi_match error: {e}")

print("\n" + "=" * 90)
print("✅ FIN DIAGNÓSTICO")
print("=" * 90)
