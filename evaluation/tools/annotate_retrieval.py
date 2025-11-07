"""
Herramienta interactiva para anotar relevancia en el CSV de evaluación de retrieval.
Muestra query + snippet, permite marcar relevancia (0/1/skip), y guarda progreso incremental.

Uso:
    python evaluation/tools/annotate_retrieval.py --csv evaluation/templates/eval_retrieval_asgard.csv

Controles:
    1 = Relevante
    0 = No relevante
    s = Skip (dejar vacío)
    q = Quit (guardar y salir)
    ? = Ver instrucciones completas

La columna 'relevance' se actualiza en el CSV original.
"""

import csv
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional


def clear_screen():
    """Limpia la pantalla (compatible con Windows/Linux)"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def print_instructions():
    """Imprime instrucciones completas"""
    print("\n" + "="*80)
    print("INSTRUCCIONES DE ANOTACIÓN DE RELEVANCIA")
    print("="*80)
    print("""
Un documento es RELEVANTE (1) si:
  ✓ Contiene información que ayudaría a clasificar correctamente el producto
  ✓ Menciona el capítulo HS correcto o productos similares
  ✓ Describe características, materiales o usos relacionados con la query
  ✓ Proporciona contexto útil para la clasificación arancelaria

Un documento es NO RELEVANTE (0) si:
  ✗ Habla de productos completamente diferentes
  ✗ Menciona capítulos HS no relacionados
  ✗ Es texto genérico sin valor para la clasificación
  ✗ Contiene información contradictoria o confusa

CRITERIO PRÁCTICO: Si fueras un agente de aduana, ¿te ayudaría este fragmento
                    a clasificar el producto descrito en la query?

Controles:
    1     = Marcar como RELEVANTE
    0     = Marcar como NO RELEVANTE
    s     = SKIP (dejar vacío, revisar después)
    b     = BACK (volver al registro anterior)
    q     = QUIT (guardar progreso y salir)
    ?     = Ver estas instrucciones
