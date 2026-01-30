#!/usr/bin/env python3
"""
DEBUG: Investigar por qué hs_code es None
"""

import requests
import json

API_URL = "http://localhost:8000"

def debug_hs_code_issue():
    """Investigar el problema de hs_code = None"""
    
    print("=" * 80)
    print("🔍 DEBUG: HS_CODE = NONE - INVESTIGACIÓN")
    print("=" * 80)
    
    # Test: Una query simple
    payload = {
        "user_query": "microondas nuevo",
        "conversation_id": "debug_hs_code"
    }
    
    print(f"\nEnviando: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{API_URL}/classify", json=payload)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    data = response.json()
    print(f"\nRESPUESTA COMPLETA:")
    print(json.dumps(data, indent=2, default=str))
    
    # Analizar
    print("\n" + "=" * 80)
    print("📋 ANÁLISIS:")
    print("=" * 80)
    
    top_candidates = data.get('top_candidates', [])
    print(f"\n✓ top_candidates encontrados: {len(top_candidates)}")
    
    for idx, cand in enumerate(top_candidates[:3], 1):
        print(f"\nCandidate {idx}:")
        print(f"  - hs_code: {cand.get('hs_code')} {'❌ NONE' if cand.get('hs_code') is None else '✅'}")
        print(f"  - description: {cand.get('description', 'N/A')[:50]}")
        print(f"  - confidence: {cand.get('confidence', 'N/A')}")
        print(f"  - year: {cand.get('year', 'N/A')}")
        print(f"  - evidence: {cand.get('evidence', 'N/A')[:50] if cand.get('evidence') else 'N/A'}")
        
        # Mostrar todas las keys
        print(f"  - Keys disponibles: {list(cand.keys())}")


if __name__ == "__main__":
    debug_hs_code_issue()
