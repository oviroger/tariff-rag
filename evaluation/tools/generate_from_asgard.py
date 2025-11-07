#!/usr/bin/env python3
"""
Script para generar queries de evaluación desde el archivo ASGARD.csv.
Extrae descripciones de productos con sus códigos HS correctos.
"""
import csv
import re
import random
import json
from typing import List, Dict
from collections import defaultdict


def extract_hs_code(partida_str: str) -> str:
    """Extraer código HS de la cadena de partida."""
    if not partida_str or partida_str == "":
        return ""
    
    # Formato: "PARTIDA ARANCELARIA: 48193010000"
    match = re.search(r'(\d{11,})', partida_str)
    if match:
        code = match.group(1)
        # Convertir a formato HS6: XXXX.XX
        if len(code) >= 6:
            return f"{code[:4]}.{code[4:6]}"
    return ""


def extract_product_description(params: List[str]) -> str:
    """
    Construir descripción del producto desde los parámetros.
    Extrae información relevante de Param_1 a Param_14.
    """
    parts = []
    
    for param in params:
        if not param or param == "":
            continue
        
        # Limpiar formato "CAMPO: valor"
        if ":" in param:
            _, value = param.split(":", 1)
            value = value.strip()
            
            # Filtrar valores no informativos
            if value.lower() in ["sin referencia", "din referencia", ""]:
                continue
            
            parts.append(value)
        else:
            parts.append(param.strip())
    
    # Construir descripción
    description = " ".join(parts)
    
    # Limpiar espacios múltiples
    description = re.sub(r'\s+', ' ', description).strip()
    
    return description


def is_valid_product_query(query: str, hs_code: str) -> bool:
    """Validar si la query es útil para evaluación."""
    if not query or not hs_code:
        return False
    
    if len(query) < 10 or len(query) > 200:
        return False
    
    # Filtrar queries muy genéricas
    generic_terms = [
        "repuesto", "sin referencia", "para uso en planta",
        "componentes electronicos", "unidades"
    ]
    
    query_lower = query.lower()
    word_count = len([w for w in query_lower.split() if len(w) > 3])
    
    # Si solo tiene términos genéricos, descartar
    if word_count < 2:
        return False
    
    # Verificar que tenga contenido descriptivo
    letters = sum(c.isalpha() for c in query)
    if letters < 15:
        return False
    
    return True


