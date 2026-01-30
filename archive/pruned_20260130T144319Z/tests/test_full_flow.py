#!/usr/bin/env python3
"""Test full conversation flow including fruit category"""
import sys
sys.path.insert(0, '/app')
from ui.gradio_app import chat_minimal_validation
from uuid import uuid4

print("\n" + "="*70)
print("TEST COMPLETO: Vehículos → Acero → Plátanos")
print("="*70)

conv_id = uuid4().hex
print(f"\nConversation ID: {conv_id[:12]}...\n")

# Step 1: Vehículos
print("--- STEP 1: Vehículos ---")
resp1, _ = chat_minimal_validation("Necesito importar un bus", [], conv_id)
has_vehicle_1 = any(w in resp1.lower() for w in ['autobús', "transporte", 'motor', 'diesel', 'gasolina'])
print(f"Query: 'Necesito importar un bus'")
print(f"Result: {'✅ Vehicle keywords' if has_vehicle_1 else '❌ No vehicle keywords'}\n")

# Step 2: Acero
print("--- STEP 2: Acero (cambio de tema) ---")
history = [["Necesito importar un bus", resp1]]
resp2, _ = chat_minimal_validation("Láminas de acero inoxidable", history, conv_id)
has_steel_2 = any(w in resp2.lower() for w in ['acero', 'inoxidable', 'laminado', 'grosor', 'espesor'])
has_vehicle_2 = any(w in resp2.lower() for w in ['autobús', 'motor', 'diesel'])
print(f"Query: 'Láminas de acero inoxidable'")
print(f"Steel keywords: {'✅ YES' if has_steel_2 else '❌ NO'}")
print(f"Vehicle contamination: {'❌ YES - BUG!' if has_vehicle_2 else '✅ NO'}\n")

# Step 3: Plátanos (NUEVA PRUEBA)
print("--- STEP 3: Plátanos (cambio de tema) ---")
history = [
    ["Necesito importar un bus", resp1],
    ["Láminas de acero inoxidable", resp2]
]
resp3, _ = chat_minimal_validation("Ahora quiero importar plátanos", history, conv_id)
has_fruit_3 = any(w in resp3.lower() for w in ['plátano', 'platano', 'fruta', 'producción', 'proceso'])
has_vehicle_3 = any(w in resp3.lower() for w in ['autobús', 'motor', 'diesel', 'vehículo'])
has_steel_3 = any(w in resp3.lower() for w in ['acero', 'inoxidable', 'laminado', 'grosor'])

print(f"Query: 'Ahora quiero importar plátanos'")
print(f"Fruit keywords: {'✅ YES' if has_fruit_3 else '❌ NO'}")
print(f"Vehicle contamination: {'❌ YES - BUG!' if has_vehicle_3 else '✅ NO'}")
print(f"Steel contamination: {'❌ YES - BUG!' if has_steel_3 else '✅ NO'}\n")

# Summary
print("="*70)
test_passed = has_vehicle_1 and has_steel_2 and not has_vehicle_2 and has_fruit_3 and not has_vehicle_3 and not has_steel_3

if test_passed:
    print("✅ FULL TEST PASSED!")
    print("   - Vehicle query returned vehicle keywords")
    print("   - Steel query returned steel keywords (no vehicle contamination)")
    print("   - Fruit query returned fruit keywords (no previous contamination)")
else:
    print("❌ TEST FAILED")
    if not has_vehicle_1:
        print("   - Vehicle query failed")
    if not has_steel_2:
        print("   - Steel query failed")
    if has_vehicle_2:
        print("   - Vehicle contamination in steel query")
    if not has_fruit_3:
        print("   - Fruit query failed")
    if has_vehicle_3:
        print("   - Vehicle contamination in fruit query!")
    if has_steel_3:
        print("   - Steel contamination in fruit query!")

print("="*70 + "\n")
