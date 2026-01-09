#!/usr/bin/env python3
"""
Script para ingestar datos de 2026 en OpenSearch.
Uso: python scripts/ingest_2026_data.py [ruta_json_2026]

Asume que tienes un archivo JSON con estructura similar a los datos de 2025,
pero con información arancelaria de 2026.
"""
import json
import logging
import sys
from pathlib import Path
from opensearchpy import OpenSearch
from app.embedder_gemini import GeminiEmbedder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ingest_2026_data(json_file: str):
    """
    Ingesta datos de 2026 desde un archivo JSON.
    
    Estructura esperada del JSON:
    [
        {
            "fragment_id": "...",
            "text": "...",
            "chapter": "...",
            "heading": "...",
            "subheading": "...",
            ...
        }
    ]
    """
    from app.config import get_settings
    from app.os_index import get_os_client
    
    settings = get_settings()
    client = get_os_client()
    embedder = GeminiEmbedder()
    
    index_name = "tariff_fragments_2026"
    
    try:
        # Leer JSON
        logger.info(f"Leyendo datos de {json_file}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            data = [data]
        
        total = len(data)
        logger.info(f"Total de fragmentos a ingestar: {total}")
        
        # Ingestar en lotes
        batch_size = 100
        ingested = 0
        failed = 0
        
        for i in range(0, total, batch_size):
            batch = data[i:i+batch_size]
            
            for doc in batch:
                try:
                    # Asegurar estructura
                    fragment_id = doc.get("fragment_id", f"doc_{ingested}")
                    text = doc.get("text", "")
                    
                    if not text:
                        logger.warning(f"Documento sin texto: {fragment_id}")
                        failed += 1
                        continue
                    
                    # Generar embedding
                    embedding = embedder.embed_texts([text])[0]
                    
                    # Preparar documento con año
                    doc["embedding"] = embedding
                    doc["year"] = 2026  # Marca como 2026
                    
                    # Indexar
                    client.index(
                        index=index_name,
                        id=fragment_id,
                        body=doc
                    )
                    ingested += 1
                    
                    if ingested % 50 == 0:
                        logger.info(f"Ingested: {ingested}/{total}")
                
                except Exception as e:
                    logger.error(f"Error ingesting {fragment_id}: {e}")
                    failed += 1
        
        logger.info(f"\n=== INGESTION COMPLETE ===")
        logger.info(f"Ingested: {ingested}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Index: {index_name}")
        
        # Verificar conteo
        count = client.count(index=index_name)["count"]
        logger.info(f"Total documentos en {index_name}: {count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/ingest_2026_data.py <ruta_json_2026>")
        print("\nEjemplo:")
        print("  python scripts/ingest_2026_data.py data/afr_done/Arancel_2026.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    if not Path(json_file).exists():
        print(f"Error: Archivo no encontrado: {json_file}")
        sys.exit(1)
    
    success = ingest_2026_data(json_file)
    sys.exit(0 if success else 1)
