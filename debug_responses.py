#!/usr/bin/env python3
"""
Debug: See exactly what responses are being generated.
"""

import sys
sys.path.insert(0, '/app')

from ui.gradio_app import (
    chat_minimal_validation,
    get_conversation_state,
    _conversation_states
)
from uuid import uuid4

# Create a conversation ID
conv_id = uuid4().hex
print(f"Conv ID: {conv_id[:12]}...\n")

# Step 1: Vehicle query
print("=== STEP 1: Vehicle Query ===")
resp1, _ = chat_minimal_validation("Quiero clasificar un automóvil", [], conv_id)
print(f"Response:\n{resp1}\n")

# Step 2: Steel query
print("=== STEP 2: Steel Query (follow-up) ===")
history = [["Quiero clasificar un automóvil", resp1]]
resp2, _ = chat_minimal_validation("Láminas de acero", history, conv_id)
print(f"Response:\n{resp2}\n")

# Debug state
print("=== DEBUG STATE ===")
conv_state = get_conversation_state(conv_id)
print(f"last_query: {conv_state.last_query[:50]}...")
print(f"last_classification keys: {list(conv_state.last_classification.keys()) if conv_state.last_classification else 'None'}")
print(f"missing_fields: {conv_state.last_classification.get('missing_fields', [])[:2]}")
