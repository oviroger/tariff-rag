#!/usr/bin/env python3
"""
Final integration test: Simulate the exact flow that chat_minimal_validation() uses.
This test will verify that conversation_id isolation prevents context contamination.
"""

import sys
sys.path.insert(0, '/app')

from ui.gradio_app import (
    chat_minimal_validation,
    get_conversation_state,
    reset_conversation_state,
    _conversation_states
)
from uuid import uuid4

def test_conversation_isolation():
    """Test that conversation isolation works at the UI level."""
    
    print("\n" + "="*70)
    print("INTEGRATION TEST: UI Conversation Isolation")
    print("="*70)
    
    # Create a conversation ID
    conv_id = uuid4().hex
    print(f"\nTest Conversation ID: {conv_id[:12]}...")
    
    # Step 1: Query about vehicle
    print("\n--- Step 1: Query about VEHICLE ---")
    print("Input: 'Quiero clasificar un automóvil'")
    
    response1, returned_id1 = chat_minimal_validation(
        "Quiero clasificar un automóvil",
        [],
        conv_id
    )
    
    print(f"Response length: {len(response1)} chars")
    
    # Check vehicle keywords
    has_vehicle_1 = any(
        word in response1.lower() 
        for word in ['automóvil', 'vehículo', 'motor', 'tipo específico', 'uso del vehículo']
    )
    print(f"Contains vehicle keywords: {'✅ YES' if has_vehicle_1 else '❌ NO'}")
    
    # Verify conversation state was created
    print(f"State created in dict: {conv_id in _conversation_states}")
    conv_state_1 = get_conversation_state(conv_id)
    print(f"last_query in state: {conv_state_1.last_query[:30]}...")
    
    # Step 2: Follow-up query about STEEL
    print("\n--- Step 2: Follow-up query about STEEL (same conversation_id) ---")
    print("Input: 'Láminas de acero'")
    
    # Build history as Gradio would do it
    history = [
        [
            "Quiero clasificar un automóvil",
            response1
        ]
    ]
    
    response2, returned_id2 = chat_minimal_validation(
        "Láminas de acero",
        history,
        conv_id
    )
    
    print(f"Response length: {len(response2)} chars")
    
    # Check steel keywords
    has_steel_2 = any(
        word in response2.lower() 
        for word in ['lámina', 'acero', 'caliente', 'frío', 'grosor', 'espesor', 'proceso de fabricación']
    )
    
    # Check for wrongful vehicle keywords
    has_vehicle_2 = any(
        word in response2.lower() 
        for word in ['automóvil', 'motor', 'cilindrada', 'tipo de automóvil', 'uso del vehículo']
    )
    
    print(f"Contains steel keywords: {'✅ YES' if has_steel_2 else '❌ NO'}")
    print(f"Contains vehicle keywords (should be NO): {'❌ YES - BUG!' if has_vehicle_2 else '✅ NO'}")
    
    # Verify conversation state was updated
    conv_state_2 = get_conversation_state(conv_id)
    print(f"last_query updated: {conv_state_2.last_query[:30]}...")
    
    # Display state contents
    print(f"\nConversation state contents:")
    print(f"  - History entries: {len(conv_state_2.history)}")
    print(f"  - Has classification: {bool(conv_state_2.last_classification)}")
    
    # Summary
    print("\n" + "="*70)
    test_passed = has_steel_2 and not has_vehicle_2 and has_vehicle_1
    
    if test_passed:
        print("✅ INTEGRATION TEST PASSED")
        print("   Conversation isolation works correctly:")
        print("   1. First vehicle query returns vehicle keywords")
        print("   2. Second steel query in same conversation returns steel keywords")
        print("   3. NO context contamination between different product types")
    else:
        print("❌ INTEGRATION TEST FAILED")
        if not has_vehicle_1:
            print("   - First query did not detect vehicles")
        if not has_steel_2:
            print("   - Second query did not detect steel")
        if has_vehicle_2:
            print("   - Second query got contaminated with vehicle keywords!")
    
    print("="*70 + "\n")
    
    return test_passed

if __name__ == "__main__":
    try:
        success = test_conversation_isolation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
