#!/usr/bin/env python3
"""
📊 MONITOR DE PROGRESO DE REINDEXACIÓN
=======================================
Consulta el estado de los índices nuevos sin interrumpir el proceso
"""

import time
from opensearchpy import OpenSearch

OS_HOST = "http://localhost:9200"

OLD_INDICES = {
    2025: "tariff_fragments_2025",
    2026: "tariff_fragments_2026"
}

NEW_INDICES = {
    2025: "tariff_fragments_2025_v2",
    2026: "tariff_fragments_2026_v2"
}

def get_index_count(os_client, index_name):
    """Obtiene el conteo de documentos de un índice"""
    try:
        result = os_client.cat.count(index=index_name, format='json')
        return int(result[0]['count'])
    except:
        return 0

def monitor_progress():
    """Monitorea el progreso de la reindexación"""
    
    os_client = OpenSearch(
        hosts=[OS_HOST],
        verify_certs=False,
        timeout=10
    )
    
    print("=" * 80)
    print("📊 MONITOR DE PROGRESO - REINDEXACIÓN")
    print("=" * 80)
    
    # Obtener conteos originales
    totals = {}
    for year in [2025, 2026]:
        totals[year] = get_index_count(os_client, OLD_INDICES[year])
    
    print(f"\n📋 Total esperado:")
    print(f"   2025: {totals[2025]:,} documentos")
    print(f"   2026: {totals[2026]:,} documentos")
    print(f"   TOTAL: {sum(totals.values()):,} documentos")
    
    # Monitorear cada 5 segundos
    print(f"\n{'Tiempo':<12} {'2025 v2':<15} {'2026 v2':<15} {'Total':<12} {'Progreso'}")
    print("-" * 80)
    
    start_time = time.time()
    
    while True:
        elapsed = int(time.time() - start_time)
        
        # Conteos actuales
        count_2025 = get_index_count(os_client, NEW_INDICES[2025])
        count_2026 = get_index_count(os_client, NEW_INDICES[2026])
        total_current = count_2025 + count_2026
        total_expected = sum(totals.values())
        
        # Calcular progreso
        progress = (total_current / total_expected * 100) if total_expected > 0 else 0
        
        # Barra de progreso
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        # Mostrar
        elapsed_str = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
        print(f"{elapsed_str:<12} {count_2025:>6,} / {totals[2025]:,}  {count_2026:>6,} / {totals[2026]:,}  {total_current:>6,}      {bar} {progress:5.1f}%", end="\r")
        
        # Terminar si llegó al 100%
        if progress >= 99.9:
            print()
            print("\n" + "=" * 80)
            print("✅ REINDEXACIÓN COMPLETADA")
            print("=" * 80)
            
            # Verificar nuevos campos
            print("\n🔍 Verificando campos nuevos...")
            for year in [2025, 2026]:
                try:
                    sample = os_client.search(
                        index=NEW_INDICES[year],
                        body={"query": {"match_all": {}}, "size": 1, "_source": True}
                    )
                    
                    if sample['hits']['hits']:
                        doc = sample['hits']['hits'][0]['_source']
                        has_hs = 'hs_code' in doc
                        has_desc = 'description' in doc
                        has_cat = 'category' in doc
                        
                        hs_val = doc.get('hs_code', 'N/A')
                        cat_val = doc.get('category', 'N/A')
                        
                        status = "✅" if (has_hs and has_desc and has_cat) else "⚠️"
                        print(f"   {status} {year}: hs_code={hs_val}, category={cat_val}")
                except:
                    print(f"   ⚠️  {year}: No se pudo verificar")
            
            break
        
        time.sleep(5)

if __name__ == "__main__":
    try:
        monitor_progress()
    except KeyboardInterrupt:
        print("\n\n⏸️  Monitor detenido por el usuario")
