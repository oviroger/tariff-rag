#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import uuid
import sys

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

url = "http://localhost:8000/classify"
conv_id = str(uuid.uuid4())

turns = [
    ("Quiero importar un electrodoméstico", "generic appliance"),
    ("es una lavadora", "identify appliance"),
    ("es lavadora carga frontal, 8kg, con secado", "add details"),
    ("voltaje 220v, 60hz, nuevo", "add voltage & new state"),
]

results = []

print("\n" + "="*70)
print("TESTING 4-TURN LAVADORA FLOW")
print("="*70)

for i, (query, desc) in enumerate(turns, 1):
    print(f"\nTURN {i}: {desc}")
    print(f"Query: {query}")
    
    resp = requests.post(url, json={"conversation_id": conv_id, "user_query": query})
    data = resp.json()
    
    top_cands = data.get("top_candidates", [])
    mf_list = data.get("missing_fields", [])
    
    if top_cands:
        top = top_cands[0]
        code = top.get('code')
        conf = top.get('confidence')
        level = top.get('level')
        years = top.get('years')
        
        results.append((code, conf, level, len(mf_list)))
        
        print(f"  Code: {code} | Confidence: {conf:.0%} | Level: {level}")
        print(f"  Years: {years} | Missing Fields: {len(mf_list)}")
        
        if len(mf_list) > 0 and len(mf_list) <= 2:
            for mf in mf_list:
                mf_short = str(mf)[:60] + "..." if len(str(mf)) > 60 else str(mf)
                print(f"    - {mf_short}")

print("\n" + "="*70)
print("RESULTS SUMMARY")
print("="*70)
for turn, (code, conf, level, mf_count) in enumerate(results, 1):
    print(f"T{turn}: {code:12} {conf:6.0%}  {level:10}  Missing: {mf_count}")

print("\n" + "="*70)
print("EXPECTED: T4 should show code like 8450.11.10 with 90%+ confidence")
print("="*70)
