#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspeccionar fragmentos específicos de neumáticos para ver por qué no tienen chapter.
"""
import os
from opensearchpy import OpenSearch

os_host = "opensearch" if os.path.exists("/.dockerenv") else "localhost"

client = OpenSearch(
    hosts=[{'host': os_host, 'port': 9200}],
    http_auth=('admin', 'admin'),
    use_ssl=False,
    verify_certs=False
)

def inspect_tire_fragments():
    """Buscar fragmentos que mencionen 'Neumáticos (llantas neumáticas) nuevos' y ver su metadata."""
    for idx in ["tariff_fragments_2025", "tariff_fragments_2026"]:
        print(f"\n{'='*80}")
        print(f"INDEX: {idx}")
        print(f"{'='*80}")
        
        # Búsqueda exacta de frase que aparece en output
        body = {
            "query": {
                "match_phrase": {
                    "text": "Neumáticos (llantas neumáticas) nuevos de caucho"
                }
            },
            "size": 3
        }
        
        try:
            resp = client.search(index=idx, body=body)
            hits = resp.get("hits", {}).get("hits", [])
            print(f"\nFound {len(hits)} hits matching 'Neumáticos (llantas neumáticas) nuevos de caucho':\n")
            
            for i, hit in enumerate(hits, 1):
                src = hit["_source"]
                print(f"\n{i}. Fragment ID: {src.get('fragment_id', 'N/A')}")
                print(f"   Doc ID: {src.get('doc_id', 'N/A')}")
                print(f"   Source: {src.get('source', 'N/A')}")
                print(f"   Bucket: {src.get('bucket', 'N/A')}")
                print(f"   Chapter: {src.get('chapter', 'N/A')}")
                print(f"   Heading: {src.get('heading', 'N/A')}")
                print(f"   Subheading: {src.get('subheading', 'N/A')}")
                print(f"   Year: {src.get('year', 'N/A')}")
                text = src.get('text', '')
                print(f"   Text: {text[:300]}...")
                
                # Buscar códigos en el texto
                import re
                codes = re.findall(r'\b\d{4}(?:\.\d{2}(?:\.\d{2})?)?\b', text)
                if codes:
                    print(f"   Codes found in text: {list(set(codes))[:10]}")
                
        except Exception as e:
            print(f"Error: {e}")

inspect_tire_fragments()
