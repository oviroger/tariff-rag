#!/usr/bin/env python3
import requests
import json
import uuid

url = "http://localhost:8000/classify"
conv_id = str(uuid.uuid4())

turns = [
    "Quiero importar un electrodoméstico",
    "es una lavadora",
    "es lavadora carga frontal, 8kg, con secado",
    "voltaje 220v, 60hz, nuevo"
]

for i, query in enumerate(turns, 1):
    resp = requests.post(url, json={"conversation_id": conv_id, "user_query": query})
    data = resp.json()
    
    top = data.get("top_candidates", [{}])[0]
    mf_count = len(data.get("missing_fields", []))
    
    print(f"\n✅ Turn {i}: {query[:40]}...")
    print(f"   Code: {top.get('code', 'N/A')}")
    print(f"   Confidence: {top.get('confidence', 'N/A'):.2%}")
    print(f"   Level: {top.get('level', 'N/A')}")
    print(f"   Years: {top.get('years', 'N/A')}")
    print(f"   Missing Fields: {mf_count}")
    if mf_count > 0 and mf_count <= 3:
        for field in data.get('missing_fields', []):
            print(f"      - {field}")
