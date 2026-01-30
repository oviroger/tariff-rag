#!/usr/bin/env python3
"""
Analizar por qué la ingesta de 2025 no incluye 'microondas'.

Investigaremos:
1. Si el archivo Parte_4 contiene 'microondas' en el JSON original
2. Qué proceso usó 'reingest_2025_with_chapters.py' 
3. Si hay problemas en la transformación de la estructura de datos
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

def check_microondas_in_json(json_file: Path) -> List[Dict[str, Any]]:
    """Busca 'microondas' en el JSON y retorna contexto."""
    results = []
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Función recursiva para buscar en estructuras anidadas
    def search_recursive(obj, path=""):
        nonlocal results
        
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                search_recursive(v, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                search_recursive(item, new_path)
        elif isinstance(obj, str) and 'microondas' in obj.lower():
            results.append({
                'path': path,
                'value': obj[:200],
                'context': str(obj)[:500]
            })
    
    search_recursive(data)
    return results

def analyze_parte4_structure():
    """Analiza la estructura de Parte 4."""
    parte4_path = Path("data/afr_2025_partes_only/Arancel_Boliviano_2025_Parte_4.json")
    
    print("=" * 80)
    print("ANÁLISIS: Estructura de Parte 4 de 2025")
    print("=" * 80)
    
    if not parte4_path.exists():
        print(f"❌ Archivo no existe: {parte4_path}")
        return
    
    print(f"✓ Archivo encontrado: {parte4_path}")
    print(f"  Tamaño: {parte4_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    with open(parte4_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\nEstructura raíz:")
    print(f"  - Tipo: {type(data).__name__}")
    if isinstance(data, dict):
        print(f"  - Keys: {list(data.keys())[:10]}")  # Primeras 10 keys
        for key in list(data.keys())[:3]:
            val = data[key]
            if isinstance(val, list):
                print(f"    - {key}: list[{len(val)}]")
                if len(val) > 0:
                    print(f"      - Primer elemento type: {type(val[0]).__name__}")
            elif isinstance(val, dict):
                print(f"    - {key}: dict con keys {list(val.keys())[:5]}")
            else:
                print(f"    - {key}: {type(val).__name__}")
    
    # Buscar microondas
    print(f"\n{'='*40}")
    print("BÚSQUEDA: 'microondas' en Parte 4")
    print(f"{'='*40}")
    
    results = check_microondas_in_json(parte4_path)
    
    if results:
        print(f"✓ Encontrados {len(results)} contextos con 'microondas':")
        for i, result in enumerate(results[:5]):
            print(f"\n  [{i+1}] Ruta: {result['path']}")
            print(f"      Valor: {result['value']}")
    else:
        print("❌ No se encontró 'microondas' en Parte 4")
        
        # Buscar patrones similares
        print("\nBuscando patrones relacionados...")
        with open(parte4_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar HS codes relacionados con electrodomésticos
        hs_codes_to_check = ['8516', '8450', '8471']
        for hs_code in hs_codes_to_check:
            if hs_code in content:
                print(f"  ✓ Encontrado HS code {hs_code} en el archivo")
                # Contar ocurrencias
                count = content.count(hs_code)
                print(f"    Ocurrencias: {count}")

def compare_2025_vs_2026():
    """Compara estructura de ambas partes."""
    print("\n" + "=" * 80)
    print("COMPARACIÓN: Estructura 2025 Parte 4 vs 2026 Parte 5")
    print("=" * 80)
    
    parte4_path = Path("data/afr_2025_partes_only/Arancel_Boliviano_2025_Parte_4.json")
    parte5_2026_path = Path("data/afr_2026_partes_only/Arancel 2026_5.pdf.json")
    
    for path in [parte4_path, parte5_2026_path]:
        if not path.exists():
            print(f"❌ {path} no existe")
            continue
            
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n{path.name}:")
        if isinstance(data, dict):
            print(f"  - Keys raíz: {list(data.keys())}")
            
            # Analizar estructura de 'analyze_result'
            if 'analyze_result' in data:
                ar = data['analyze_result']
                print(f"  - analyze_result type: {type(ar).__name__}")
                if isinstance(ar, dict):
                    print(f"    - Keys: {list(ar.keys())}")
                    if 'content' in ar:
                        content = ar['content']
                        if isinstance(content, list):
                            print(f"    - content: list[{len(content)}]")
                            if len(content) > 0:
                                print(f"      - Primer elemento: {type(content[0]).__name__}")

if __name__ == "__main__":
    analyze_parte4_structure()
    compare_2025_vs_2026()
    
    print("\n" + "=" * 80)
    print("CONCLUSIÓN")
    print("=" * 80)
    print("""
Si 'microondas' existe en Parte 4:
  → El problema es en el script 'reingest_2025_with_chapters.py'
  → Verificar cómo procesa el JSON y extrae fragmentos
  
Si 'microondas' NO existe en Parte 4:
  → El archivo fue procesado/limpiado antes de guardarse
  → Revisar cómo se descargó/procesó el PDF original
""")
