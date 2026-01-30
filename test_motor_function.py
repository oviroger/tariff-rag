#!/usr/bin/env python3
"""Direct test of the _was_motor_question_asked_in_previous_turn function"""

import sys
sys.path.insert(0, '/d:/MAESTRIA - copia/tariff-rag')

from app.generator_gemini import _was_motor_question_asked_in_previous_turn

# Simulate a conversation history where motor was asked in Turn 1
conversation_history = [
    {
        'user': 'Necesito clasificar un autobus',
        'assistant': {
            'top_candidates': [{'code': '8702.90', 'description': 'Autobús', 'confidence': 0.52}],
            'missing_fields': ['¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)']
        }
    }
]

result = _was_motor_question_asked_in_previous_turn(conversation_history)
print(f"Motor asked in previous turn: {result}")
print(f"Expected: True")
print(f"Status: {'✅ PASS' if result else '❌ FAIL'}")
