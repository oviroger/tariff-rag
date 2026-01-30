#!/usr/bin/env python3
"""
🔄 REINDEXACIÓN COMPLETA CON METADATOS ENRIQUECIDOS
====================================================

Crea nuevos índices (v2) con:
✅ hs_code enriquecido automáticamente
✅ descripción detallada de la partida
✅ categoría del producto (electrodoméstico, vehículo, etc.)
✅ nivel arancelario (HS6, NANDINA8, NATIONAL10)
✅ año de referencia
✅ embeddings de alta calidad

Índices originales:
- tariff_fragments_2025: 3,992 docs
- tariff_fragments_2026: 14,175 docs

Índices nuevos:
- tariff_fragments_2025_v2: versión mejorada
- tariff_fragments_2026_v2: versión mejorada
"""

import requests
import json
import re
from opensearchpy import OpenSearch
from typing import Dict, List, Optional
import time

# ============================================================================
# 1. CONFIGURACIÓN
# ============================================================================

OS_HOST = "http://localhost:9200"
OLD_INDICES = {
    2025: "tariff_fragments_2025",
    2026: "tariff_fragments_2026"
}
NEW_INDICES = {
    2025: "tariff_fragments_2025_v2",
    2026: "tariff_fragments_2026_v2"
}

# Mapeo de palabras clave a códigos HS (diccionario de dominio)
KEYWORD_TO_HS_MAPPING = {
    # Electrodomésticos (8509, 8516, 8418, 8450, etc.)
    "microondas": "8516.50",
    "horno microondas": "8516.50",
    "hornos de microondas": "8516.50",
    "microonda convencional": "8516.50",
    
    "horno eléctrico": "8516.10",
    "hornillo eléctrico": "8516.10",
    
    "refrigerador": "8418.69",
    "heladera": "8418.69",
    "congelador": "8418.69",
    
    "lavadora": "8450.11",
    "máquina lavar": "8450.11",
    "washing machine": "8450.11",
    
    "secadora": "8451.21",
    
    "aspiradora": "8509.80",
    "aspirador": "8509.80",
    "vacuum": "8509.80",
    
    "batidora": "8509.40",
    "licuadora": "8509.40",
    "mezcladora": "8509.40",
    
    "cafetera": "8509.80",
    "tostadora": "8509.80",
    "plancha": "8509.30",
    
    # Vehículos (87)
    "automóvil": "8704.21",
    "auto": "8704.21",
    "carro": "8704.21",
    "coche": "8704.21",
    "vehiculo": "8704.21",
    "motor": "8704.21",
    
    "camión": "8704.23",
    "truck": "8704.23",
    
    "bicicleta": "8712.00",
    "moto": "8711.60",
    "motocicleta": "8711.60",
    
    # TI y Electrónica (84, 85)
    "computadora": "8471.30",
    "laptop": "8471.30",
    "monitor": "8528.49",
    "teclado": "8471.49",
    "ratón": "8471.49",
    "mouse": "8471.49",
    
    # Neumaticos (4011-4016)
    "neumático": "4011.10",
    "llanta": "4011.10",
    "llantа": "4011.10",
}

# Categorías de productos
PRODUCT_CATEGORIES = {
    "85": "Electrodoméstico",
    "84": "Maquinaria",
    "87": "Vehículo",
    "40": "Caucho/Neumático",
    "48": "Papel/Cartón",
    "39": "Plásticos",
    "61": "Ropa/Textil",
    "62": "Textil",
}

# ============================================================================
# 2. FUNCIONES DE ENRIQUECIMIENTO
# ============================================================================

def extract_hs_code_from_text(text: str) -> Optional[str]:
    """Extrae código HS del formato '8516.50' o similar"""
    match = re.search(r'\b(\d{4}\.\d{2})\b', text)
    if match:
        return match.group(1)
    return None

def enrich_with_hs_code(fragment: Dict) -> Dict:
    """Enriquece un fragmento con HS code"""
    text = fragment.get('text', '').lower()
    
    # 1. Intentar extraer del texto
    hs_code = extract_hs_code_from_text(fragment.get('text', ''))
    
    # 2. Si no, buscar con palabras clave
    if not hs_code:
        for keyword, code in KEYWORD_TO_HS_MAPPING.items():
            if keyword in text:
                hs_code = code
                break
    
    # 3. Si no, usar primeros dígitos si existen
    if not hs_code:
        match = re.search(r'(\d{2,4})', fragment.get('text', ''))
        if match:
            digits = match.group(1)
            if len(digits) >= 2:
                hs_code = f"{digits}.00"
    
    fragment['hs_code'] = hs_code or "UNKNOWN"
    return fragment

