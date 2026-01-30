#!/usr/bin/env python3
"""
Test para verificar si los parámetros 'years' afectan los códigos retornados
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_with_years():
    """Compara respuestas con y sin filtro de años."""
    
    print("\n" + "="*80)
    print("[TEST] Comparando códigos CON y SIN filtro de años")
    print("="*80)
    
    # TEST 1: SIN years (parámetro omitido)
    print("\n[SCENARIO 1] Sin parámetro years")
    print("-"*80)
    
    payload1 = {
        "user_query": "Necesito clasificar un autobus",
        "conversation_history": []
    }
    
    resp1 = requests.post(f"{API_URL}/classify", json=payload1, timeout=30)
    resp1.raise_for_status()
    result1 = resp1.json()
    code1_no_years = result1.get('top_candidates', [{}])[0].get('code')
    
    print(f"Código sin years: {code1_no_years}")
    
    # TEST 2: CON years=[2025, 2026]
    print("\n[SCENARIO 2] Con years=[2025, 2026]")
    print("-"*80)
    
    payload2 = {
        "user_query": "Necesito clasificar un autobus",
        "conversation_history": [],
        "years": [2025, 2026]
    }
    
    resp2 = requests.post(f"{API_URL}/classify", json=payload2, timeout=30)
    resp2.raise_for_status()
    result2 = resp2.json()
    code1_with_years = result2.get('top_candidates', [{}])[0].get('code')
    
    print(f"Código con years: {code1_with_years}")
    
    # TEST 3: CON years=[2025]
    print("\n[SCENARIO 3] Con years=[2025]")
    print("-"*80)
    
    payload3 = {
        "user_query": "Necesito clasificar un autobus",
        "conversation_history": [],
        "years": [2025]
    }
    
    resp3 = requests.post(f"{API_URL}/classify", json=payload3, timeout=30)
    resp3.raise_for_status()
    result3 = resp3.json()
    code1_year_2025 = result3.get('top_candidates', [{}])[0].get('code')
    
    print(f"Código con years=[2025]: {code1_year_2025}")
    
    # COMPARACIÓN
    print("\n" + "="*80)
    print("[COMPARISON]")
    print("="*80)
    print(f"Sin years: {code1_no_years}")
    print(f"Con years=[2025, 2026]: {code1_with_years}")
    print(f"Con years=[2025]: {code1_year_2025}")
    
    if code1_no_years == code1_with_years == code1_year_2025:
        print("\n[CONCLUSION] Los parámetros 'years' NO afectan el código retornado")
    else:
        print("\n[CONCLUSION] Los parámetros 'years' SÍ afectan los códigos retornados")

if __name__ == "__main__":
    try:
        test_with_years()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
