#!/usr/bin/env python3
import requests
import json

url = "http://localhost:8000/classify"
query = "Quiero importar un electrodomestico para la tienda"

print(f"Testing query: {query}\n")
print("="*80)

resp = requests.post(
    url,
    json={"conversation_id": "test-debug", "user_query": query},
    timeout=15
)

print(f"Status Code: {resp.status_code}")
print(f"\nFull Response:")
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

data = resp.json()
print(f"\n\nExtracted Values:")
print(f"top_candidates: {data.get('top_candidates', [])}")
print(f"missing_fields: {data.get('missing_fields', [])}")
print(f"explanation: {data.get('explanation', 'N/A')}")
