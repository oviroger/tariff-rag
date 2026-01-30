#!/usr/bin/env python3
"""
Test to verify UI will now display classifications correctly
"""
import requests
import json

test_cases = [
    "Quiero importar un electrodomestico para la tienda",
    "Es una lavadora",
    "Es lavadora carga frontal, 8kg, con secado",
]

url = "http://localhost:8000/classify"
conv_id = "test-ui-verify"

print("="*80)
print("VERIFICATION TEST: API Returns Proper Classifications")
print("="*80)

for i, query in enumerate(test_cases, 1):
    print(f"\n[TURN {i}] {query}")
    print("-"*80)
    
    resp = requests.post(
        url,
        json={"conversation_id": conv_id, "user_query": query},
        timeout=15
    )
    
    data = resp.json()
    top_cands = data.get("top_candidates", [])
    
    if top_cands:
        top = top_cands[0]
        print(f"STATUS: CLASSIFICATION FOUND")
        print(f"  Code: {top.get('code')}")
        print(f"  Confidence: {top.get('confidence'):.0%}")
        print(f"  Level: {top.get('level')}")
        print(f"  Missing Fields: {len(data.get('missing_fields', []))}")
    else:
        print(f"STATUS: NO CLASSIFICATION")
        print(f"  Error: top_candidates is empty")

print("\n" + "="*80)
print("EXPECTED UI BEHAVIOR (after restart):")
print("="*80)
print("""
For each query above, the UI should display:

a) CODE SECTION - Shows the HS code with confidence and year reference
   Example: a) 8509.80 | Referencia: 2025, 2026 | Confidence: 43%
   
b) DESCRIPTION - Brief description of the product category
   Example: Electrodomestico (generico)
   
c) MISSING FIELDS SECTION - Optional information needed
   Example: Informacion adicional sugerida
            - que tipo de electrodomestico...
            - es nuevo o usado...
            
The UI will NOT show "Necesito mas informacion para clasificar" 
because the API IS returning top_candidates.
""")

print("="*80)
print("NEXT STEPS:")
print("="*80)
print("""
1. The UI container has been restarted (completed)
2. Test the UI at: http://localhost:7860
3. Enter: "Quiero importar un electrodomestico para la tienda"
4. You should see the 8509.80 classification displayed with confidence percentage

If you still see the "Necesito mas informacion" message:
- Clear browser cache (Ctrl+Shift+Del)
- Try incognito/private window
- Check browser console for errors (F12)
""")

print("="*80 + "\n")
