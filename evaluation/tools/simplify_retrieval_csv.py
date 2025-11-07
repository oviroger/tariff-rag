"""
Genera versión simplificada del CSV de retrieval para anotación manual en Excel.
Incluye solo las columnas necesarias: query_id, query, doc_id, rank, snippet, relevance

Uso:
    python evaluation/tools/simplify_retrieval_csv.py --input eval_retrieval_asgard.csv --output eval_retrieval_simple.csv
"""

import csv
import sys
import argparse
from pathlib import Path


def simplify_csv(input_path: str, output_path: str):
    """Simplifica CSV para anotación manual"""
    
    # Columnas a mantener (en orden)
    keep_cols = ['query_id', 'query', 'doc_id', 'rank', 'snippet', 'relevance']
    
    rows_out = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            simple_row = {col: row.get(col, '') for col in keep_cols}
            # Limpiar snippet (remover saltos de línea para Excel)
            snippet = simple_row.get('snippet', '').replace('\n', ' ').replace('\r', ' ')
            simple_row['snippet'] = ' '.join(snippet.split())  # Normalizar espacios
            rows_out.append(simple_row)
    
    # Guardar versión simplificada
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keep_cols)
        writer.writeheader()
        writer.writerows(rows_out)
    
    print(f"✅ Versión simplificada guardada: {output_path}")
    print(f"   Total de registros: {len(rows_out)}")
    print(f"   Columnas: {', '.join(keep_cols)}")
    print(f"\n💡 Abre este archivo en Excel y llena la columna 'relevance' con 0 o 1")
    print(f"   Luego copia los valores de vuelta a: {input_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='CSV de entrada')
    parser.add_argument('--output', required=True, help='CSV de salida simplificado')
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"❌ Error: No existe {args.input}")
        sys.exit(1)
    
    simplify_csv(args.input, args.output)
