#!/usr/bin/env python3
"""
Test rápido: Verificar respuestas del API actual
"""
import requests
import json

API_URL = "http://localhost:8000/classify"

print("=" * 80)
print("🧪 TEST: Verificando respuestas actuales del API")
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
    print(f"   Descripción: {top1['description']}")
    print(f"   Campos faltantes: {len(data1.get('missing_fields', []))}")

# Test 2: Automóvil de gasolina
print("\n[TEST 2] Consulta: 'Es un automóvil de turismo con motor de gasolina'")
conv_history = [
    {
        "user": "Necesito clasificar un vehículo",
        "assistant": f"Código: {top1['code']} ({top1['description']})"
    }
]
payload2 = {
    "user_query": "Es un automóvil de turismo con motor de gasolina",
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
    print(f"   Campos faltantes ({len(missing2)}): {missing2[:3]}")

print("\n" + "=" * 80)
print("✅ Test completado")
print("=" * 80)
