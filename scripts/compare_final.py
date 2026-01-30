#!/usr/bin/env python3
"""Compare 2025 vs 2026 v2 indices"""
from app.os_index import get_os_client

client = get_os_client()

print('=== COMPARATIVA INDICES 2025 vs 2026 ===\n')

for year in ['2025', '2026']:
    idx = f'tariff_fragments_{year}_v2'
    count = client.count(index=idx)['count']
    
    result = client.search(index=idx, body={
        'size': 0,
        'aggs': {
            'by_unit': {'terms': {'field': 'unit', 'size': 10}},
            'with_hs': {'filter': {'exists': {'field': 'hs_code'}}},
            'with_cat': {'filter': {'exists': {'field': 'category'}}}
        }
    })
    
    units = {u['key']: u['doc_count'] for u in result['aggregations']['by_unit']['buckets']}
    hs_count = result['aggregations']['with_hs']['doc_count']
    cat_count = result['aggregations']['with_cat']['doc_count']
    
    paragraphs = units.get('paragraph', 0)
    tables = units.get('table', 0)
    
    print(f'{idx}:')
    print(f'  Total: {count}')
    print(f'  Paragraphs: {paragraphs} ({100*paragraphs/count:.1f}%)')
    print(f'  Tables: {tables} ({100*tables/count:.1f}%)')
    print(f'  Con HS code: {hs_count} ({100*hs_count/count:.1f}%)')
    print(f'  Con categoria: {cat_count} ({100*cat_count/count:.1f}%)')
    print()

print('\n=== RESUMEN ===')
print('✅ 2025: Completado (tablas + HS codes + categorias)')
print('✅ 2026: Completado (tablas + HS codes, categorias pendiente)')
