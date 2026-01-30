#!/usr/bin/env python3
"""
Script para generar queries de evaluación automáticamente desde el corpus.
Extrae descripciones de productos y códigos HS de OpenSearch y MySQL.
"""
import argparse
import csv
import json
import random
import re
from typing import List, Dict, Tuple
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos de la app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from opensearchpy import OpenSearch
    from opensearchpy.exceptions import ConnectionError as OSConnectionError
except ImportError:
    print("❌ Error: opensearch-py no está instalado")
    print("Instale con: pip install opensearch-py")
    sys.exit(1)

try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    print("⚠️ Warning: mysql-connector-python no instalado. No se extraerán queries de MySQL.")
    HAS_MYSQL = False


def connect_opensearch(host: str) -> OpenSearch:
    """Conectar a OpenSearch."""
    try:
        client = OpenSearch(
            hosts=[host],
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
            timeout=30
        )
        # Test connection
        client.info()
        return client
    except Exception as e:
        print(f"❌ Error conectando a OpenSearch: {e}")
        sys.exit(1)


def extract_hs_codes_from_text(text: str) -> List[str]:
    """Extraer códigos HS del texto (formato: XXXX.XX o similares)."""
    # Patrón para códigos HS de 4-6 dígitos con punto opcional
    pattern = r'\b\d{2,4}(?:\.\d{2})?\b'
    codes = re.findall(pattern, text)
    return list(set(codes))  # Únicos


def extract_product_descriptions(text: str, max_words: int = 15) -> List[str]:
    """Extraer descripciones de productos del texto."""
    descriptions = []
    
    # Patrones comunes en nomenclatura HS
    product_keywords = [
        'animales', 'carne', 'pescado', 'lácteos', 'frutas', 'legumbres', 'café', 'té',
        'cereales', 'productos', 'grasas', 'aceites', 'preparaciones', 'bebidas',
        'tabaco', 'materias', 'plástico', 'caucho', 'pieles', 'cuero', 'madera',
        'papel', 'cartón', 'textiles', 'calzado', 'piedra', 'cemento', 'vidrio',
        'perlas', 'metales', 'hierro', 'acero', 'cobre', 'aluminio', 'plomo',
        'herramientas', 'máquinas', 'aparatos', 'vehículos', 'aeronaves', 'barcos',
        'instrumentos', 'armas', 'muebles', 'juguetes', 'manufacturas'
    ]
    
    # Buscar líneas que parecen descripciones de productos
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        line_lower = line.lower()
        
        # Filtrar líneas que parecen descripciones
        if len(line) > 15 and len(line) < 250:
            words = line.split()
            if 2 <= len(words) <= max_words:
                # Verificar que contenga palabras clave de productos
                has_keyword = any(keyword in line_lower for keyword in product_keywords)
                
                # Verificar que contenga más letras que números
                letters = sum(c.isalpha() for c in line)
                digits = sum(c.isdigit() for c in line)
                
                if (has_keyword or letters > digits * 2) and letters > 20:
                    # Limpiar caracteres especiales al inicio/final
                    line_clean = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', line)
                    if len(line_clean) > 15:
                        descriptions.append(line_clean)
    
    return descriptions


