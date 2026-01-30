#!/usr/bin/env python3
"""
Test: Verificar si el LLM pregunta por motor cuando se menciona autobús
"""
import requests
import json

API_URL = "http://localhost:8000/classify"

print("=" * 80)
print("🧪 TEST: Autobús - Verificar si pregunta por tipo de motor")
print("=" * 80)

# Test 1: Vehículo genérico
print("\n[TEST 1] Consulta: 'Necesito clasificar un vehículo'")
payload1 = {
    "user_query": "Necesito clasificar un vehículo",
    "conversation_history": [],
    "top_k": 5
}
resp1 = requests.post(API_URL, json=payload1, timeout=60)
data1 = resp1.json()
if data1.get("top_candidates"):
    top1 = data1["top_candidates"][0]
    print(f"   Código: {top1['code']}")
    print(f"   Confianza: {top1['confidence']:.0%}")
    print(f"   Campos faltantes: {data1.get('missing_fields', [])}")

# Test 2: Autobús específico  
print("\n[TEST 2] Consulta: 'Es un bus para 50 personas'")
conv_history = [
    {
        "user": "Necesito clasificar un vehículo",
        "assistant": f"Código: {top1['code']}"
    }
]
payload2 = {
    "user_query": "Es un bus para 50 personas",
    "conversation_history": conv_history,
    "top_k": 5
}
resp2 = requests.post(API_URL, json=payload2, timeout=60)
data2 = resp2.json()
if data2.get("top_candidates"):
    top2 = data2["top_candidates"][0]
    print(f"   Código: {top2['code']}")
    print(f"   Confianza: {top2['confidence']:.0%}")
    print(f"   Descripción: {top2['description']}")
    missing2 = data2.get('missing_fields', [])
    print(f"   Campos faltantes: {missing2}")
    
    # Analizar si pregunta por motor
    pregunta_motor = any("motor" in str(f).lower() for f in missing2)
    print(f"\n   ✓ ¿Pregunta por tipo de motor? {pregunta_motor}")
    
    # Analizar si asumió diesel
    asumio_diesel = "diésel" in top2['description'].lower() or "diesel" in top2['description'].lower()
    print(f"   ✓ ¿Asumió diésel? {asumio_diesel}")
    
    if asumio_diesel and not pregunta_motor:
        print(f"\n   ⚠️  BUG: El LLM asumió diesel sin preguntar primero")

print("\n" + "=" * 80)
