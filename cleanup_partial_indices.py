#!/usr/bin/env python3
"""
🗑️ LIMPIAR ÍNDICES PARCIALES Y REINICIAR
"""

from opensearchpy import OpenSearch

OS_HOST = "http://localhost:9200"

os_client = OpenSearch(
    hosts=[OS_HOST],
    verify_certs=False,
    timeout=10
)

print("🗑️  Eliminando índices parciales...")

for idx in ['tariff_fragments_2025_v2', 'tariff_fragments_2026_v2']:
    try:
        os_client.indices.delete(index=idx)
        print(f"   ✅ Eliminado: {idx}")
    except:
        print(f"   ⚠️  No existe: {idx}")

print("\n✅ Listo para reiniciar reindexación")
print("   Ejecuta: python step2_reindex_opensearch.py")