def sample_opensearch_queries(
    os_client: OpenSearch,
    index: str,
    num_samples: int = 100,
    max_per_category: int = 10
) -> List[Dict]:
    """
    Extraer queries de muestra desde OpenSearch.
    Intenta obtener diversidad de categorías HS.
    """
    queries = []
    
    print(f"📥 Extrayendo {num_samples} documentos de OpenSearch...")
    
    try:
        # Obtener documentos aleatorios
        response = os_client.search(
            index=index,
            body={
                "size": num_samples,
                "query": {
                    "function_score": {
                        "query": {"match_all": {}},
                        "random_score": {}
                    }
                },
                "_source": ["text", "hs_code", "title", "doc_id"]
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        print(f"✓ Obtenidos {len(hits)} documentos")
        
        # Agrupar por prefijo de código HS (primeros 2 dígitos)
        by_category = {}
        
        for hit in hits:
            source = hit.get("_source", {})
            text = source.get("text", "")
            hs_code = source.get("hs_code", "")
            title = source.get("title", "")
            
            if not text or len(text) < 50:
                continue
            
            # Extraer descripciones del texto
            descriptions = extract_product_descriptions(text)
            
            # Intentar extraer códigos HS del texto
            hs_codes_in_text = extract_hs_codes_from_text(text)
            
            # Determinar categoría (primeros 2 dígitos del código HS)
            category = hs_code[:2] if hs_code and len(hs_code) >= 2 else "00"
            
            if category not in by_category:
                by_category[category] = []
            
            # Agregar descripciones encontradas
            for desc in descriptions[:3]:  # Máximo 3 por documento
                if len(by_category[category]) < max_per_category:
                    query_data = {
                        "query": desc,
                        "hs_code": hs_code or (hs_codes_in_text[0] if hs_codes_in_text else ""),
                        "category": category,
                        "source": "opensearch"
                    }
                    by_category[category].append(query_data)
        
        # Recopilar todas las queries
        for category, category_queries in by_category.items():
            queries.extend(category_queries)
        
        print(f"✓ Extraídas {len(queries)} queries de {len(by_category)} categorías")
        
    except Exception as e:
        print(f"⚠️ Error extrayendo de OpenSearch: {e}")
    
    return queries


def sample_mysql_queries(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    num_samples: int = 50
) -> List[Dict]:
    """
    Extraer queries de muestra desde MySQL.
    Busca tablas con descripciones de productos y códigos HS.
    """
    queries = []
    
    if not HAS_MYSQL:
        return queries
    
    print(f"📥 Extrayendo queries de MySQL...")
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor(dictionary=True)
        
        # Intentar encontrar tablas relevantes
        # Buscar tablas con columnas que contengan 'description', 'hs', 'product', etc.
        cursor.execute("SHOW TABLES")
        tables = [row[f'Tables_in_{database}'] for row in cursor.fetchall()]
        
        for table in tables:
            try:
                # Obtener columnas de la tabla
                cursor.execute(f"DESCRIBE {table}")
                columns = [row['Field'] for row in cursor.fetchall()]
                
                # Buscar columnas relevantes
                desc_col = next((c for c in columns if 'descripcion' in c.lower() or 'description' in c.lower() or 'producto' in c.lower() or 'product' in c.lower()), None)
                hs_col = next((c for c in columns if 'hs' in c.lower() or 'codigo' in c.lower() or 'code' in c.lower()), None)
                
                if desc_col:
                    # Construir query SQL
                    select_cols = [desc_col]
                    if hs_col:
                        select_cols.append(hs_col)
                    
                    query_sql = f"SELECT {', '.join(select_cols)} FROM {table} ORDER BY RAND() LIMIT {num_samples}"
                    cursor.execute(query_sql)
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        desc = row.get(desc_col, "")
                        hs_code = row.get(hs_col, "") if hs_col else ""
                        
                        if desc and len(desc) > 10:
                            # Limpiar descripción
                            desc_clean = desc.strip()
                            if len(desc_clean) > 200:
                                desc_clean = desc_clean[:200] + "..."
                            
                            query_data = {
                                "query": desc_clean,
                                "hs_code": str(hs_code) if hs_code else "",
                                "category": str(hs_code)[:2] if hs_code else "00",
                                "source": f"mysql:{table}"
                            }
                            queries.append(query_data)
                    
                    print(f"  ✓ {len(rows)} queries de tabla '{table}'")
            
            except Exception as e:
                # Tabla puede no ser accesible o tener problemas
                continue
        
        cursor.close()
        conn.close()
        
        print(f"✓ Extraídas {len(queries)} queries de MySQL")
    
    except Exception as e:
        print(f"⚠️ Error conectando a MySQL: {e}")
    
    return queries


def generate_synthetic_queries(base_queries: List[Dict], num_synthetic: int = 20) -> List[Dict]:
    """
    Generar queries sintéticas basadas en las queries existentes.
    Crea variaciones añadiendo atributos comunes.
    """
    synthetic = []
    
    # Queries predefinidas comunes (casos típicos de clasificación arancelaria)
    predefined_queries = [
        # Electrónica (Capítulo 85)
        "Smartphone con pantalla OLED",
        "Laptop HP 15 pulgadas",
        "Auriculares inalámbricos Bluetooth",
        "Tablet Android 10 pulgadas",
        "Cargador USB-C 65W",
        "Cable HDMI 2 metros",
        "Mouse inalámbrico",
        "Teclado mecánico RGB",
        "Monitor LED 27 pulgadas",
        "Cámara web Full HD",
        
        # Alimentos (Capítulos 01-24)
        "Bananas frescas",
        "Manzanas rojas importadas",
        "Café en grano tostado",
        "Arroz blanco largo",
        "Aceite de oliva virgen extra",
        "Chocolate con leche",
        "Queso parmesano",
        "Vino tinto reserva",
        "Cerveza artesanal",
        "Té verde en bolsitas",
        
        # Textiles (Capítulos 50-63)
        "Camiseta de algodón",
        "Pantalones vaqueros",
        "Zapatos deportivos",
        "Bolso de cuero genuino",
        "Chaqueta impermeable",
        "Toallas de baño",
        "Sábanas de algodón",
        
        # Vehículos (Capítulo 87)
        "Neumáticos radiales 205/55R16",
        "Llantas de aleación 17 pulgadas",
        "Batería de auto 12V",
        "Filtro de aceite automotriz",
        "Parabrisas delantero",
        
        # Maquinaria (Capítulo 84)
        "Bomba de agua centrífuga",
        "Compresor de aire industrial",
        "Taladro eléctrico 500W",
        "Sierra circular",
        "Generador eléctrico 5KW",
        
        # Productos químicos (Capítulos 28-38)
        "Detergente líquido",
        "Champú anticaspa",
        "Pintura acrílica blanca",
        "Fertilizante NPK",
        "Insecticida en aerosol",
        
        # Juguetes y deportes (Capítulos 95-96)
        "Pelota de fútbol oficial",
        "Bicicleta de montaña",
        "Muñeca de plástico",
        "Raqueta de tenis",
        "Patineta eléctrica",
        
        # Muebles (Capítulo 94)
        "Silla de oficina ergonómica",
        "Mesa de comedor de madera",
        "Colchón queen size",
        "Estantería metálica",
        
        # Plásticos (Capítulo 39)
        "Tubos PVC 2 pulgadas",
        "Contenedores plásticos",
        "Bolsas plásticas biodegradables",
        
        # Metales (Capítulos 72-83)
        "Alambre de acero galvanizado",
        "Tornillos de acero inoxidable",
        "Láminas de aluminio",
        
        # Instrumentos (Capítulo 90)
        "Termómetro digital",
        "Gafas de sol polarizadas",
        "Tensiómetro digital",
        
        # Libros y papel (Capítulo 48-49)
        "Cuadernos universitarios",
        "Libro de texto",
        "Papel bond carta",
    ]
    
    # Atributos comunes para añadir variación
    materials = ["de acero", "de plástico", "de aluminio", "de madera", "de vidrio", "de algodón", "de cuero"]
    sizes = ["grande", "pequeño", "mediano", "extra grande"]
    colors = ["rojo", "azul", "negro", "blanco", "verde", "amarillo"]
    conditions = ["nuevo", "usado"]
    origins = ["importado de China", "importado de USA", "nacional"]
    brands = ["marca Samsung", "marca Apple", "marca Sony", "marca LG"]
    
    print(f"🔨 Generando {num_synthetic} queries sintéticas...")
    
    # Primero agregar queries predefinidas
    num_predefined = min(len(predefined_queries), num_synthetic // 2)
    selected_predefined = random.sample(predefined_queries, num_predefined)
    
    for query_text in selected_predefined:
        synthetic.append({
            "query": query_text,
            "hs_code": "",
            "category": "00",
            "source": "predefined"
        })
    
    # Luego generar variaciones de queries base
    remaining = num_synthetic - len(synthetic)
    
    for _ in range(remaining):
        if not base_queries and not synthetic:
            # Si no hay queries base, usar predefinidas
            query_text = random.choice(predefined_queries)
            base_hs = ""
            base_cat = "00"
            base_source = "predefined"
        elif base_queries:
            base = random.choice(base_queries)
            query_text = base["query"]
            base_hs = base.get("hs_code", "")
            base_cat = base.get("category", "00")
            base_source = base.get("source", "unknown")
        else:
            base = random.choice(synthetic)
            query_text = base["query"]
            base_hs = base.get("hs_code", "")
            base_cat = base.get("category", "00")
            base_source = base.get("source", "unknown")
        
        # Añadir variación aleatoria
        variation_type = random.choice(["material", "size", "color", "condition", "origin", "brand", "none"])
        
        if variation_type == "material" and len(query_text.split()) < 8:
            new_query = f"{query_text} {random.choice(materials)}"
        elif variation_type == "size" and len(query_text.split()) < 8:
            new_query = f"{query_text} {random.choice(sizes)}"
        elif variation_type == "color" and len(query_text.split()) < 8:
            new_query = f"{query_text} {random.choice(colors)}"
        elif variation_type == "condition" and len(query_text.split()) < 8:
            new_query = f"{query_text} {random.choice(conditions)}"
        elif variation_type == "origin" and len(query_text.split()) < 8:
            new_query = f"{query_text} {random.choice(origins)}"
        elif variation_type == "brand" and len(query_text.split()) < 8:
            new_query = f"{query_text} {random.choice(brands)}"
        else:
            new_query = query_text
        
        synthetic.append({
            "query": new_query,
            "hs_code": base_hs,
            "category": base_cat,
            "source": f"synthetic:{base_source}"
        })
    
    print(f"✓ Generadas {len(synthetic)} queries sintéticas")
    return synthetic


def clean_and_deduplicate(queries: List[Dict]) -> List[Dict]:
    """Limpiar y eliminar duplicados."""
    seen = set()
    cleaned = []
    
    for q in queries:
        query_text = q["query"].strip().lower()
        
        # Filtrar queries muy cortas o muy largas
        if len(query_text) < 10 or len(query_text) > 300:
            continue
        
        # Eliminar duplicados (case-insensitive)
        if query_text not in seen:
            seen.add(query_text)
            cleaned.append(q)
    
    return cleaned


def save_queries(queries: List[Dict], output_file: str):
    """Guardar queries en archivo de texto."""
    with open(output_file, 'w', encoding='utf-8') as f:
        for q in queries:
            # Formato: query|hs_code|category|source
            f.write(f"{q['query']}\n")
    
    print(f"💾 Guardadas {len(queries)} queries en: {output_file}")


def save_queries_with_metadata(queries: List[Dict], output_file: str):
    """Guardar queries con metadata en JSON."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Guardado metadata en: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generar queries de evaluación desde el corpus"
    )
    parser.add_argument(
        "--os-host",
        default="http://localhost:9200",
        help="Host de OpenSearch (default: http://localhost:9200)"
    )
    parser.add_argument(
        "--os-index",
        default="tariff_fragments",
        help="Índice de OpenSearch (default: tariff_fragments)"
    )
    parser.add_argument(
        "--os-samples",
        type=int,
        default=100,
        help="Número de documentos a muestrear de OpenSearch (default: 100)"
    )
    parser.add_argument(
        "--mysql-host",
        default="localhost",
        help="Host de MySQL (default: localhost)"
    )
    parser.add_argument(
        "--mysql-port",
        type=int,
        default=3306,
        help="Puerto de MySQL (default: 3306)"
    )
    parser.add_argument(
        "--mysql-db",
        default="corpusdb",
        help="Base de datos MySQL (default: corpusdb)"
    )
    parser.add_argument(
        "--mysql-user",
        default="appuser",
        help="Usuario MySQL (default: appuser)"
    )
    parser.add_argument(
        "--mysql-password",
        default="apppass",
        help="Password MySQL (default: apppass)"
    )
    parser.add_argument(
        "--mysql-samples",
        type=int,
        default=50,
        help="Número de registros a muestrear de MySQL (default: 50)"
    )
    parser.add_argument(
        "--use-mysql",
        action="store_true",
        help="Habilitar extracción desde MySQL"
    )
    parser.add_argument(
        "--synthetic",
        type=int,
        default=20,
        help="Número de queries sintéticas a generar (default: 20)"
    )
    parser.add_argument(
        "--target-total",
        type=int,
        default=100,
        help="Número total de queries objetivo (default: 100)"
    )
    parser.add_argument(
        "--output",
        default="evaluation/test_queries.txt",
        help="Archivo de salida (default: evaluation/test_queries.txt)"
    )
    parser.add_argument(
        "--metadata",
        default="evaluation/test_queries_metadata.json",
        help="Archivo de metadata (default: evaluation/test_queries_metadata.json)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔍 GENERADOR DE QUERIES DE EVALUACIÓN")
    print("=" * 60)
    
    all_queries = []
    
    # 1. Extraer de OpenSearch
    os_client = connect_opensearch(args.os_host)
    os_queries = sample_opensearch_queries(
        os_client,
        args.os_index,
        num_samples=args.os_samples
    )
    all_queries.extend(os_queries)
    
    # 2. Extraer de MySQL (opcional)
    if args.use_mysql:
        mysql_queries = sample_mysql_queries(
            args.mysql_host,
            args.mysql_port,
            args.mysql_db,
            args.mysql_user,
            args.mysql_password,
            num_samples=args.mysql_samples
        )
        all_queries.extend(mysql_queries)
    
    # 3. Limpiar y deduplicar
    all_queries = clean_and_deduplicate(all_queries)
    
    # 4. Generar sintéticas si no llegamos al objetivo
    if len(all_queries) < args.target_total and args.synthetic > 0:
        needed = min(args.synthetic, args.target_total - len(all_queries))
        synthetic_queries = generate_synthetic_queries(all_queries, num_synthetic=needed)
        all_queries.extend(synthetic_queries)
    
    # 5. Limitar al objetivo y mezclar
    if len(all_queries) > args.target_total:
        all_queries = random.sample(all_queries, args.target_total)
    
    random.shuffle(all_queries)
    
    # 6. Guardar
    save_queries(all_queries, args.output)
    save_queries_with_metadata(all_queries, args.metadata)
    
    print("\n" + "=" * 60)
    print("✅ GENERACIÓN COMPLETADA")
    print("=" * 60)
    print(f"📊 Total de queries: {len(all_queries)}")
    
    # Estadísticas por fuente
    by_source = {}
    for q in all_queries:
        source = q.get("source", "unknown").split(":")[0]
        by_source[source] = by_source.get(source, 0) + 1
    
    print("\n📈 Distribución por fuente:")
    for source, count in sorted(by_source.items()):
        print(f"  - {source}: {count} queries")
    
    print(f"\n💡 Siguiente paso:")
    print(f"   1. Revisar queries en: {args.output}")
    print(f"   2. Generar CSVs de evaluación:")
    print(f"      python evaluation/tools/generate_eval_clasificador.py --queries-file {args.output} --top-n 3")
    print(f"      python evaluation/tools/generate_eval_retrieval.py --queries-file {args.output} --top-k 5")


if __name__ == "__main__":
    main()
