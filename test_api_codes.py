#!/usr/bin/env python3
"""
Test para verificar qué códigos retorna exactamente el API
Comparar: "Necesito clasificar un autobus"
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_api_response():
    """Verifica exactamente qué retorna el API."""
    
    print("\n" + "="*80)
    print("[TEST] Verificando códigos exactos retornados por API")
    print("="*80)
    
    # TURNO 1: "Necesito clasificar un autobus"
    print("\n[TURNO 1] Query: 'Necesito clasificar un autobus'")
    print("-"*80)
    
    payload1 = {
        "user_query": "Necesito clasificar un autobus",
        "conversation_history": [],
        "conversation_id": "test123"
    }
    
    resp1 = requests.post(f"{API_URL}/classify", json=payload1, timeout=30)
    resp1.raise_for_status()
    result1 = resp1.json()
    
    print("\n[RAW JSON - top_candidates]:")
    print(json.dumps(result1.get("top_candidates", [])[:2], indent=2))
    
    code1 = result1.get('top_candidates', [{}])[0].get('code')
    level1 = result1.get('top_candidates', [{}])[0].get('level')
    conf1 = result1.get('top_candidates', [{}])[0].get('confidence', 0)
    
    print(f"\n[EXTRACTED]")
    print(f"  code: '{code1}'")
    print(f"  level: '{level1}'")
    print(f"  confidence: {conf1*100:.0f}%")
    print(f"  len(code): {len(code1) if code1 else 0} dígitos")
    
    # Verificar diferencia
    if code1 == "8702":
        print(f"\n[WARNING] Código sin decimales: {code1} (HS4)")
    elif code1 == "8702.20":
        print(f"\n[INFO] Código con decimales: {code1} (HS6)")
    
    # TURNO 2: "Es a diesel"
    print("\n" + "="*80)
    print("[TURNO 2] Query: 'Es a diesel'")
    print("-"*80)
    
    payload2 = {
        "user_query": "Es a diesel",
        "conversation_history": [
            {
                "user": "Necesito clasificar un autobus",
                "assistant": f"Codigo: {code1}"
            }
        ],
        "conversation_id": "test123"
    }
    
    resp2 = requests.post(f"{API_URL}/classify", json=payload2, timeout=30)
    resp2.raise_for_status()
    result2 = resp2.json()
    
    print("\n[RAW JSON - top_candidates]:")
    print(json.dumps(result2.get("top_candidates", [])[:2], indent=2))
    
    code2 = result2.get('top_candidates', [{}])[0].get('code')
    level2 = result2.get('top_candidates', [{}])[0].get('level')
    conf2 = result2.get('top_candidates', [{}])[0].get('confidence', 0)
    
    print(f"\n[EXTRACTED]")
    print(f"  code: '{code2}'")
    print(f"  level: '{level2}'")
    print(f"  confidence: {conf2*100:.0f}%")
    print(f"  len(code): {len(code2) if code2 else 0} dígitos")
    
    # COMPARACIÓN
    print("\n" + "="*80)
    print("[COMPARISON]")
    print("="*80)
    print(f"TURNO 1: {code1} ({level1}) @ {conf1*100:.0f}%")
    print(f"TURNO 2: {code2} ({level2}) @ {conf2*100:.0f}%")
    
    if code1 == "8702" and code2 == "8702.20":
        print("\n[FINDING] En Turno 1 retorna HS4 sin decimales (8702)")
        print("[FINDING] En Turno 2 retorna HS6 con decimales (8702.20)")
        print("\n[HYPOTHESIS] La UI podría estar formateando para mostrar solo HS4")
    

if __name__ == "__main__":
    try:
        test_api_response()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
