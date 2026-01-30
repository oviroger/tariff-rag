import requests
import json
import time

# Espera a que el API esté listo
print("Esperando a que el API esté disponible...")
max_attempts = 20
for attempt in range(max_attempts):
    try:
        resp = requests.get("http://localhost:8000/health", timeout=2)
        if resp.status_code == 200:
            print("✓ API ready!")
            break
    except:
        if attempt < max_attempts - 1:
            print(f"  Attempt {attempt+1}/{max_attempts}: waiting...")
            time.sleep(3)
        else:
            print("✗ API did not become ready")
            exit(1)

# Test 1: Pregunta sobre vehículo con 50 personas y diesel
print("\n" + "="*80)
print("TEST 1: Vehicle + 50 persons + diesel")
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
print(f"Code returned: {result.get('top_candidates', [{}])[0].get('code', 'ERROR')}")
print(f"Confidence: {result.get('top_candidates', [{}])[0].get('confidence', 0)}")
print(f"Number of evidence docs: {len(result.get('evidence', []))}")
if result.get('evidence'):
    print(f"First evidence doc text (first 100 chars): {result['evidence'][0].get('text', '')[:100]}...")

# Verificar si el código es correcto
expected_code = "8702"  # Autobús (≥10 personas)
actual_code_full = result.get('top_candidates', [{}])[0].get('code', '')
actual_code = str(actual_code_full)[:4]
if actual_code == expected_code:
    print(f"✓ PASS: Got expected code {expected_code}.xx (specifically: {actual_code_full})")
else:
    print(f"✗ FAIL: Expected code {expected_code}.xx but got {actual_code_full}")

# Test 2: Pregunta sobre vehículo simple
print("\n" + "="*80)
print("TEST 2: Simple vehicle query")
print("="*80)

test_query2 = {
    "user_query": "vehículo para transportar",
    "top_k": 5,
    "years": [2025, 2026]
}

response2 = requests.post(
    "http://localhost:8000/classify",
    json=test_query2,
    headers={"Content-Type": "application/json"}
)

result2 = response2.json()
print(f"Status: {response2.status_code}")
print(f"Code returned: {result2.get('top_candidates', [{}])[0].get('code', 'ERROR') if result2.get('top_candidates') else 'N/A'}")
print(f"Number of evidence docs: {len(result2.get('evidence', []))}")

if len(result2.get('evidence', [])) > 0:
    print(f"✓ Got evidence documents (not empty)")
else:
    print(f"✗ No evidence documents returned")
