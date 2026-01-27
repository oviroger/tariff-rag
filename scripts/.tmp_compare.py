import json

# Cargar original
with open('data/afr_done/Arancel_Boliviano_2025_Parte_1.json', encoding='utf-8') as f:
    original = json.load(f)

# Cargar filtrado
with open('data/afr_done_filtered/Arancel_Boliviano_2025_Parte_1.json', encoding='utf-8') as f:
    filtered = json.load(f)

print("=" * 80)
print("COMPARACIÓN: ORIGINAL vs FILTRADO")
print("=" * 80)
print(f"\n📊 Estadísticas:")
print(f"   Original:  {len(original['analyzeResult']['paragraphs'])} párrafos")
print(f"   Filtrado:  {filtered['stats']['filtered_paragraphs']} párrafos")
print(f"   Reducción: {filtered['stats']['reduction_percent']}%")
print(f"   Tablas:    {filtered['stats']['tables']} (mantenidas todas)")

print("\n" + "=" * 80)
print("PRIMEROS 15 PÁRRAFOS DEL ORIGINAL (sin filtrar):")
print("=" * 80)
for i, p in enumerate(original['analyzeResult']['paragraphs'][:15], 1):
    role = p.get('role', 'text')
    content = p['content'][:100].replace('\n', ' ')
    print(f"\n{i}. [{role}]")
    print(f"   {content}{'...' if len(p['content']) > 100 else ''}")

print("\n\n" + "=" * 80)
print("PRIMEROS 10 PÁRRAFOS DEL FILTRADO (relevantes):")
print("=" * 80)
for i, p in enumerate(filtered['analyzeResult']['paragraphs'][:10], 1):
    role = p.get('role', 'text')
    content = p['content'][:100].replace('\n', ' ')
    print(f"\n{i}. [{role}]")
    print(f"   {content}{'...' if len(p['content']) > 100 else ''}")
