#!/usr/bin/env python3
"""Verify Step 1: Reingest with table extraction"""

from app.os_index import get_os_client

client = get_os_client()

# Count documents
count = client.count(index='tariff_fragments_2025')['count']
print(f'\n✅ Total documentos en tariff_fragments_2025: {count}')

# Search for microondas
result = client.search(
    index='tariff_fragments_2025', 
    body={'query': {'match': {'text': 'microondas'}}}
)
hits = result['hits']['total']['value']
print(f'🔍 Búsqueda "microondas": {hits} resultados')

if hits > 0:
    print(f'   ✅ ¡Microondas ENCONTRADO!')
    hit = result['hits']['hits'][0]
    print(f'   - Documento: {hit["_id"]}')
    print(f'   - Score: {hit["_score"]:.4f}')
    print(f'   - Tipo: {hit["_source"].get("unit", "N/A")}')

# Statistics by type
agg_result = client.search(
    index='tariff_fragments_2025',
    body={
        'size': 0,
        'aggs': {
            'by_unit': {
                'terms': {'field': 'unit', 'size': 10}
            }
        }
    }
)

print(f'\n📊 Composición por tipo:')
for bucket in agg_result['aggregations']['by_unit']['buckets']:
    print(f'   - {bucket["key"]}: {bucket["doc_count"]}')

total_by_unit = sum(b['doc_count'] for b in agg_result['aggregations']['by_unit']['buckets'])
print(f'\n   Total contabilizado: {total_by_unit}')

# Check table documents
table_count = sum(
    b['doc_count'] for b in agg_result['aggregations']['by_unit']['buckets']
    if b['key'] == 'table'
)
paragraph_count = sum(
    b['doc_count'] for b in agg_result['aggregations']['by_unit']['buckets']
    if b['key'] == 'paragraph'
)

print(f'\n📈 RESULTADO:')
print(f'   - Párrafos: {paragraph_count}')
print(f'   - Tablas: {table_count}')
print(f'   - Total: {count}')

if table_count > 100:
    print(f'\n✅ STEP 1 COMPLETADO EXITOSAMENTE')
    print(f'   - Tablas extraídas: ✅ {table_count} documentos')
    print(f'   - Microondas indexado: ✅ {hits} resultados')
else:
    print(f'\n⚠️  ADVERTENCIA: Pocas tablas extraídas ({table_count})')
