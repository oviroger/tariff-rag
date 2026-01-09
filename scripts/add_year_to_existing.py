#!/usr/bin/env python3
"""
Script para añadir el campo 'year: 2025' al índice tariff_fragments existente
usando la API de update_by_query.
"""
import logging
from opensearchpy import OpenSearch
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def add_year_to_index(index_name: str, year: int):
    """Añade el campo year a todos los documentos de un índice usando update_by_query"""
    settings = get_settings()
    
    # Conectar a OpenSearch
    client = OpenSearch(
        hosts=[settings.opensearch_host],
        http_auth=("elastic", "elastic"),
        use_ssl=False,
        verify_certs=False,
        timeout=120
    )
    
    logger.info(f"Añadiendo year={year} a todos los documentos en {index_name}...")
    
    # Usar update_by_query para añadir el campo year (esto puede tardar varios minutos)
    response = client.update_by_query(
        index=index_name,
        body={
            "script": {
                "source": f"ctx._source.year = {year}",
                "lang": "painless"
            },
            "query": {
                "match_all": {}
            }
        },
        wait_for_completion=True,
        conflicts="proceed",
        refresh=True,
        request_timeout=300
    )
    
    logger.info(f"✓ Documentos actualizados: {response.get('updated', 0)}")
    logger.info(f"✓ Operación completada exitosamente")
    
    return response

if __name__ == "__main__":
    logger.info("===== Añadiendo año a índice existente =====\n")
    
    index = "tariff_fragments"
    year = 2025
    
    logger.info(f"Índice: {index}")
    logger.info(f"Año: {year}\n")
    
    try:
        result = add_year_to_index(index, year)
        logger.info("\n✓ Script completado exitosamente")
    except Exception as e:
        logger.error(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
