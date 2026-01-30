#!/usr/bin/env python3
"""Test: Autobus motor question - with debug logs"""

import requests
import json
from uuid import uuid4
import logging

# Setup logging para ver los logs del servidor
logging.basicConfig(level=logging.DEBUG)

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

print(f"\nRaw assistant response for history:")
print(json.dumps(result1, indent=2)[:500])

# Add to history - IMPORTANTE: guardar el resultado completo
history.append({'user': 'Necesito clasificar un autobus', 'assistant': result1})

print("\n" + "="*80)
print("[TURN 2] User: Es para 50 personas")
print("="*80)

print(f"\nHistory being sent to API (first turn missing_fields):")
print(f"  {history[0]['assistant'].get('missing_fields', [])}")

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
print("[EXPECTED BEHAVIOR]")
print("="*80)
print("Since motor was asked in TURN 1 and user chose NOT to answer it (responded about personas instead),")
print("the motor question should NOT be repeated in TURN 2 (to avoid repetitive/inconsistent conversation)")
print(f"\nMotor asked in TURN 1: {motor_asked_in_turn1}")
print(f"Motor asked in TURN 2: {motor_asked_in_turn2}")

if motor_asked_in_turn1 and not motor_asked_in_turn2:
    print("\n✅ CORRECT: Motor question removed because it was already asked in TURN 1")
elif motor_asked_in_turn1 and motor_asked_in_turn2:
    print("\n❌ WRONG: Motor question is still being repeated (inconsistent)")
