#!/usr/bin/env python3
"""
Test: Verificar que no se repiten preguntas de motor inconsistentemente
REQUISITO: Si motor fue preguntado en TURN N-1 sin ser respondido,
NO debe volver a preguntarse en TURN N (para mantener coherencia conversacional)
"""

import requests
from uuid import uuid4


def test_motor_question_not_repeated():
    """
    Test case: Motor question should not be repeated if already asked in previous turn
    """
    API_BASE_URL = 'http://localhost:8000'
    conversation_id = str(uuid4().hex)[:16]
    history = []

    print("\n" + "="*80)
    print("TEST: Motor Question Consistency")
    print("="*80)
    
    # TURN 1: User asks to classify a bus
    print("\n[TURN 1] User: Necesito clasificar un autobus\n")
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
    
    motor_in_turn1 = any('motor' in f.lower() for f in missing1)
    print(f"Missing fields in TURN 1: {len(missing1)}")
    for field in missing1:
        print(f"  • {field[:70]}...")
    print(f"\nMotor question present: {motor_in_turn1}")
    
    # Save to history
    history.append({'user': 'Necesito clasificar un autobus', 'assistant': result1})
    
    assert motor_in_turn1, "❌ FAIL: Motor should be asked in TURN 1 for vehicles"
    
    # TURN 2: User answers about capacity (NOT motor)
    print("\n[TURN 2] User: Es para 50 personas\n")
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
    missing2 = result2.get('missing_fields', [])
    
    motor_in_turn2 = any('motor' in f.lower() for f in missing2)
    print(f"Missing fields in TURN 2: {len(missing2)}")
    for field in missing2:
        print(f"  • {field[:70]}...")
    print(f"\nMotor question present: {motor_in_turn2}")
    
    # Assertion: Motor should NOT be repeated
    assert not motor_in_turn2, \
        "❌ FAIL: Motor should NOT be repeated in TURN 2 (already asked, user chose not to answer)"
    
    print("\n" + "="*80)
    print("✅ TEST PASSED: Motor question consistency maintained!")
    print("="*80)
    print("\nSummary:")
    print(f"  • TURN 1 asked motor: {motor_in_turn1} ✓")
    print(f"  • TURN 2 repeats motor: {motor_in_turn2} ✓ (should be False)")
    print(f"  • Conversation flow is now consistent and not repetitive")


if __name__ == '__main__':
    try:
        test_motor_question_not_repeated()
    except AssertionError as e:
        print(f"\n{e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
