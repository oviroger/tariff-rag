import requests
import json

# Test detailed response
print("\n" + "="*80)
print("DETAILED TEST: Vehicle + 50 persons + diesel")
print("="*80)

test_query = {
    "user_query": "Tengo un vehículo para 50 personas, nuevo, motor a diesel para importar de USA",
    "top_k": 5,
    "years": [2025, 2026]
}

response = requests.post(
    "http://localhost:8000/classify",
    json=test_query,
    headers={"Content-Type": "application/json"}
)

result = response.json()

print(f"Status: {response.status_code}")
print(f"\nFull Response:")
print(json.dumps(result, indent=2, ensure_ascii=False))

print(f"\nResponse keys: {list(result.keys())}")
print(f"Code field: '{result.get('code')}'")
print(f"Code type: {type(result.get('code'))}")
print(f"Top candidates count: {len(result.get('top_candidates', []))}")
if result.get('top_candidates'):
    print(f"First candidate: {result['top_candidates'][0]}")
