#!/usr/bin/env python3
"""Investigar el contenido del JSON 2026."""
import json
from pathlib import Path

# Comparar estructura y contenido de 2025 vs 2026
data_dir_2025 = Path("data/afr_done")
data_dir_2026 = Path("data/afr_done_2026")

print("=== INVESTIGACIÓN 2025 vs 2026 ===\n")

# 2025 - Primera parte
json_2025 = data_dir_2025 / "Arancel_Boliviano_2025_Parte_1.json"
if json_2025.exists():
    with open(json_2025, 'r', encoding='utf-8') as f:
        data_2025 = json.load(f)
    
    paras_2025 = data_2025.get("analyzeResult", {}).get("paragraphs", [])
    print(f"2025 - Total párrafos: {len(paras_2025)}")
    
    # Buscar "electrodoméstico" o "lavadora"
    found_terms_2025 = []
    for i, p in enumerate(paras_2025[:1000]):  # Primeros 1000
        text = p.get("content", "").lower()
        if "electrodoméstico" in text or "lavadora" in text or "capítulo 85" in text or "capítulo 84" in text:
            found_terms_2025.append((i, text[:100]))
    
    print(f"  - Párrafos con 'electrodoméstico'/'lavadora'/cap 85-84: {len(found_terms_2025)}")
    if found_terms_2025:
        print(f"  - Ejemplo: {found_terms_2025[0][1]}\n")

# 2026 - Primera parte
json_2026 = data_dir_2026 / "Arancel 2026_1.pdf.json"
if json_2026.exists():
    with open(json_2026, 'r', encoding='utf-8') as f:
        data_2026 = json.load(f)
    
    paras_2026 = data_2026.get("analyzeResult", {}).get("paragraphs", [])
    print(f"2026 - Total párrafos: {len(paras_2026)}")
    
    # Buscar "electrodoméstico" o "lavadora"
    found_terms_2026 = []
    for i, p in enumerate(paras_2026[:1000]):  # Primeros 1000
        text = p.get("content", "").lower()
        if "electrodoméstico" in text or "lavadora" in text or "capítulo 85" in text or "capítulo 84" in text:
            found_terms_2026.append((i, text[:100]))
    
    print(f"  - Párrafos con 'electrodoméstico'/'lavadora'/cap 85-84: {len(found_terms_2026)}")
    if found_terms_2026:
        print(f"  - Ejemplo: {found_terms_2026[0][1]}\n")

# Ver primeros párrafos 2026
print("\n=== PRIMEROS 5 PÁRRAFOS DEL 2026 ===")
for i, p in enumerate(paras_2026[:5]):
    text = p.get("content", "")[:150]
    print(f"{i}: {text}...\n")

# Estadísticas de longitud
lengths_2025 = [len(p.get("content", "")) for p in paras_2025]
lengths_2026 = [len(p.get("content", "")) for p in paras_2026]

print("\n=== ESTADÍSTICAS DE LONGITUD ===")
print(f"2025 - Promedio: {sum(lengths_2025)/len(lengths_2025):.0f} chars, Max: {max(lengths_2025)}, Min: {min(lengths_2025)}")
print(f"2026 - Promedio: {sum(lengths_2026)/len(lengths_2026):.0f} chars, Max: {max(lengths_2026)}, Min: {min(lengths_2026)}")

# Buscar capítulo/heading en los párrafos
print("\n=== BÚSQUEDA DE PATRONES DE CAPÍTULOS ===")
import re

for idx, name, paras in [(0, "2025", paras_2025), (1, "2026", paras_2026)]:
    chapters_found = {}
    for p in paras[:2000]:
        text = p.get("content", "")
        # Buscar capítulo XX
        ch_match = re.search(r'cap[íi]tulo\s+(\d{2})', text, re.IGNORECASE)
        if ch_match:
            ch = ch_match.group(1)
            chapters_found[ch] = chapters_found.get(ch, 0) + 1
    
    print(f"\n{name} - Capítulos encontrados (primeros 2000 párrafos):")
    for ch in sorted(chapters_found.keys())[:10]:
        print(f"  Capítulo {ch}: {chapters_found[ch]} menciones")
