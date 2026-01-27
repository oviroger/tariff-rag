#!/usr/bin/env python3
"""Test script to verify year metadata in retrieved fragments."""

from app.os_retrieval import hybrid_search_with_fallback
from app.os_index import get_os_client

client = get_os_client()

print("=" * 70)
print("Testing dual-index search with YEAR metadata")
print("=" * 70)

# Test 1: Search both indices
print("\n[TEST 1] Searching BOTH 2025 and 2026 indices for 'motor automóvil'")
results = hybrid_search_with_fallback(client, None, "motor automóvil", k=5, years=[2025, 2026])
print(f"Found {len(results)} results\n")

for i, hit in enumerate(results[:5], 1):
    src = hit.get("_source", {})
    year_val = src.get("year", "NO_YEAR")
    score = hit.get("_score", 0)
    bucket = src.get("bucket", "?")
    doc_id = src.get("doc_id", "?")
    text = src.get("text", "")[:80]
    
    year_status = f"✅ {year_val}" if year_val != "NO_YEAR" else "❌ MISSING"
    print(f"{i}. {year_status} | Score: {score:.3f} | Bucket: {bucket}")
    print(f"   Doc: {doc_id}")
    print(f"   Text: {text}...\n")

# Test 2: Search only 2025
print("\n[TEST 2] Searching ONLY 2025 index for 'arancel'")
results_2025 = hybrid_search_with_fallback(client, None, "arancel", k=3, years=[2025])
print(f"Found {len(results_2025)} results\n")
for i, hit in enumerate(results_2025[:3], 1):
    src = hit.get("_source", {})
    print(f"{i}. Year: {src.get('year')} | Text: {src.get('text', '')[:70]}...")

# Test 3: Search only 2026
print("\n[TEST 3] Searching ONLY 2026 index for 'arancel'")
results_2026 = hybrid_search_with_fallback(client, None, "arancel", k=3, years=[2026])
print(f"Found {len(results_2026)} results\n")
for i, hit in enumerate(results_2026[:3], 1):
    src = hit.get("_source", {})
    print(f"{i}. Year: {src.get('year')} | Text: {src.get('text', '')[:70]}...")

print("\n" + "=" * 70)
print("✅ Year metadata verification complete!")
print("=" * 70)
