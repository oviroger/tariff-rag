#!/usr/bin/env python3
"""
DEBUG: Investigar por qué las confianzas de microondas son bajas
Problema real: El modelo está dando 42% de confianza, debería dar 80%+
"""

import requests
import json
from opensearchpy import OpenSearch

def debug_microwave_confidence():
    """Investigar por qué las confianzas son bajas"""
    
    print("=" * 80)
    print("🔍 DEBUG: ¿POR QUÉ MICROONDAS = 42% DE CONFIANZA?")
    print("=" * 80)
    
    # 1. Buscar en OpenSearch qué documentos existen sobre microondas
    print("\n1️⃣  BÚSQUEDA EN OPENSEARCH")
    print("-" * 80)
    
    try:
        os_client = OpenSearch(
            hosts=["http://localhost:9200"],
            verify_certs=False,
            timeout=10
        )
        
        # Buscar índices
        indices = os_client.cat.indices(format='json')
        tariff_indices = [idx['index'] for idx in indices if 'tariff' in idx['index'].lower()]
        print(f"Índices encontrados: {tariff_indices}")
        
        # Buscar "microondas" en cada índice
        for idx_name in tariff_indices[:1]:  # Usar el primero
            print(f"\n  Buscando en índice: {idx_name}")
            
            search_query = {
                "query": {
                    "match": {
                        "text": {
                            "query": "microondas",
                            "boost": 2.0
                        }
                    }
                },
                "size": 10,
                "_source": ["text", "hs_code", "description"]
            }
            
            result = os_client.search(index=idx_name, body=search_query)
            hits = result['hits']['hits']
            
            print(f"  Documentos encontrados: {len(hits)}")
            for i, hit in enumerate(hits[:5], 1):
                source = hit['_source']
                score = hit['_score']
                text = source.get('text', 'N/A')[:80]
                print(f"\n    {i}. Score: {score:.3f}")
                print(f"       Texto: {text}...")
                if 'hs_code' in source:
                    print(f"       HS Code: {source['hs_code']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 2. Llamar al API y ver qué retorna
    print("\n\n2️⃣  LLAMADA AL API")
    print("-" * 80)
    
    queries = [
        "microondas",
        "microondas nuevo",
        "microondas convencional",
        "horno microondas",
        "aparato para cocinar microondas"
    ]
    
    for q in queries:
        resp = requests.post("http://localhost:8000/classify", json={
            "user_query": q,
            "conversation_id": "debug_conf"
        })
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('top_candidates'):
                top = data['top_candidates'][0]
                code = top.get('code', 'N/A')
                conf = top.get('confidence', 0)
                desc = top.get('description', 'N/A')[:50]
                
                print(f"\n  Query: '{q}'")
                print(f"    Código: {code}")
                print(f"    Confianza: {conf:.2%} {'❌ BAJA' if conf < 0.7 else '✅ ALTA'}")
                print(f"    Descripción: {desc}...")
                
                # Mostrar evidencia
                evidence = data.get('evidence', [])
                if evidence:
                    print(f"    Evidencia recuperada: {len(evidence)} fragmentos")
                    top_ev = evidence[0]
                    print(f"      - Score: {top_ev.get('score', 'N/A')}")
                    print(f"      - Texto: {top_ev.get('text', 'N/A')[:50]}...")
    
    # 3. Análisis del problema
    print("\n\n3️⃣  ANÁLISIS DEL PROBLEMA")
    print("-" * 80)
    
    print("""
    POSIBLES CAUSAS DE BAJA CONFIANZA:
    
    A) 🔴 EVIDENCIA DÉBIL
       - El código 8516 existe pero está descrito como "Hornillos eléctricos y hornos de microondas"
       - La evidencia recuperada es muy general/corta
       - Score de relevancia bajo en OpenSearch
    
    B) 🔴 MODELO DE LENGUAJE
       - El prompt está siendo demasiado conservador
       - No está aprovechando el contexto conversacional
       - No tiene suficiente información en la evidencia
    
    C) 🔴 ESTRATEGIA DE RECUPERACIÓN
       - El BM25/búsqueda de OpenSearch no es lo suficientemente efectiva
       - Faltan metadatos en los documentos
       - Los embeddings no están optimizados para aranceles
    
    D) 🔴 CALIBRACIÓN DEL MODELO
       - El modelo Gemini podría estar calibrado para ser conservador
       - Las reglas de negocio (RGI) podrían estar restringiendo confianza
    
    SOLUCIONES A PROBAR:
    ✅ 1. Revisar prompts en app/prompts.py - Hacer más específico
    ✅ 2. Revisar reglas en app/rules.py - Relajar restricciones
    ✅ 3. Verificar datos en OpenSearch - ¿Tiene 8516.50?
    ✅ 4. Ajustar parámetros de búsqueda en app/os_retrieval.py
    """)


if __name__ == "__main__":
    debug_microwave_confidence()
