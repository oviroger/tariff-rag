#!/usr/bin/env python3
"""
Test script to verify that conversation_id isolation works correctly.
Simulates what the UI does: multiple conversation_ids should not interfere with each other.
"""

import requests
import json
from uuid import uuid4

API_URL = "http://localhost:8000"

def test_scenario():
    """
    Scenario:
    1. User starts with "Quiero clasificar un automóvil" 
    2. User changes to "Láminas de acero"
    Both in SAME conversation_id to test if enrich logic correctly detects category change.
    """
    
    # First query: vehicle
    conv_id_1 = uuid4().hex
    print(f"\n=== CONVERSATION 1: Vehicle (ID: {conv_id_1[:8]}...) ===")
    
    payload1 = {
        "user_query": "Quiero clasificar un automóvil",
        "top_k": 5,
        "conversation_history": [],
        "conversation_id": conv_id_1
    }
    
    resp1 = requests.post(f"{API_URL}/classify", json=payload1)
    result1 = resp1.json()
    
    print(f"Query: Quiero clasificar un automóvil")
    print(f"Missing fields (first 2):")
    for mf in result1.get("missing_fields", [])[:2]:
        print(f"  - {mf}")
    print(f"Type check: {'✅ VEHICLE' if 'automóvil' in result1.get('missing_fields', [{}])[0].lower() or 'tipo específico' in str(result1.get('missing_fields', [])).lower() else '❌ NOT VEHICLE'}")
    
    # Second query in SAME conversation: steel (should be treated as category change)
    print(f"\n=== CONVERSATION 1 CONTINUED: Steel query (same ID) ===")
    
    payload2 = {
        "user_query": "Láminas de acero",
        "top_k": 5,
        "conversation_history": [
            {
                "user": "Quiero clasificar un automóvil",
                "assistant": "First response about vehicles"
            }
        ],
        "conversation_id": conv_id_1
    }
    
    resp2 = requests.post(f"{API_URL}/classify", json=payload2)
    result2 = resp2.json()
    
    print(f"Query: Láminas de acero")
    print(f"Missing fields (first 2):")
    for mf in result2.get("missing_fields", [])[:2]:
        print(f"  - {mf}")
    
    # Check: Should be steel-related, NOT vehicle-related
    is_steel_result = any(
        word in str(result2.get('missing_fields', [])).lower() 
        for word in ['lámina', 'acero', 'caliente', 'fría', 'grosor', 'espesor']
    )
    is_vehicle_result = any(
        word in str(result2.get('missing_fields', [])).lower() 
        for word in ['automóvil', 'motor', 'cilindrada', 'tipo de automóvil']
    )
    
    print(f"Type check: {'✅ STEEL' if is_steel_result else '❌ NOT STEEL'}")
    print(f"False positive: {'⚠️ STILL VEHICLE RESPONSE!' if is_vehicle_result else '✅ Not vehicle response'}")
    
    # Now test NEW conversation (fresh ID)
    conv_id_2 = uuid4().hex
    print(f"\n=== CONVERSATION 2: FRESH Steel (ID: {conv_id_2[:8]}...) ===")
    
    payload3 = {
        "user_query": "Láminas de acero",
        "top_k": 5,
        "conversation_history": [],
        "conversation_id": conv_id_2
    }
    
    resp3 = requests.post(f"{API_URL}/classify", json=payload3)
    result3 = resp3.json()
    
    print(f"Query: Láminas de acero")
    print(f"Missing fields (first 2):")
    for mf in result3.get("missing_fields", [])[:2]:
        print(f"  - {mf}")
    print(f"Type check: {'✅ STEEL' if is_steel_result else '❌ NOT STEEL'}")
    
    # Summary
    print("\n=== SUMMARY ===")
    steel_ok = is_steel_result and not is_vehicle_result
    print(f"Test result: {'✅ PASSED - Conversation isolation working!' if steel_ok else '❌ FAILED - Steel query got vehicle response'}")

if __name__ == "__main__":
    test_scenario()