def load_asgard_csv(file_path: str, max_per_hs: int = 3, total_target: int = 100) -> List[Dict]:
    """
    Cargar queries desde ASGARD.csv con balance por capítulo HS.
    
    Args:
        file_path: Ruta al archivo ASGARD.csv
        max_per_hs: Máximo de queries por código HS6
        total_target: Objetivo total de queries
    """
    queries_by_chapter = defaultdict(list)
    total_processed = 0
    
    print(f"📂 Abriendo archivo: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            total_processed += 1
            
            if total_processed % 50000 == 0:
                print(f"   Procesadas {total_processed:,} líneas...")
            
            # Extraer código HS
            partida = row.get('Partida', '')
            hs_code = extract_hs_code(partida)
            
            if not hs_code:
                continue
            
            # Extraer descripción del producto
            params = [
                row.get('Mercancia', ''),
                row.get('Param_1', ''),
                row.get('Param_2', ''),
                row.get('Param_3', ''),
                row.get('Param_4', ''),
                row.get('Param_5', ''),
                row.get('Param_6', ''),
                row.get('Param_7', ''),
                row.get('Param_8', ''),
                row.get('Param_9', ''),
                row.get('Param_11', ''),
                row.get('Param_12', ''),
                row.get('Param_14', ''),
            ]
            
            description = extract_product_description(params)
            
            # Validar query
            if not is_valid_product_query(description, hs_code):
                continue
            
            # Agrupar por capítulo (primeros 2 dígitos del HS)
            chapter = hs_code[:2]
            
            # Limitar queries por código HS específico
            hs_count = sum(1 for q in queries_by_chapter[chapter] if q['hs_code'] == hs_code)
            if hs_count >= max_per_hs:
                continue
            
            query_data = {
                'query': description,
                'hs_code': hs_code,
                'chapter': chapter,
                'source': 'asgard',
                'codigo_producto': row.get('codigoproducto', '')
            }
            
            queries_by_chapter[chapter].append(query_data)
    
    print(f"✓ Procesadas {total_processed:,} líneas totales")
    print(f"✓ Encontrados {len(queries_by_chapter)} capítulos HS diferentes")
    
    # Balancear y seleccionar queries
    all_queries = []
    queries_per_chapter = max(1, total_target // len(queries_by_chapter))
    
    print(f"\n📊 Seleccionando ~{queries_per_chapter} queries por capítulo...")
    
    for chapter in sorted(queries_by_chapter.keys()):
        chapter_queries = queries_by_chapter[chapter]
        
        # Seleccionar aleatoriamente hasta el límite
        selected = random.sample(
            chapter_queries,
            min(queries_per_chapter, len(chapter_queries))
        )
        
        all_queries.extend(selected)
        print(f"   Cap. {chapter}: {len(selected)} queries")
    
    # Si no llegamos al objetivo, agregar más
    if len(all_queries) < total_target:
        remaining = total_target - len(all_queries)
        all_available = [q for chapter_list in queries_by_chapter.values() 
                        for q in chapter_list if q not in all_queries]
        
        if all_available:
            additional = random.sample(all_available, min(remaining, len(all_available)))
            all_queries.extend(additional)
    
    # Mezclar
    random.shuffle(all_queries)
    
    # Limitar al objetivo
    all_queries = all_queries[:total_target]
    
    return all_queries


def save_queries(queries: List[Dict], output_txt: str, output_json: str, output_csv: str):
    """Guardar queries en múltiples formatos."""
    
    # Formato texto (solo queries)
    with open(output_txt, 'w', encoding='utf-8') as f:
        for q in queries:
            f.write(f"{q['query']}\n")
    
    print(f"💾 Guardado texto: {output_txt}")
    
    # Formato JSON (con metadata completa)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Guardado JSON: {output_json}")
    
    # Formato CSV con ground truth
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['query_id', 'query', 'true_hs6', 'chapter', 'codigo_producto'])
        
        for idx, q in enumerate(queries, 1):
            writer.writerow([
                idx,
                q['query'],
                q['hs_code'],
                q['chapter'],
                q['codigo_producto']
            ])
    
    print(f"💾 Guardado CSV con ground truth: {output_csv}")


def print_statistics(queries: List[Dict]):
    """Imprimir estadísticas del dataset."""
    print("\n" + "=" * 70)
    print("📊 ESTADÍSTICAS DEL DATASET GENERADO")
    print("=" * 70)
    
    print(f"\n📈 Total queries: {len(queries)}")
    
    # Por capítulo
    by_chapter = defaultdict(int)
    for q in queries:
        by_chapter[q['chapter']] += 1
    
    print(f"\n📦 Distribución por capítulo HS:")
    for chapter in sorted(by_chapter.keys()):
        count = by_chapter[chapter]
        print(f"   Capítulo {chapter}: {count} queries ({count/len(queries)*100:.1f}%)")
    
    # Longitud promedio
    avg_length = sum(len(q['query']) for q in queries) / len(queries)
    print(f"\n📏 Longitud promedio de query: {avg_length:.1f} caracteres")
    
    # Ejemplos
    print(f"\n💡 Ejemplos de queries generadas:")
    for q in random.sample(queries, min(5, len(queries))):
        print(f"   [{q['hs_code']}] {q['query'][:80]}...")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generar queries de evaluación desde ASGARD.csv con códigos HS"
    )
    parser.add_argument(
        "--input",
        default="D:/MAESTRIA/ASGARD.csv",
        help="Ruta al archivo ASGARD.csv"
    )
    parser.add_argument(
        "--total",
        type=int,
        default=100,
        help="Número total de queries a generar (default: 100)"
    )
    parser.add_argument(
        "--max-per-hs",
        type=int,
        default=3,
        help="Máximo queries por código HS6 (default: 3)"
    )
    parser.add_argument(
        "--output-txt",
        default="evaluation/queries_asgard.txt",
        help="Archivo de salida (texto)"
    )
    parser.add_argument(
        "--output-json",
        default="evaluation/queries_asgard_metadata.json",
        help="Archivo de salida (JSON con metadata)"
    )
    parser.add_argument(
        "--output-csv",
        default="evaluation/queries_asgard_groundtruth.csv",
        help="Archivo CSV con ground truth"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔍 GENERADOR DE QUERIES DESDE ASGARD.CSV")
    print("=" * 70)
    print(f"Archivo entrada: {args.input}")
    print(f"Objetivo queries: {args.total}")
    print(f"Máx. por HS6: {args.max_per_hs}")
    print()
    
    # Cargar queries
    queries = load_asgard_csv(
        args.input,
        max_per_hs=args.max_per_hs,
        total_target=args.total
    )
    
    # Guardar
    save_queries(
        queries,
        args.output_txt,
        args.output_json,
        args.output_csv
    )
    
    # Estadísticas
    print_statistics(queries)
    
    print("\n" + "=" * 70)
    print("✅ GENERACIÓN COMPLETADA")
    print("=" * 70)
    print(f"\n💡 Siguiente paso:")
    print(f"   Usar queries_asgard_groundtruth.csv que YA TIENE los códigos HS correctos")
    print(f"   No necesitas anotar true_hs6 manualmente!")