""")
    print("="*80 + "\n")


def load_csv(path: str) -> List[Dict]:
    """Carga el CSV y retorna lista de diccionarios"""
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def save_csv(path: str, rows: List[Dict], fieldnames: List[str]):
    """Guarda el CSV con las anotaciones actualizadas"""
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def get_annotation_stats(rows: List[Dict]) -> Dict[str, int]:
    """Calcula estadísticas de anotación"""
    stats = {
        'total': len(rows),
        'annotated': 0,
        'relevant': 0,
        'not_relevant': 0,
        'pending': 0
    }
    for row in rows:
        rel = row.get('relevance', '').strip()
        if rel in ('0', '1'):
            stats['annotated'] += 1
            if rel == '1':
                stats['relevant'] += 1
            else:
                stats['not_relevant'] += 1
        else:
            stats['pending'] += 1
    return stats


def print_progress(stats: Dict[str, int]):
    """Imprime barra de progreso"""
    pct = (stats['annotated'] / stats['total']) * 100 if stats['total'] > 0 else 0
    bar_length = 50
    filled = int(bar_length * stats['annotated'] / stats['total'])
    bar = '█' * filled + '░' * (bar_length - filled)
    
    print(f"\n{'='*80}")
    print(f"PROGRESO: [{bar}] {pct:.1f}%")
    print(f"Anotados: {stats['annotated']}/{stats['total']} | "
          f"Relevantes: {stats['relevant']} | "
          f"No relevantes: {stats['not_relevant']} | "
          f"Pendientes: {stats['pending']}")
    print(f"{'='*80}\n")


def annotate_interactive(csv_path: str, start_from: int = 0):
    """Modo interactivo de anotación"""
    rows = load_csv(csv_path)
    fieldnames = list(rows[0].keys()) if rows else []
    
    # Asegurar que existe columna 'relevance'
    if 'relevance' not in fieldnames:
        fieldnames.append('relevance')
        for row in rows:
            row['relevance'] = ''
    
    current_idx = start_from
    history = []  # Para función "back"
    
    print_instructions()
    input("Presiona Enter para comenzar...")
    
    while current_idx < len(rows):
        clear_screen()
        row = rows[current_idx]
        stats = get_annotation_stats(rows)
        print_progress(stats)
        
        # Mostrar información del registro
        query_id = row.get('query_id', 'N/A')
        query = row.get('query', 'N/A')
        doc_id = row.get('doc_id', 'N/A')
        rank = row.get('rank', 'N/A')
        snippet = row.get('snippet', 'N/A')
        current_rel = row.get('relevance', '').strip()
        
        print(f"📋 Query ID: {query_id} | Doc Rank: {rank}/5 | Doc ID: {doc_id}")
        print(f"─" * 80)
        print(f"\n🔍 QUERY:\n{query}\n")
        print(f"─" * 80)
        print(f"\n📄 SNIPPET RECUPERADO:\n{snippet}\n")
        print(f"─" * 80)
        
        if current_rel in ('0', '1'):
            print(f"\n⚠️  Ya anotado como: {'RELEVANTE' if current_rel == '1' else 'NO RELEVANTE'}")
        
        print(f"\n[Registro {current_idx + 1}/{len(rows)}]")
        print("¿Este documento es relevante para clasificar el producto de la query?")
        print("  1=Sí | 0=No | s=Skip | b=Back | q=Quit | ?=Help")
        
        choice = input("\n➤ ").strip().lower()
        
        if choice == '1':
            history.append(current_idx)
            rows[current_idx]['relevance'] = '1'
            current_idx += 1
        elif choice == '0':
            history.append(current_idx)
            rows[current_idx]['relevance'] = '0'
            current_idx += 1
        elif choice == 's':
            history.append(current_idx)
            rows[current_idx]['relevance'] = ''
            current_idx += 1
        elif choice == 'b':
            if history:
                current_idx = history.pop()
            else:
                print("\n⚠️  Ya estás en el primer registro")
                input("Presiona Enter para continuar...")
        elif choice == 'q':
            save_csv(csv_path, rows, fieldnames)
            stats = get_annotation_stats(rows)
            print(f"\n✅ Progreso guardado en: {csv_path}")
            print(f"   Anotados: {stats['annotated']}/{stats['total']} ({stats['annotated']/stats['total']*100:.1f}%)")
            print(f"   Puedes continuar más tarde con: --start-from {current_idx}")
            return
        elif choice == '?':
            print_instructions()
            input("Presiona Enter para continuar...")
        else:
            print(f"\n⚠️  Opción inválida: '{choice}'")
            input("Presiona Enter para continuar...")
    
    # Terminó de anotar todo
    save_csv(csv_path, rows, fieldnames)
    stats = get_annotation_stats(rows)
    clear_screen()
    print("\n" + "="*80)
    print("🎉 ¡ANOTACIÓN COMPLETA!")
    print("="*80)
    print(f"\nTotal anotado: {stats['annotated']}/{stats['total']}")
    print(f"  ✓ Relevantes: {stats['relevant']}")
    print(f"  ✗ No relevantes: {stats['not_relevant']}")
    print(f"  ⊘ Pendientes: {stats['pending']}")
    print(f"\n💾 Guardado en: {csv_path}")
    print("="*80 + "\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Herramienta de anotación de relevancia para retrieval')
    parser.add_argument('--csv', required=True, help='Ruta al CSV de evaluación')
    parser.add_argument('--start-from', type=int, default=0, help='Índice para continuar anotación (0-based)')
    args = parser.parse_args()
    
    if not Path(args.csv).exists():
        print(f"❌ Error: No existe el archivo {args.csv}")
        sys.exit(1)
    
    try:
        annotate_interactive(args.csv, args.start_from)
    except KeyboardInterrupt:
        print("\n\n⚠️  Anotación interrumpida. Ejecuta nuevamente para continuar.")
        sys.exit(0)
