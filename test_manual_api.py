import requests
import json

API_URL = "http://localhost:8000/classify"

# Turno 1
print("=== TURNO 1 ===")
resp1 = requests.post(API_URL, json={
    "user_query": "Hola, tengo un vehículo para importar de USA",
    "years": [2025, 2026],
    "conversation_id": None
})
data1 = resp1.json()
conv_id = data1.get("conversation_id")
print(f"Conv ID: {conv_id}")
print(f"Código: {data1['top_candidates'][0]['code']}")
print()

# Turno 2
print("=== TURNO 2 ===")
resp2 = requests.post(API_URL, json={
    "user_query": "Es para 50 personas, motor a diesel, y es nuevo",
    "years": [2025, 2026],
    "conversation_id": conv_id
})
data2 = resp2.json()
print(f"Código: {data2['top_candidates'][0]['code']}")
print(f"Description: {data2['top_candidates'][0]['description']}")
print(f"Confianza: {data2['top_candidates'][0]['confidence']}")
print(f"\nMissing fields: {data2.get('missing_fields', [])}")
