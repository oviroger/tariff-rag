#!/usr/bin/env python3
"""
Script para crear el índice de 2026 en OpenSearch copiando datos de 2025.
Útil para pruebas antes de tener datos reales de 2026.

Uso:
  python scripts/create_2026_index.py
"""
import json
import logging
import sys
from opensearchpy import OpenSearch
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def copy_index_with_year(source_index: str, target_index: str, target_year: int):
    """
    Copia índice de OpenSearch añadiendo metadata de año a cada documento.
    
    Args:
        source_index: Índice origen (ej: tariff_fragments_2025)
        target_index: Índice destino (ej: tariff_fragments_2026)
        target_year: Año para marcar cada documento (ej: 2026)
    """
    settings = get_settings()
    
    client = OpenSearch(
        hosts=[settings.opensearch_host],
        http_auth=None,
        use_ssl=False,
        verify_certs=False,
    )
    
    try:
        # 1. Verificar que el índice fuente existe
        logger.info(f"[1/4] Verificando índice fuente: {source_index}...")
        if not client.indices.exists(index=source_index):
            logger.error(f"✗ Índice fuente no existe: {source_index}")
            return False
        logger.info(f"✓ Índice fuente encontrado")
        
        # 2. Obtener configuración del índice fuente
        logger.info(f"[2/4] Obteniendo configuración...")
        index_info = client.indices.get(index=source_index)
        source_config = index_info[source_index]
        
        # Preparar mappings
        mappings = source_config.get("mappings", {})
        if "properties" not in mappings:
            mappings["properties"] = {}
        
        # Asegurar que existe el campo year
        if "year" not in mappings["properties"]:
            mappings["properties"]["year"] = {
                "type": "integer",
                "index": True
            }
        
        # 3. Crear nuevo índice
        logger.info(f"[3/4] Creando índice destino: {target_index}...")
        if client.indices.exists(index=target_index):
            logger.warning(f"⚠ Índice destino ya existe. Eliminando...")
            client.indices.delete(index=target_index)
        
        # Filtrar settings que no deben copiarse (son de sistema)
        source_settings = source_config.get("settings", {})
        filtered_settings = {}
        if "index" in source_settings:
            # Solo copiar settings que sabemos que funcionan
            safe_settings = ["number_of_shards", "number_of_replicas", "codec"]
            filtered_settings["index"] = {
                k: v for k, v in source_settings["index"].items()
                if k in safe_settings
            }
        
        client.indices.create(
            index=target_index,
            body={
                "settings": filtered_settings,
                "mappings": mappings
            }
        )
        logger.info(f"✓ Índice {target_index} creado")
        
        # 4. Copiar documentos usando bulk API
        logger.info(f"[4/4] Copiando documentos de {source_index} a {target_index} usando bulk API...")
        
        from opensearchpy.helpers import bulk, BulkIndexError
        
        # Usar scroll para procesar en lotes
        batch_size = 1000
        scroll = "5m"
        
        response = client.search(
            index=source_index,
            scroll=scroll,
            size=batch_size,
            body={"query": {"match_all": {}}}
        )
        
        scroll_id = response.get("_scroll_id")
        total_copied = 0
        errors = 0
        
        while True:
            hits = response.get("hits", {}).get("hits", [])
            if not hits:
                break
            
            # Preparar batch para bulk API
            bulk_actions = []
            for doc in hits:
                source_data = doc.get("_source", {})
                doc_id = doc.get("_id")
                
                # Añadir año al documento
                source_data["year"] = target_year
                
                bulk_actions.append({
                    '_op_type': 'index',
                    '_index': target_index,
                    '_id': doc_id,
                    '_source': source_data
                })
            
            # Ejecutar bulk
            try:
                success, failed = bulk(client, bulk_actions, raise_on_error=False, stats_only=False)
                total_copied += success
                if failed:
                    errors += len(failed)
                    logger.warning(f"  {len(failed)} documentos fallaron en este batch")
            except BulkIndexError as e:
                errors += len(e.errors)
                logger.error(f"Error en bulk: {len(e.errors)} documentos fallaron")
            except Exception as e:
                logger.error(f"Error ejecutando bulk: {e}")
                errors += len(bulk_actions)
            
            # Mostrar progreso
            logger.info(f"  Copiados: {total_copied}...")
            
            # Siguiente página con manejo de errores
            try:
                response = client.scroll(scroll_id=scroll_id, scroll=scroll)
                scroll_id = response.get("_scroll_id")
            except Exception as e:
                logger.error(f"Error en scroll: {e}")
                logger.warning("Deteniendo copia debido a error de scroll")
                break
        
        # Limpiar scroll
        try:
            client.clear_scroll(scroll_id=scroll_id)
        except:
            pass
        
        # Resumen
        logger.info(f"\n=== COPIA COMPLETADA ===")
        logger.info(f"✓ Documentos copiados: {total_copied}")
        logger.info(f"✗ Errores: {errors}")
        logger.info(f"Índice origen: {source_index}")
        logger.info(f"Índice destino: {target_index}")
        logger.info(f"Año asignado: {target_year}")
        
        # Verificar conteos
        count_source = client.count(index=source_index).get("count", 0)
        count_target = client.count(index=target_index).get("count", 0)
        logger.info(f"\nVerificación:")
        logger.info(f"  Documentos en {source_index}: {count_source}")
        logger.info(f"  Documentos en {target_index}: {count_target}")
        
        if count_source == count_target:
            logger.info(f"✓ Copia verificada exitosamente")
            return True
        else:
            logger.warning(f"⚠ Advertencia: Las cantidades no coinciden")
            return False
        
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("===== Copiando índice con metadata de año =====\n")
    
    # Parámetros
    source = "tariff_fragments"
    target = "tariff_fragments_2026"
    year = 2026
    
    logger.info(f"Origen: {source}")
    logger.info(f"Destino: {target}")
    logger.info(f"Año: {year}\n")
    
    success = copy_index_with_year(source, target, year)
    sys.exit(0 if success else 1)

