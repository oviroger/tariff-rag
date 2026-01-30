#!/usr/bin/env python3
import requests
import uuid

url = "http://localhost:8000/classify"
conv_id = str(uuid.uuid4())

# Test Turn 3 and 4 specifically
turns_3_4 = [
    ("es lavadora carga frontal, 8kg, con secado", 3),
    ("voltaje 220v, 60hz, nuevo", 4),
]

# First, set up the history by running turn 1-2
setup_turns = [
    "Quiero importar un electrodomestico",
    "es una lavadora",
]

for q in setup_turns:
    requests.post(url, json={"conversation_id": conv_id, "user_query": q})

# Now test turns 3-4
for query, turn in turns_3_4:
    resp = requests.post(url, json={"conversation_id": conv_id, "user_query": query})
    data = resp.json()
    top = data.get("top_candidates", [{}])[0]
    mf_count = len(data.get("missing_fields", []))
    
    print(f"TURN {turn}:")
    print(f"  Query: {query[:45]}")
    print(f"  Code: {top.get('code')}")
    print(f"  Confidence: {top.get('confidence'):.1%}")
    print(f"  Level: {top.get('level')}")
    print(f"  Missing Fields: {mf_count}")
    print()
