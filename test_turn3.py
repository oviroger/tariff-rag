#!/usr/bin/env python3
import requests
import json

# Use same conversation from previous test
conv_id = "test-conv-turn3"

url = "http://localhost:8000/classify"

# Simulated history - pretend we've been in conversation
history_setup = [
    ("Quiero importar un electrodoméstico", "8509.80"),
    ("es una lavadora", "8450.11"),
]

# Now test turn 3
query = "es lavadora carga frontal, 8kg, con secado"
resp = requests.post(url, json={"conversation_id": conv_id, "user_query": query})
data = resp.json()

top_cands = data.get("top_candidates", [])
mf_list = data.get("missing_fields", [])

print(f"Turn 3 Response:")
print(f"Status: {resp.status_code}")
print(f"\nTop Candidates ({len(top_cands)}):")
for idx, cand in enumerate(top_cands[:3]):
    print(f"  [{idx}] {cand.get('code')} - {cand.get('confidence'):.0%} ({cand.get('level')})")

print(f"\nMissing Fields ({len(mf_list)}):")
for idx, mf in enumerate(mf_list[:5]):
    print(f"  [{idx}] {mf}")

print(f"\nFull Response:")
print(json.dumps({
    "code": top_cands[0].get('code') if top_cands else None,
    "confidence": top_cands[0].get('confidence') if top_cands else None,
    "level": top_cands[0].get('level') if top_cands else None,
    "years": top_cands[0].get('years') if top_cands else None,
    "mf_count": len(mf_list)
}, indent=2))
