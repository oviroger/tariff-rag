#!/usr/bin/env python3
"""
DEBUG: Investigar por qué las confianzas de microondas son bajas
"""

import requests
import json
from typing import Any

API_URL = "http://localhost:8000"

def debug_microwave_search():
    """Hacer queries de debug sobre microondas"""
    
    print("=" * 80)
    print("🔍 DEBUG: BÚSQUEDA DE MICROONDAS - ANÁLISIS DETALLADO")
    print("=" * 80)
    
    # Test 1: Query simple de microondas
    print("\n📊 TEST 1: Query simple 'microondas'")
    print("-" * 80)
    
    payload1 = {
        "user_query": "microondas",
        "conversation_id": "debug_test_1"
    }
    
    response1 = requests.post(f"{API_URL}/classify", json=payload1)
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"Status: ✅ 200 OK")
        print(f"Top candidates found: {len(data1.get('top_candidates', []))}")
        
        for idx, cand in enumerate(data1.get('top_candidates', [])[:3], 1):
            print(f"\n  {idx}. Código: {cand.get('hs_code')} | Conf: {cand.get('confidence', 0):.2%}")
            print(f"     Descripción: {cand.get('description', 'N/A')[:60]}...")
    else:
        print(f"❌ Error: {response1.status_code}")
        print(response1.text)
    
    # Test 2: Query más específica con contexto
    print("\n\n📊 TEST 2: Query con contexto 'microondas convencional'")
    print("-" * 80)
    
    payload2 = {
        "user_query": "microondas convencional nuevo",
        "conversation_id": "debug_test_2"
    }
    
    response2 = requests.post(f"{API_URL}/classify", json=payload2)
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"Status: ✅ 200 OK")
        print(f"Top candidates found: {len(data2.get('top_candidates', []))}")
        
        for idx, cand in enumerate(data2.get('top_candidates', [])[:3], 1):
            print(f"\n  {idx}. Código: {cand.get('hs_code')} | Conf: {cand.get('confidence', 0):.2%}")
            print(f"     Descripción: {cand.get('description', 'N/A')[:60]}...")
    else:
        print(f"❌ Error: {response2.status_code}")
        print(response2.text)
    
    # Test 3: Multi-turn para simular conversación
    print("\n\n📊 TEST 3: Multi-turn conversation (como el UI)")
    print("-" * 80)
    
    conversation_id = "debug_multi_turn"
    
    queries = [
        "Quiero importar un electrodoméstico",
        "Es un microondas",
        "es un microondas convencional",
        "es nuevo"
    ]
    
    for turn, query in enumerate(queries, 1):
        print(f"\n  🔄 TURNO {turn}: '{query}'")
        
        payload = {
            "user_query": query,
            "conversation_id": conversation_id
        }
        
        response = requests.post(f"{API_URL}/classify", json=payload)
        if response.status_code == 200:
            data = response.json()
            top = data.get('top_candidates', [{}])[0]
            conf = top.get('confidence', 0)
            code = top.get('hs_code', 'N/A')
            desc = top.get('description', 'N/A')[:50]
            
            print(f"     → Resultado: {code} | {conf:.2%} | {desc}...")
        else:
            print(f"     → ❌ Error: {response.status_code}")
    
    # Test 4: Buscar qué documentos se recuperan
    print("\n\n📊 TEST 4: Verificar OpenSearch directamente")
    print("-" * 80)
    
    try:
        os_response = requests.get("http://localhost:9200/_cat/indices?format=json")
        if os_response.status_code == 200:
            indices = os_response.json()
            print(f"Índices en OpenSearch: {len(indices)}")
            for idx in indices:
                if 'tariff' in idx['index'].lower() or 'asgard' in idx['index'].lower():
                    print(f"  ✅ {idx['index']}: {idx.get('docs.count', 'N/A')} docs")
    except Exception as e:
        print(f"⚠️ No se pudo conectar a OpenSearch: {e}")
    
    # Test 5: Buscar específicamente en el índice
    print("\n\n📊 TEST 5: Búsqueda en OpenSearch - 'microondas'")
    print("-" * 80)
    
    try:
        search_query = {
            "query": {
                "multi_match": {
                    "query": "microondas",
                    "fields": ["description", "hs_code", "content"]
                }
            },
            "size": 5
        }
        
        # Encontrar índice tariff
        indices_resp = requests.get("http://localhost:9200/_cat/indices?format=json")
        tariff_indices = [idx['index'] for idx in indices_resp.json() if 'tariff' in idx['index'].lower()]
        
        if tariff_indices:
            index_name = tariff_indices[0]
            print(f"Buscando en índice: {index_name}")
            
            search_resp = requests.post(
                f"http://localhost:9200/{index_name}/_search",
                json=search_query
            )
            
            if search_resp.status_code == 200:
                hits = search_resp.json().get('hits', {}).get('hits', [])
                print(f"Documentos encontrados: {len(hits)}")
                
                for idx, hit in enumerate(hits[:3], 1):
                    source = hit['_source']
                    print(f"\n  {idx}. Score: {hit['_score']:.3f}")
                    print(f"     Código: {source.get('hs_code', 'N/A')}")
                    print(f"     Desc: {source.get('description', 'N/A')[:60]}...")
    except Exception as e:
        print(f"⚠️ Error en búsqueda OpenSearch: {e}")
    
    print("\n" + "=" * 80)
    print("✅ DEBUG COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    debug_microwave_search()