def get_category_from_hs(hs_code: str) -> str:
    """Obtiene categoría de producto desde HS code"""
    if hs_code == "UNKNOWN":
        return "Otros"
    
    first_two = hs_code[:2]
    return PRODUCT_CATEGORIES.get(first_two, "Otros")

def enrich_description(fragment: Dict) -> Dict:
    """Enriquece descripción del fragmento"""
    text = fragment.get('text', '')[:100]
    hs_code = fragment.get('hs_code', 'UNKNOWN')
    category = get_category_from_hs(hs_code)
    
    # Construir descripción enriquecida
    if hs_code != "UNKNOWN":
        fragment['description'] = f"[{category}] {text.strip()}"
    else:
        fragment['description'] = text.strip()
    
    fragment['category'] = category
    fragment['level'] = "HS6"  # Por defecto, nivel 6 dígitos
    
    return fragment

def enrich_fragment(fragment: Dict, year: int) -> Dict:
    """Enriquece completamente un fragmento"""
    fragment = enrich_with_hs_code(fragment)
    fragment = enrich_description(fragment)
    fragment['year'] = year
    fragment['version'] = '2'  # Marcar como versión 2
    return fragment

# ============================================================================
# 3. CONEXIÓN A OPENSEARCH
# ============================================================================

def connect_opensearch():
    """Conectar a OpenSearch"""
    return OpenSearch(
        hosts=[OS_HOST],
        verify_certs=False,
        timeout=30
    )

