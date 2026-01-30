#!/usr/bin/env python3
import requests
import json
import uuid

url = "http://localhost:8000/classify"
conv_id = str(uuid.uuid4())

print("=" * 70)
print("TESTING 4-TURN LAVADORA FLOW WITH NEW PRUNING & PRESERVATION LOGIC")
print("=" * 70)

turns = [
    ("Quiero importar un electrodoméstico", "generic appliance"),
    ("es una lavadora", "identify as washing machine"),
    ("es lavadora carga frontal, 8kg, con secado", "add specific details"),
    ("voltaje 220v, 60hz, nuevo", "add voltage and NEW state"),
]

for i, (query, desc) in enumerate(turns, 1):
    print(f"\n📌 TURN {i}: {desc}")
    print(f"   Query: \"{query}\"")
    
    resp = requests.post(url, json={"conversation_id": conv_id, "user_query": query})
    data = resp.json()
    
    top = data.get("top_candidates", [{}])[0]
    mf_count = len(data.get("missing_fields", []))
    
    print(f"   ➜ Code: {top.get('code')} | Level: {top.get('level')}")
    print(f"   ➜ Confidence: {top.get('confidence'):.1%} | Missing Fields: {mf_count}")
    
    if mf_count > 0 and mf_count <= 3:
        print(f"   Missing:")
        for mf in data.get('missing_fields', [])[:3]:
            mf_str = str(mf)
            if len(mf_str) > 70:
                mf_str = mf_str[:67] + "..."
            print(f"      • {mf_str}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("✅ System should show:")
print("   T1: 8509.80 @ 43%, HS6, 2 missing fields")
print("   T2: 8450.11 @ 38%, HS6, ~4 missing fields")
print("   T3: 8450.11 @ 64%, HS6, ~4 missing fields (same as T2, no 'nueva' yet)")
print("   T4: 8450.11.10 @ 90%, NANDINA8, 0-1 missing fields (with confidence boost!)")
