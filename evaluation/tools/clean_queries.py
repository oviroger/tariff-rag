#!/usr/bin/env python3
"""
Script para limpiar y filtrar queries de evaluación.
Elimina queries que no son descripciones de productos válidas.
"""
import re

def is_valid_product_query(query: str) -> bool:
    """Determinar si una query es una descripción válida de producto."""
    query_lower = query.lower().strip()
    
    # Filtrar queries muy cortas o muy largas
    if len(query) < 10 or len(query) > 150:
        return False
    
    # Filtrar queries que contienen texto de formularios/documentos
    invalid_patterns = [
        r'cuantitativo',
        r'cualitativo',
        r'no aplica',
        r'consignar',
        r'reglamento',
        r'd\.v\.a',
        r'características:.*\|',
        r'tipo:.*ejemplos',
        r'parches para reparar',
        r'p-p-a.*pícea',
        r'alcohol furfurílico'
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, query_lower):
            return False
    
    # Verificar que tiene contenido significativo
    words = query.split()
    if len(words) < 2:
        return False
    
    # Verificar que tiene más letras que números/símbolos
    letters = sum(c.isalpha() for c in query)
    other = len(query) - letters - query.count(' ')
    
    if letters < other:
        return False
    
    return True


def clean_queries_file(input_file: str, output_file: str):
    """Limpiar archivo de queries."""
    with open(input_file, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip()]
    
    # Filtrar queries válidas
    valid_queries = [q for q in queries if is_valid_product_query(q)]
    
    # Eliminar duplicados
    seen = set()
    unique_queries = []
    for q in valid_queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique_queries.append(q)
    
    # Guardar
    with open(output_file, 'w', encoding='utf-8') as f:
        for q in unique_queries:
            f.write(f"{q}\n")
    
    print(f"📊 Queries originales: {len(queries)}")
    print(f"✅ Queries válidas: {len(valid_queries)}")
    print(f"🔍 Queries únicas: {len(unique_queries)}")
    print(f"❌ Eliminadas: {len(queries) - len(unique_queries)}")
    print(f"\n💾 Guardado en: {output_file}")


if __name__ == "__main__":
    clean_queries_file(
        "evaluation/test_queries.txt",
        "evaluation/test_queries_cleaned.txt"
    )