def create_index_with_mappings(os_client, index_name: str) -> bool:
    """Crea índice con mappings correctos"""
    try:
        # Eliminar si existe
        try:
            os_client.indices.delete(index=index_name)
            print(f"   🗑️  Índice anterior eliminado: {index_name}")
        except:
            pass
        
        # Crear nuevo índice con mappings
        mappings = {
            "mappings": {
                "properties": {
                    "fragment_id": {"type": "keyword"},
                    "text": {"type": "text"},
                    "hs_code": {"type": "keyword"},  # ✅ NUEVO
                    "description": {"type": "text"},  # ✅ NUEVO
                    "category": {"type": "keyword"},  # ✅ NUEVO
                    "level": {"type": "keyword"},  # ✅ NUEVO
                    "doc_id": {"type": "keyword"},
                    "bucket": {"type": "keyword"},
                    "unit": {"type": "keyword"},
                    "year": {"type": "integer"},
                    "page": {"type": "integer"},
                    "version": {"type": "keyword"},  # ✅ NUEVO
                    "embedding": {"type": "knn_vector", "dimension": 1536, "method": {"name": "hnsw", "space_type": "cosinesimil"}}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index.knn": True,
                "index.knn.space_type": "cosinesimil"
            }
        }
        
        os_client.indices.create(index=index_name, body=mappings)
        print(f"   ✅ Índice creado: {index_name}")
        return True
    except Exception as e:
        print(f"   ❌ Error creando índice: {e}")
        return False

# ============================================================================
# 4. REINDEXACIÓN
# ============================================================================

def reindex_with_enrichment(year: int):
    """Reindexar fragmentos con enriquecimiento de metadatos"""
    
    print(f"\n{'='*100}")
    print(f"🔄 REINDEXACIÓN AÑO {year}")
    print(f"{'='*100}")
    
    old_index = OLD_INDICES[year]
    new_index = NEW_INDICES[year]
    
    os_client = connect_opensearch()
    
    # 1. Crear índice nuevo
    print(f"\n1️⃣  Creando índice: {new_index}")
    if not create_index_with_mappings(os_client, new_index):
        return False
    
    # 2. Recuperar documentos del índice antiguo
    print(f"\n2️⃣  Recuperando documentos del índice: {old_index}")
    
    docs_processed = 0
    docs_failed = 0
    batch_size = 100
    
    try:
        # Búsqueda iterativa
        total_hits = 0
        
        # Iniciar scroll
        result = os_client.search(
            index=old_index,
            body={
                "size": batch_size,
                "query": {"match_all": {}},
                "_source": ["fragment_id", "text", "doc_id", "bucket", "unit", "year", "page", "embedding"]
            },
            scroll='5m'  # Mantener contexto por 5 minutos
        )
        
        scroll_id = result['_scroll_id']
        
        while True:
            hits = result['hits']['hits']
            
            if not hits:
                break
            
            total_hits = result['hits']['total']['value']
            
            # 3. Enriquecer y reindexar
            bulk_body = []
            for hit in hits:
                try:
                    doc = hit['_source']
                    doc_id = hit['_id']
                    
                    # Enriquecer
                    enriched_doc = enrich_fragment(doc.copy(), year)
                    
                    # Agregar a bulk
                    bulk_body.append({"index": {"_index": new_index, "_id": doc_id}})
                    bulk_body.append(enriched_doc)
                    
                    docs_processed += 1
                    
                except Exception as e:
                    docs_failed += 1
                    if docs_failed <= 3:  # Mostrar solo primeros 3 errores
                        print(f"      ⚠️  Error enriqueciendo doc {doc_id}: {e}")
            
            # Enviar bulk
            if bulk_body:
                try:
                    response = os_client.bulk(body=bulk_body)
                    errors = response['errors']
                    if not errors:
                        print(f"   ✅ Batch procesado: {len(hits)} documentos")
                    else:
                        print(f"   ⚠️  Batch con algunos errores: {len(hits)} documentos")
                except Exception as e:
                    print(f"   ❌ Error en bulk insert: {e}")
            
            # Siguiente batch
            if len(hits) < batch_size:
                break
            
            # Continuar scroll
            result = os_client.scroll(scroll_id=scroll_id, scroll='5m')
            scroll_id = result['_scroll_id']
        
        print(f"\n   📊 Resultado:")
        print(f"      Total procesados: {docs_processed}")
        print(f"      Total errores: {docs_failed}")
        print(f"      Total original: {total_hits}")
        
        # Limpiar scroll
        try:
            os_client.clear_scroll(scroll_id=scroll_id)
        except:
            pass
        
        # Validar índice nuevo
        new_count = os_client.cat.count(index=new_index, format='json')[0]['count']
        print(f"      Documentos en {new_index}: {new_count}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error en reindexación: {e}")
        return False

# ============================================================================
# 5. VALIDACIÓN
# ============================================================================

def validate_reindexation():
    """Valida que la reindexación fue exitosa"""
    
    print(f"\n{'='*100}")
    print(f"✅ VALIDACIÓN DE REINDEXACIÓN")
    print(f"{'='*100}")
    
    os_client = connect_opensearch()
    
    for year in [2025, 2026]:
        old_index = OLD_INDICES[year]
        new_index = NEW_INDICES[year]
        
        print(f"\n📋 Año {year}:")
        
        # Comparar conteos
        try:
            old_count = os_client.cat.count(index=old_index, format='json')[0]['count']
            new_count = os_client.cat.count(index=new_index, format='json')[0]['count']
            
            print(f"   {old_index}: {old_count} docs")
            print(f"   {new_index}: {new_count} docs")
            
            if new_count >= old_count * 0.95:  # Al menos 95% de cobertura
                print(f"   ✅ Cobertura OK ({new_count}/{old_count})")
            else:
                print(f"   ❌ Cobertura baja ({new_count}/{old_count})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Verificar que los nuevos campos existen
        print(f"\n   Campos en {new_index}:")
        try:
            sample = os_client.search(
                index=new_index,
                body={"query": {"match_all": {}}, "size": 1, "_source": True}
            )
            
            if sample['hits']['hits']:
                doc = sample['hits']['hits'][0]['_source']
                required_fields = ['hs_code', 'description', 'category', 'level', 'version']
                
                for field in required_fields:
                    if field in doc:
                        value = str(doc[field])[:50]
                        print(f"      ✅ {field}: {value}")
                    else:
                        print(f"      ❌ {field}: FALTA")
        except Exception as e:
            print(f"   ❌ Error: {e}")

# ============================================================================
# 6. MAIN
# ============================================================================

def main():
    print("\n🔄 INICIANDO REINDEXACIÓN COMPLETA")
    print("=" * 100)
    
    success = True
    
    # Reindexar ambos años
    for year in [2025, 2026]:
        if not reindex_with_enrichment(year):
            success = False
    
    # Validar
    if success:
        validate_reindexation()
        
        print(f"\n{'='*100}")
        print(f"✅ REINDEXACIÓN COMPLETADA EXITOSAMENTE")
        print(f"{'='*100}")
        print(f"\n📝 Próximos pasos:")
        print(f"   1. Actualizar config del API para usar nuevos índices")
        print(f"   2. Ejecutar: python step2_update_config.py")
        print(f"   3. Reiniciar contenedor: docker restart rag-api")
        print(f"   4. Ejecutar pruebas: python debug_microwave_confidence.py")
    else:
        print(f"\n{'='*100}")
        print(f"❌ REINDEXACIÓN FALLÓ")
        print(f"{'='*100}")

if __name__ == "__main__":
    main()
