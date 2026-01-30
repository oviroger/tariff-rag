#!/usr/bin/env python3
"""Compare index sizes and composition."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.os_index import get_os_client

client = get_os_client()

print('\nCOMPARATIVA DE ÍNDICES 2025 vs 2026\n')
print('='*70)

for idx in ['tariff_fragments_2025_v2', 'tariff_fragments_2026_v2']:
    print(f'\nIndice: {idx}')
    print('-'*70)
    
    # Total docs
    total = client.count(index=idx)['count']
    print(f'Total documentos: {total}')
    
    # Composición por tipo
    result = client.search(
        index=idx,
        body={
            'size': 0,
            'aggs': {
                'by_unit': {
                    'terms': {'field': 'unit', 'size': 10}
                }
            }
        }
    )
    
    print(f'Composición por tipo:')
    for unit in result['aggregations']['by_unit']['buckets']:
        pct = (unit['doc_count'] / total) * 100
        print(f"  - {unit['key']}: {unit['doc_count']} ({pct:.1f}%)")
    
    # Documentos por año
    result = client.search(
        index=idx,
        body={
            'size': 0,
            'aggs': {
                'by_year': {
                    'terms': {'field': 'year', 'size': 10}
                }
            }
        }
    )
    
    print(f'Documentos por año:')
    for year in result['aggregations']['by_year']['buckets']:
        print(f"  - {int(year['key'])}: {year['doc_count']}")
    
    # Documentos únicos (doc_id)
    result = client.search(
        index=idx,
        body={
            'size': 0,
            'aggs': {
                'unique_docs': {
                    'cardinality': {'field': 'doc_id'}
                }
            }
        }
    )
    unique = result['aggregations']['unique_docs']['value']
    print(f'Documentos únicos (PDFs): {unique}')
    print(f'Promedio fragmentos por PDF: {total/unique:.1f}')

print('\n' + '='*70)
