#!/usr/bin/env python3
"""
Final validation test showing the complete 4-turn lavadora classification flow
demonstrating all enhancements: pruning, code preservation, refinement, and confidence boost.
"""
import requests
import json
import uuid

def test_lavadora_flow():
    """Test the complete lavadora classification with all improvements"""
    
    url = "http://localhost:8000/classify"
    conv_id = str(uuid.uuid4())
    
    # Define the conversation flow
    turns = [
        {
            "query": "Quiero importar un electrodomestico",
            "description": "Initial generic appliance inquiry",
            "expected": {
                "code_contains": ["8509"],
                "min_confidence": 0.40,
                "level": "HS6"
            }
        },
        {
            "query": "es una lavadora",
            "description": "User identifies as washing machine (lavadora)",
            "expected": {
                "code_contains": ["8450.11"],
                "min_confidence": 0.35,
                "level": "HS6"
            }
        },
        {
            "query": "es lavadora carga frontal, 8kg, con secado",
            "description": "User provides specific appliance details",
            "expected": {
                "code_contains": ["8450.11"],
                "min_confidence": 0.70,
                "level": "HS6",
                "max_missing_fields": 2
            }
        },
        {
            "query": "voltaje 220v, 60hz, nuevo",
            "description": "User provides voltage, frequency, and condition (NEW)",
            "expected": {
                "code_exact": "8450.11.10",
                "min_confidence": 0.85,
                "level": "NANDINA8",
                "max_missing_fields": 1
            }
        }
    ]
    
    print("\n" + "="*75)
    print("LAVADORA (WASHING MACHINE) CLASSIFICATION FLOW TEST")
    print("="*75 + "\n")
    
    results = []
    all_passed = True
    
    for i, turn in enumerate(turns, 1):
        print(f"TURN {i}: {turn['description']}")
        print(f"  User says: \"{turn['query']}\"")
        
        # Make the API call
        try:
            resp = requests.post(
                url,
                json={"conversation_id": conv_id, "user_query": turn["query"]},
                timeout=15
            )
            data = resp.json()
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
            all_passed = False
            continue
        
        # Extract results
        top_cands = data.get("top_candidates", [])
        mf_list = data.get("missing_fields", [])
        
        if not top_cands:
            print(f"  [FAIL] No candidates returned!")
            all_passed = False
            continue
        
        top = top_cands[0]
        code = top.get("code", "N/A")
        confidence = top.get("confidence", 0)
        level = top.get("level", "N/A")
        years = top.get("years", [])
        
        print(f"  Classification: {code} @ {confidence:.0%} ({level})")
        print(f"  Years: {years}")
        print(f"  Missing Fields: {len(mf_list)}")
        
        # Validate against expectations
        expected = turn["expected"]
        turn_passed = True
        
        # Check code
        if "code_exact" in expected:
            if code != expected["code_exact"]:
                print(f"  [FAIL] Code should be {expected['code_exact']}, got {code}")
                turn_passed = False
                all_passed = False
            else:
                print(f"  [PASS] Code matches expected {expected['code_exact']}")
        elif "code_contains" in expected:
            if not any(x in code for x in expected["code_contains"]):
                print(f"  [FAIL] Code should contain {expected['code_contains']}")
                turn_passed = False
                all_passed = False
            else:
                print(f"  [PASS] Code contains expected pattern")
        
        # Check confidence
        if confidence < expected.get("min_confidence", 0):
            print(f"  [FAIL] Confidence {confidence:.0%} < expected {expected['min_confidence']:.0%}")
            turn_passed = False
            all_passed = False
        else:
            print(f"  [PASS] Confidence {confidence:.0%} >= {expected['min_confidence']:.0%}")
        
        # Check level
        if level != expected.get("level", level):
            print(f"  [WARN] Level is {level}, expected {expected['level']}")
        else:
            print(f"  [PASS] Level is {level}")
        
        # Check missing fields
        if "max_missing_fields" in expected:
            if len(mf_list) > expected["max_missing_fields"]:
                print(f"  [FAIL] {len(mf_list)} missing fields > expected max {expected['max_missing_fields']}")
                turn_passed = False
                all_passed = False
            else:
                print(f"  [PASS] {len(mf_list)} missing fields <= {expected['max_missing_fields']}")
        
        results.append({
            "turn": i,
            "code": code,
            "confidence": confidence,
            "level": level,
            "missing_fields": len(mf_list),
            "passed": turn_passed
        })
        
        print()
    
    # Print summary
    print("="*75)
    print("SUMMARY")
    print("="*75)
    print(f"{'Turn':<6} {'Code':<15} {'Confidence':<15} {'Level':<12} {'Missing':<10}")
    print("-"*75)
    for r in results:
        status = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"{r['turn']:<6} {r['code']:<15} {r['confidence']:.0%}{'':<10} {r['level']:<12} {r['missing_fields']:<10}")
    
    print("\n" + "="*75)
    if all_passed:
        print("SUCCESS! All tests passed. System improvements working correctly.")
    else:
        print("SOME TESTS FAILED. See details above.")
    print("="*75 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = test_lavadora_flow()
    exit(0 if success else 1)
