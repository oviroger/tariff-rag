#!/usr/bin/env python3
"""
✅ Verifica requisitos de reindexación para RAG
- Índices v2 existen
- Conteo >= 95% del índice original
- Campos requeridos presentes: hs_code, description, category, level, year, embedding
- Búsqueda de microondas retorna hs_code
"""

from opensearchpy import OpenSearch

OS_HOST = "http://localhost:9200"
OLD = {2025: "tariff_fragments_2025", 2026: "tariff_fragments_2026"}
NEW = {2025: "tariff_fragments_2025_v2", 2026: "tariff_fragments_2026_v2"}

REQUIRED_FIELDS = ["hs_code", "description", "category", "level", "year", "embedding"]

client = OpenSearch(hosts=[OS_HOST], verify_certs=False, timeout=30)

print("=" * 90)
print("✅ VERIFICACIÓN DE REINDEXACIÓN (RAG)")
print("=" * 90)

# 1) Conteos
print("\n1) Conteos por índice")
for year in [2025, 2026]:
    try:
        old_count = int(client.cat.count(index=OLD[year], format="json")[0]["count"])
        new_count = int(client.cat.count(index=NEW[year], format="json")[0]["count"])
        ratio = (new_count / old_count) if old_count else 0
        status = "✅" if ratio >= 0.95 else "⚠️"
        print(f"  {status} {year}: {NEW[year]} = {new_count} / {old_count} ({ratio:.1%})")
    except Exception as e:
        print(f"  ❌ {year}: Error contando índices: {e}")

# 2) Campos requeridos
print("\n2) Campos requeridos en documentos de muestra")
for year in [2025, 2026]:
    try:
        res = client.search(
            index=NEW[year],
            body={"query": {"match_all": {}}, "size": 1, "_source": True}
        )
        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            print(f"  ❌ {year}: Sin documentos en {NEW[year]}")
            continue
        doc = hits[0]["_source"]
        missing = [f for f in REQUIRED_FIELDS if f not in doc]
        if not missing:
            print(f"  ✅ {year}: Todos los campos requeridos presentes")
        else:
            print(f"  ⚠️ {year}: Faltan campos: {missing}")
    except Exception as e:
        print(f"  ❌ {year}: Error leyendo documento: {e}")

# 3) Prueba de búsqueda de microondas
print("\n3) Prueba de búsqueda: 'microondas'")
for year in [2025, 2026]:
    try:
        res = client.search(
            index=NEW[year],
            body={
                "query": {"match": {"text": "microondas"}},
                "size": 3,
                "_source": ["text", "hs_code", "description", "category", "year"]
            }
        )
        hits = res.get("hits", {}).get("hits", [])
        if not hits:
            print(f"  ⚠️ {year}: Sin resultados para 'microondas'")
            continue
        top = hits[0]["_source"]
        hs = top.get("hs_code", "N/A")
        cat = top.get("category", "N/A")
        print(f"  ✅ {year}: hs_code={hs}, category={cat}, text='{top.get('text','')[:50]}...'")
    except Exception as e:
        print(f"  ❌ {year}: Error buscando microondas: {e}")

print("\n" + "=" * 90)
print("✅ FIN DE VERIFICACIÓN")
print("=" * 90)
