#!/usr/bin/env python3
"""Verificar estado del indice 2026 despues del reingest"""
import logging
from app.os_index import get_os_client

logging.basicConfig(level=logging.INFO, format='%(message)s')

try:
    client = get_os_client()
    idx = 'tariff_fragments_2026'
    
    # Count
    count = client.count(index=idx, timeout=30)['count']
    print(f'Documentos en {idx}: {count}')
    
    # Composition
    result = client.search(
        index=idx,
        body={
            'size': 0,
            'aggs': {
                'by_unit': {
                    'terms': {'field': 'unit', 'size': 20}
                }
            }
        }
    )
    
    print(f'\nComposicion:')
    for unit in result['aggregations']['by_unit']['buckets']:
        print(f"  - {unit['key']}: {unit['doc_count']}")
    
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
