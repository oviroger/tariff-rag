#!/usr/bin/env python3
"""Simple sanity check: verify that _was_motor_question_asked_in_previous_turn works correctly"""

import sys
sys.path.insert(0, '/d:/MAESTRIA - copia/tariff-rag')

from app.generator_gemini import _was_motor_question_asked_in_previous_turn, _normalize_text

# Test Case 1: Motor was asked
history1 = [
    {
        'user': 'Necesito clasificar un autobus',
        'assistant': {
            'missing_fields': ['¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)']
        }
    }
]

result1 = _was_motor_question_asked_in_previous_turn(history1)
print(f"Test 1 - Motor was asked:")
print(f"  Input: {history1[0]['assistant']['missing_fields'][0]}")
print(f"  _normalize_text result: '{_normalize_text(history1[0]['assistant']['missing_fields'][0])}'")
print(f"  Result: {result1}")
print(f"  Expected: True")
print(f"  Status: {'✅ PASS' if result1 else '❌ FAIL'}\n")

# Test Case 2: Motor was NOT asked
history2 = [
    {
        'user': 'Necesito clasificar un autobus',
        'assistant': {
            'missing_fields': ['¿Cuántas personas puede transportar?']
        }
    }
]

result2 = _was_motor_question_asked_in_previous_turn(history2)
print(f"Test 2 - Motor was NOT asked:")
print(f"  Result: {result2}")
print(f"  Expected: False")
print(f"  Status: {'✅ PASS' if not result2 else '❌ FAIL'}\n")

# Test Case 3: Motor question with different wording
history3 = [
    {
        'user': 'Necesito clasificar un autobus',
        'assistant': {
            'missing_fields': ['que tipo de motor tiene diesel gasolina electrico']
        }
    }
]

result3 = _was_motor_question_asked_in_previous_turn(history3)
print(f"Test 3 - Motor with different wording:")
print(f"  Input: {history3[0]['assistant']['missing_fields'][0]}")
print(f"  _normalize_text result: '{_normalize_text(history3[0]['assistant']['missing_fields'][0])}'")
print(f"  Result: {result3}")
print(f"  Expected: True")
print(f"  Status: {'✅ PASS' if result3 else '❌ FAIL'}\n")
