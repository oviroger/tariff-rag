#!/usr/bin/env python3
"""
Final Integration Test: Verify conversation isolation is working.
"""

import sys
sys.path.insert(0, '/app')

from ui.gradio_app import chat_minimal_validation
from uuid import uuid4

print("\n" + "="*70)
print("FINAL TEST: UI Conversation Isolation After Fix")
print("="*70)

# Create a conversation ID
conv_id = uuid4().hex
print(f"\nTest Conversation ID: {conv_id[:12]}...")

# Step 1: Vehicle query
print("\n--- Step 1: Query about VEHICLE ---")
print("Input: 'Quiero clasificar un automóvil'")

resp1, _ = chat_minimal_validation("Quiero clasificar un automóvil", [], conv_id)

has_vehicle_1 = any(
    word in resp1.lower() 
    for word in ['automóvil', 'vehículo', 'motor', 'cilindrada']
)
print(f"Result: {'✅ Vehicle keywords found' if has_vehicle_1 else '❌ No vehicle keywords'}")
if has_vehicle_1:
    print(f"  (asking about): {resp1.split('¿')[1].split('?')[0] if '¿' in resp1 else 'vehicle'}")

# Step 2: Steel query
print("\n--- Step 2: Query about STEEL (follow-up in SAME conversation) ---")
print("Input: 'Láminas de acero'")

history = [["Quiero clasificar un automóvil", resp1]]
resp2, _ = chat_minimal_validation("Láminas de acero", history, conv_id)

has_steel_2 = any(
    word in resp2.lower() 
    for word in ['lámina', 'acero', 'laminada', 'grosor', 'espesor', 'norma', 'grado']
)

has_vehicle_2 = any(
    word in resp2.lower() 
    for word in ['automóvil', 'motor', 'cilindrada', 'tipo de automóvil']
)

print(f"Result: {'✅ Steel keywords found' if has_steel_2 else '❌ No steel keywords'}")
if has_steel_2:
    print(f"  (asking about): {resp2.split('¿')[1].split('?')[0] if '¿' in resp2 else 'steel'}")

print(f"Contamination: {'⚠️ Still has vehicle keywords!' if has_vehicle_2 else '✅ No vehicle keywords'}")

# Summary
print("\n" + "="*70)
test_passed = has_vehicle_1 and has_steel_2 and not has_vehicle_2

if test_passed:
    print("✅ TEST PASSED: UI CONTEXT ISOLATION IS WORKING!")
    print("   Conversation context is properly isolated per conversation_id")
else:
    print("❌ TEST FAILED")

print("="*70 + "\n")
