#!/usr/bin/env python3
"""Detailed test of motor question repetition with full logging"""

import requests
import json
from uuid import uuid4
import time

API_BASE_URL = 'http://localhost:8000'

for attempt in range(2):
    print(f"\n{'='*80}")
    print(f"ATTEMPT {attempt + 1}")
    print(f"{'='*80}\n")
    
    conversation_id = str(uuid4().hex)[:16]
    history = []

    # TURN 1
    print("[TURN 1] User: Necesito clasificar un autobus\n")
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
    missing1 = result1.get('missing_fields', [])
    
    print(f"Missing Fields in TURN 1:")
    for i, field in enumerate(missing1, 1):
        print(f"  {i}. {field}")
    
    # Save to history
    history_entry = {'user': 'Necesito clasificar un autobus', 'assistant': result1}
    history.append(history_entry)
    
    print(f"\nSaved to history:")
    print(f"  User: {history_entry['user']}")
    print(f"  Assistant missing_fields: {result1.get('missing_fields', [])}")

    time.sleep(1)

    # TURN 2
    print("\n[TURN 2] User: Es para 50 personas\n")
    
    payload = {
        'user_query': 'Es para 50 personas',
        'conversation_history': history,
        'conversation_id': conversation_id
    }
    
    print(f"Sending to API with history containing {len(history)} turns")
    print(f"History[0].assistant.missing_fields = {history[0]['assistant'].get('missing_fields', [])}")
    
    response2 = requests.post(
        f'{API_BASE_URL}/classify',
        json=payload,
        timeout=30
    )
    result2 = response2.json()
    missing2 = result2.get('missing_fields', [])
    
    print(f"\nMissing Fields in TURN 2:")
    for i, field in enumerate(missing2, 1):
        print(f"  {i}. {field}")
    
    # Check
    motor_in_t1 = any('motor' in f.lower() for f in missing1)
    motor_in_t2 = any('motor' in f.lower() for f in missing2)
    
    print(f"\n[CHECK]")
    print(f"  Motor asked in TURN 1: {motor_in_t1}")
    print(f"  Motor asked in TURN 2: {motor_in_t2}")
    
    if motor_in_t1 and not motor_in_t2:
        print(f"  ✅ PASS: Motor removed from TURN 2 (was already asked in TURN 1)")
    elif motor_in_t1 and motor_in_t2:
        print(f"  ❌ FAIL: Motor is STILL in TURN 2 (repetitive!)")
        break
    
    time.sleep(1)
