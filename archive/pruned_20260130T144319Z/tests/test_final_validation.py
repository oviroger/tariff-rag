#!/usr/bin/env python3
import requests
import json
import uuid
import time

url = "http://localhost:8000/classify"
conv_id = str(uuid.uuid4())

print("\n" + "=" * 75)
print("✨ 4-TURN LAVADORA CLASSIFICATION FLOW WITH ENHANCED PRUNING & PRESERVATION")
print("=" * 75)

turns = [
    ("Quiero importar un electrodoméstico", "initial: generic appliance query"),
    ("es una lavadora", "identify: washing machine"),
    ("es lavadora carga frontal, 8kg, con secado", "refine: add specific features"),
    ("voltaje 220v, 60hz, nuevo", "complete: add voltage + NEW state"),
]

results = []

for i, (query, desc) in enumerate(turns, 1):
    print(f"\n📍 TURN {i} ({desc})")
    print(f"   User Query: \"{query}\"")
    print(f"   " + "─" * 70)
    
    resp = requests.post(url, json={"conversation_id": conv_id, "user_query": query})
    data = resp.json()
    
    top_cands = data.get("top_candidates", [])
    mf_list = data.get("missing_fields", [])
    
    if top_cands:
        top = top_cands[0]
        results.append({
            "turn": i,
            "code": top.get('code'),
            "confidence": top.get('confidence'),
            "level": top.get('level'),
            "years": top.get('years'),
            "mf_count": len(mf_list)
        })
        
        print(f"   🎯 CLASSIFICATION:")
        print(f"      Code: {top.get('code')} @ {top.get('confidence'):.0%} confidence")
        print(f"      Level: {top.get('level')} | Years: {top.get('years')}")
        
        print(f"\n   📋 MISSING FIELDS ({len(mf_list)}):")
        if len(mf_list) == 0:
            print(f"      ✅ NONE - Classification complete!")
        else:
            for j, mf in enumerate(mf_list[:3], 1):
                mf_str = str(mf)
                if len(mf_str) > 65:
                    mf_str = mf_str[:62] + "..."
                print(f"      {j}. {mf_str}")
            if len(mf_list) > 3:
                print(f"      ... and {len(mf_list)-3} more")
    else:
        print("   ❌ No candidates returned!")
    
    time.sleep(0.5)  # Small delay to avoid rate limiting

print("\n" + "=" * 75)
print("📊 SUMMARY TABLE")
print("=" * 75)
print(f"{'Turn':<6} {'Code':<15} {'Confidence':<15} {'Level':<12} {'Missing Fields':<15}")
print("─" * 75)
for r in results:
    print(f"{r['turn']:<6} {r['code']:<15} {r['confidence']:.0%}{'':<10} {r['level']:<12} {r['mf_count']:<15}")

print("\n" + "=" * 75)
print("✅ EXPECTED BEHAVIOR")
print("=" * 75)
print("T1: 8509.80 @ 43%, HS6 level, ~2 missing fields (generic appliance)")
print("T2: 8450.11 @ 43%, HS6 level, ~3-4 missing fields (specific appliance)")
print("T3: 8450.11 @ 75%, HS6 level, ~1 missing field (details reduce requests)")
print("T4: 8450.11.10 @ 90%, NANDINA8 level, 0 missing fields (refined + pruned!)")
print("\n🎉 If T4 shows:")
print("   • Code ending in .10 (refined from .11)")
print("   • Confidence at 90% or higher")
print("   • NANDINA8 or NATIONAL10 level")
print("   • Zero missing fields")
print("   → SUCCESS! The fixes are working correctly.")
print("=" * 75 + "\n")
