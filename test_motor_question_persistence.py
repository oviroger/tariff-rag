#!/usr/bin/env python3
"""Test: Autobus motor question persistence across turns"""

import requests
import json
from uuid import uuid4

API_BASE_URL = 'http://localhost:8000'
conversation_id = str(uuid4().hex)[:16]
history = []

print("="*80)
print("[TURN 1] User: Necesito clasificar un autobus")
print("="*80)

response1 = requests.post(
    f'{API_BASE_URL}/classify',
    json={
        'user_query': 'Necesito clasificar un autobus',
        'conversation_history': history,
        'conversation_id': conversation_id
    },
    timeout=30
)
result1 = response1.json()
top_code1 = result1.get('top_candidates', [{}])[0].get('code', 'N/A')
missing1 = result1.get('missing_fields', [])

print(f"CODE: {top_code1}")
print(f"MISSING_FIELDS:")
for i, field in enumerate(missing1, 1):
    print(f"  {i}. {field}")

# Add to history
history.append({'user': 'Necesito clasificar un autobus', 'assistant': result1})

print("\n" + "="*80)
print("[TURN 2] User: Es para 50 personas")
print("="*80)

response2 = requests.post(
    f'{API_BASE_URL}/classify',
    json={
        'user_query': 'Es para 50 personas',
        'conversation_history': history,
        'conversation_id': conversation_id
    },
    timeout=30
)
result2 = response2.json()
top_code2 = result2.get('top_candidates', [{}])[0].get('code', 'N/A')
missing2 = result2.get('missing_fields', [])

print(f"CODE: {top_code2}")
print(f"MISSING_FIELDS:")
for i, field in enumerate(missing2, 1):
    print(f"  {i}. {field}")

# Analysis
motor_asked_in_turn1 = any("motor" in f.lower() for f in missing1)
motor_asked_in_turn2 = any("motor" in f.lower() for f in missing2)

print("\n" + "="*80)
print("[ANALYSIS]")
print("="*80)
print(f"Motor asked in TURN 1: {motor_asked_in_turn1}")
print(f"Motor asked in TURN 2: {motor_asked_in_turn2}")
print(f"User answered motor in TURN 2: NO (user said '50 personas', not about motor)")
print(f"\n[EXPECTATION]: Motor should STILL be asked in TURN 2 (user didn't answer)")
print(f"[ACTUAL]: Motor {'IS' if motor_asked_in_turn2 else 'IS NOT'} asked in TURN 2")

if motor_asked_in_turn2:
    print("\n✅ CORRECT: Motor question persists because user didn't answer it")
else:
    print("\n❌ WRONG: Motor question disappeared even though user didn't answer it")
