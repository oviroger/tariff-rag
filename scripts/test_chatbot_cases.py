#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba: Simula tres casos completos de chatbot con la API.
Verifica que:
1. Ambos años (2025, 2026) aparecen en la evidencia
2. Los follow-ups mantienen el contexto correcto
3. El código arancelario se refina correctamente
"""
import requests
import json
import sys
import os
from typing import List, Dict, Any

# Configurar UTF-8
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
API_URL = "http://localhost:8000"

def test_case(name: str, queries: List[Dict[str, Any]]):
    """Simula un caso de prueba con múltiples queries (conversation flow)."""
    print(f"\n{'='*80}")
    print(f"TEST CASE: {name}")
    print(f"{'='*80}\n")
    
    history = []
    conversation_id = ""
    
    for i, query_info in enumerate(queries):
        query = query_info.get("query", "")
        step_name = query_info.get("step", f"Paso {i+1}")
        
        print(f"\n{'-'*80}")
        print(f"{step_name}")
        print(f"{'-'*80}")
        print(f"Query: {query}\n")
        
        # Preparar payload
        payload = {
            "user_query": query,
            "top_k": 5,
            "conversation_history": history,
            "conversation_id": conversation_id,
            "years": [2025, 2026]  # Ambos años
        }
        
        try:
            # Llamar API
            resp = requests.post(f"{API_URL}/classify", json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            conversation_id = data.get("conversation_id", conversation_id)
            
            # Mostrar resultados
            if data.get("top_candidates"):
                print("CANDIDATOS SUGERIDOS:")
                for j, cand in enumerate(data["top_candidates"][:3], 1):
                    code = cand.get("code", "N/A")
                    desc = cand.get("description", "")[:70]
                    conf = cand.get("confidence", 0) * 100
                    print(f"   {chr(96+j)}) {code} | {conf:.0f}% confidence | {desc}...")
            
            # Mostrar evidencia por año
            evidence = data.get("evidence", [])
            if evidence:
                years_found = {}
                for ev in evidence:
                    year = ev.get("year", "N/A")
                    years_found[year] = years_found.get(year, 0) + 1
                
                print(f"\nEVIDENCIA RECUPERADA:")
                for year, count in sorted(years_found.items()):
                    print(f"   * Año {year}: {count} fragmentos")
                
                # Verificar si hay ambos años
                if 2025 in years_found and 2026 in years_found:
                    print(f"   [OK] Ambos años presentes")
                else:
                    missing = [y for y in [2025, 2026] if y not in years_found]
                    print(f"   [WARN] Falta año: {missing}")
            
            # Información adicional
            if data.get("missing_fields"):
                print(f"\nINFORMACION FALTANTE:")
                for info in data.get("missing_fields", [])[:2]:
                    print(f"   * {info}")
            
            # Actualizar historial para siguiente query
            if data.get("top_candidates"):
                best = data["top_candidates"][0]
                history.append({
                    "role": "user",
                    "content": query
                })
                history.append({
                    "role": "assistant",
                    "content": f"Sugerencia: {best.get('code')} ({best.get('description', '')})"
                })
            
            # Verificación esperada
            expected = query_info.get("expect", {})
            if expected:
                print(f"\nEXPECTATIVAS:")
                
                # Verificar código
                if "code" in expected:
                    top_code = data.get("top_candidates", [{}])[0].get("code", "")
                    if str(expected["code"]) in str(top_code):
                        print(f"   [OK] Codigo correcto: {top_code} contiene {expected['code']}")
                    else:
                        print(f"   [FAIL] Codigo incorrecto: se esperaba {expected['code']}, se obtuvo {top_code}")
                
                # Verificar años
                if "years" in expected:
                    years_found = {ev.get("year") for ev in evidence}
                    expected_years = set(expected["years"])
                    if expected_years.issubset(years_found):
                        print(f"   [OK] Anos correctos: {expected['years']}")
                    else:
                        print(f"   [FAIL] Anos incompletos: se esperaba {expected['years']}, se encontro {years_found}")
        
        except Exception as e:
            print(f"ERROR: {e}")

# Caso 1: Electrodomésticos
test_case(
    "ELECTRODOMESTICOS DE COCINA",
    [
        {
            "step": "1 - Busqueda inicial",
            "query": "quiero importar electrodomésticos",
            "expect": {"years": [2025, 2026]}
        },
        {
            "step": "2 - Refinamiento: especificar tipo",
            "query": "es una lavadora de carga frontal",
            "expect": {"code": "8450", "years": [2025, 2026]}
        },
        {
            "step": "3 - Refinamiento: especificaciones tecnicas",
            "query": "es para uso doméstico, capacidad 8kg",
            "expect": {"code": "8450", "years": [2025, 2026]}
        },
    ]
)

# Caso 2: Equipos de cómputo
test_case(
    "EQUIPOS DE COMPUTO",
    [
        {
            "step": "1 - Busqueda inicial",
            "query": "quiero importar laptops",
            "expect": {"years": [2025, 2026]}
        },
        {
            "step": "2 - Refinamiento: especificaciones",
            "query": "14 pulgadas, 16GB RAM, 512GB SSD, nuevo",
            "expect": {"code": "8471", "years": [2025, 2026]}
        },
        {
            "step": "3 - Refinamiento: comparar con tablet",
            "query": "también tengo tablet con pantalla tactil, ¿mismo codigo?",
            "expect": {"years": [2025, 2026]}
        },
    ]
)

# Caso 3: Neumáticos
test_case(
    "NEUMATICOS PARA AUTOMOVIL",
    [
        {
            "step": "1 - Busqueda inicial",
            "query": "neumaticos radiales para automovil 205/55R16",
            "expect": {"code": "4011", "years": [2025, 2026]}
        },
        {
            "step": "2 - Refinamiento: confirmacion de tipo",
            "query": "para vehículos de pasajeros, nuevos",
            "expect": {"code": "4011", "years": [2025, 2026]}
        },
        {
            "step": "3 - Pregunta sobre variante",
            "query": "¿hay diferencia de codigo si son neumaticos usados?",
            "expect": {"years": [2025, 2026]}
        },
    ]
)

print(f"\n\n{'='*80}")
print("PRUEBAS COMPLETADAS")
print(f"{'='*80}\n")
