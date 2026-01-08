#!/usr/bin/env python3
"""
Test the UI logic by simulating what chat_minimal_validation() does.
This validates that conversation_id isolation prevents context contamination.
"""

import requests
import json
from uuid import uuid4
from time import sleep

UI_API = "http://localhost:7860/api/chat_minimal_validation/"

def make_request(message: str, history: list, conv_id: str) -> tuple:
    """Make a request to the UI endpoint."""
    try:
        payload = {
            "data": [message, history, conv_id]
        }
        
        resp = requests.post(UI_API, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        
        # Gradio returns result in 'data' key
        if "data" in result and isinstance(result["data"], list):
            response_text = result["data"][0]
            returned_conv_id = result["data"][1] if len(result["data"]) > 1 else conv_id
            return response_text, returned_conv_id
        else:
            return str(result), conv_id
            
    except Exception as e:
        return f"ERROR: {str(e)}", conv_id

def test_ui_isolation():
    """Test that UI correctly isolates conversations."""
    
    print("\n" + "="*70)
    print("TEST: UI Conversation Isolation")
    print("="*70)
    
    # Create new conversation ID for this test
    test_conv_id = uuid4().hex
    print(f"\nTest Conversation ID: {test_conv_id[:12]}...")
    
    # Test 1: First query about vehicle
    print("\n--- Step 1: Query about vehicle ---")
    print("User input: 'Quiero clasificar un automóvil'")
    
    response1, conv_id1 = make_request(
        "Quiero clasificar un automóvil",
        [],
        test_conv_id
    )
    
    print(f"Response length: {len(response1)} chars")
    print(f"Response (first 200 chars): {response1[:200]}...")
    
    # Check if response contains vehicle-related questions
    has_vehicle_keywords = any(
        word in response1.lower() 
        for word in ['automóvil', 'vehículo', 'motor', 'cilindrada', 'tipo de automóvil']
    )
    print(f"Contains vehicle keywords: {'✅ YES' if has_vehicle_keywords else '❌ NO'}")
    
    # Test 2: Follow-up query about steel
    print("\n--- Step 2: Follow-up query about STEEL in SAME conversation ---")
    print("User input: 'Láminas de acero'")
    
    sleep(1)  # Brief pause for UI to process
    
    # Build history with previous exchange
    history = [
        [
            "Quiero clasificar un automóvil",
            response1
        ]
    ]
    
    response2, conv_id2 = make_request(
        "Láminas de acero",
        history,
        test_conv_id
    )
    
    print(f"Response length: {len(response2)} chars")
    print(f"Response (first 200 chars): {response2[:200]}...")
    
    # Check if response contains STEEL-related questions (GOOD)
    has_steel_keywords = any(
        word in response2.lower() 
        for word in ['lámina', 'acero', 'caliente', 'frío', 'grosor', 'espesor', 'dimensiones']
    )
    
    # Check if response WRONGLY contains vehicle-related questions (BAD)
    has_vehicle_keywords_2 = any(
        word in response2.lower() 
        for word in ['automóvil', 'motor', 'cilindrada', 'tipo de automóvil']
    )
    
    print(f"Contains steel keywords: {'✅ YES' if has_steel_keywords else '❌ NO'}")
    print(f"Contains vehicle keywords (should be NO): {'❌ YES - BUG!' if has_vehicle_keywords_2 else '✅ NO'}")
    
    # Summary
    print("\n" + "="*70)
    test_passed = has_steel_keywords and not has_vehicle_keywords_2
    
    if test_passed:
        print("✅ TEST PASSED: UI correctly isolates conversation context")
        print("   Steel query did not get contaminated with vehicle context")
    else:
        print("❌ TEST FAILED: UI context isolation not working")
        if not has_steel_keywords:
            print("   - Steel query did not get steel-related responses")
        if has_vehicle_keywords_2:
            print("   - Steel query still contains vehicle keywords (contamination!)")
    
    print("="*70 + "\n")
    
    return test_passed

if __name__ == "__main__":
    success = test_ui_isolation()
    exit(0 if success else 1)
