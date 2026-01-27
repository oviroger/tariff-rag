#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para inspeccionar directamente los fragmentos sobre neumáticos en OpenSearch.
"""
import json
from opensearchpy import OpenSearch

# Conectar a OpenSearch
client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_auth=('admin', 'admin'),
    use_ssl=False,
    verify_certs=False
)

def search_by_text(index, query_text):
    """Buscar fragmentos que contengan texto específico."""
    search_body = {
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["text", "chapter", "heading", "subheading"],
                "type": "best_fields"
            }
        },
        "size": 20
    }
    
    results = client.search(index=index, body=search_body)
    return results

def search_by_chapter(index, chapter):
    """Buscar fragmentos por número de capítulo."""
    search_body = {
        "query": {
            "term": {
                "chapter": chapter
            }
        },
        "size": 20
    }
    
    results = client.search(index=index, body=search_body)
    return results

def search_by_code(index, code):
    """Buscar fragmentos que contengan un código arancelario específico."""
    search_body = {
        "query": {
            "multi_match": {
                "query": code,
                "fields": ["text"],
                "type": "phrase"
            }
        },
        "size": 20
    }
    
    results = client.search(index=index, body=search_body)
    return results

print("\n" + "="*80)
print("SEARCHING FOR NEUMATICOS DOCUMENTS IN OPENSEARCH")
print("="*80)

# Buscar en ambos índices
for index in ["tariff_fragments_2025", "tariff_fragments_2026"]:
    print(f"\n{'─'*80}")
    print(f"INDEX: {index}")
    print(f"{'─'*80}")
    
    # 1. Buscar por "4011" (código de neumáticos)
    print("\n1. Search by code '4011':")
    try:
        results = search_by_code(index, "4011")
        print(f"   Found: {len(results['hits']['hits'])} documents")
        for i, hit in enumerate(results['hits']['hits'][:3], 1):
            doc = hit['_source']
            text = doc.get('text', '')[:100]
            print(f"   {i}. Chapter={doc.get('chapter')} | Text: {text}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Buscar por capitulo 40 (caucho)
    print("\n2. Search by chapter '40' (caucho/rubber):")
    try:
        results = search_by_chapter(index, 40)
        print(f"   Found: {len(results['hits']['hits'])} documents")
        for i, hit in enumerate(results['hits']['hits'][:3], 1):
            doc = hit['_source']
            text = doc.get('text', '')[:100]
            print(f"   {i}. Heading={doc.get('heading')} | Text: {text}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Buscar por "neumáticos de caucho"
    print("\n3. Search by 'neumáticos de caucho':")
    try:
        results = search_by_text(index, "neumáticos de caucho")
        print(f"   Found: {len(results['hits']['hits'])} documents")
        for i, hit in enumerate(results['hits']['hits'][:3], 1):
            doc = hit['_source']
            text = doc.get('text', '')[:100]
            code = doc.get('heading', '')
            print(f"   {i}. Heading={code} | Text: {text}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 4. Buscar por "neumáticos nuevos"
    print("\n4. Search by 'neumáticos nuevos':")
    try:
        results = search_by_text(index, "neumáticos nuevos")
        print(f"   Found: {len(results['hits']['hits'])} documents")
        for i, hit in enumerate(results['hits']['hits'][:3], 1):
            doc = hit['_source']
            text = doc.get('text', '')[:100]
            code = doc.get('heading', '')
            print(f"   {i}. Heading={code} | Text: {text}...")
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "="*80)
