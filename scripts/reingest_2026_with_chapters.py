#!/usr/bin/env python3
"""
Reingestar datos de 2026 con extracción de chapter/heading/subheading.
Soporta checkpoints para continuar desde archivos interrumpidos.
"""
import json
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.os_index import get_os_client
from app.os_ingest import bulk_ingest_fragments
from app.embedder_gemini import GeminiEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHECKPOINT_FILE = Path("scripts/reingest_2026_checkpoint.json")

def extract_hs_codes_from_text(text: str) -> Dict[str, Optional[str]]:
    """
    Extrae chapter, heading, subheading del texto.
    
    Patrones:
    - "8450.11" -> chapter=84, heading=8450, subheading=8450.11
    - "Capítulo 84" -> chapter=84
    - "84.50" -> heading=8450
    """
    result = {"chapter": None, "heading": None, "subheading": None}
    
    # Patrón para subpartida completa: 8450.11, 4011.10, etc.
    subheading_match = re.search(r'\b(\d{2})(\d{2})\.(\d{2})\b', text)
    if subheading_match:
        ch = subheading_match.group(1)
        hd = ch + subheading_match.group(2)
        sh = f"{hd}.{subheading_match.group(3)}"
        result["chapter"] = ch
        result["heading"] = hd
        result["subheading"] = sh
        return result
    
    # Patrón para heading: 84.50, 40.11, etc.
    heading_match = re.search(r'\b(\d{2})\.(\d{2})\b', text)
    if heading_match:
        ch = heading_match.group(1)
        hd = ch + heading_match.group(2)
        result["chapter"] = ch
        result["heading"] = hd
        return result
    
    # Patrón para capítulo explícito: "Capítulo 84", "CAPITULO 40"
    chapter_match = re.search(r'cap[íi]tulo\s+(\d{2})', text, re.IGNORECASE)
    if chapter_match:
        result["chapter"] = chapter_match.group(1)
        return result
    
    # Patrón alternativo para códigos sin punto: "8450 11" o "401110"
    code_match = re.search(r'\b(\d{4})\s*(\d{2})\b', text)
    if code_match:
        hd = code_match.group(1)
        ch = hd[:2]
        sh = f"{hd}.{code_match.group(2)}"
        result["chapter"] = ch
        result["heading"] = hd
        result["subheading"] = sh
        return result
    
    return result

def load_checkpoint() -> Dict[str, Any]:
    """Carga el checkpoint si existe."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"processed_files": [], "total_fragments": 0}

def save_checkpoint(checkpoint: Dict[str, Any]):
    """Guarda el checkpoint."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    logger.info(f"Checkpoint guardado: {checkpoint['processed_files']}")

def process_afr_json(json_path: Path, year: int = 2026) -> List[Dict[str, Any]]:
    """Procesa un JSON de AFR y genera fragmentos con chapter/heading/subheading."""
    logger.info(f"Procesando {json_path.name}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    ar = data.get("analyzeResult", {})
    paragraphs = ar.get("paragraphs", [])
    
    fragments = []
    doc_id = json_path.stem.replace('.pdf', '').replace(' ', '_')
    
    for i, para in enumerate(paragraphs):
        text = para.get("content", "").strip()
        if not text or len(text) < 20:
            continue
        
        # Extraer códigos del texto
        codes = extract_hs_codes_from_text(text)
        
        # Obtener número de página
        page_num = None
        if para.get("boundingRegions"):
            page_num = para["boundingRegions"][0].get("pageNumber")
        
        fragment = {
            "fragment_id": f"{doc_id}_p{i}",
            "text": text,
            "doc_id": doc_id,
            "bucket": "afr_2026",
            "unit": "paragraph",
            "year": year,
        }
        
        # Agregar códigos si se encontraron
        if codes["chapter"]:
            fragment["chapter"] = codes["chapter"]
        if codes["heading"]:
            fragment["heading"] = codes["heading"]
        if codes["subheading"]:
            fragment["subheading"] = codes["subheading"]
        if page_num:
            fragment["page"] = page_num
        
        fragments.append(fragment)
    
    logger.info(f"  Extraídos {len(fragments)} fragmentos")
    
    # Estadísticas de códigos
    with_chapter = sum(1 for f in fragments if f.get("chapter"))
    with_heading = sum(1 for f in fragments if f.get("heading"))
    with_subheading = sum(1 for f in fragments if f.get("subheading"))
    
    logger.info(f"  Con chapter: {with_chapter}, heading: {with_heading}, subheading: {with_subheading}")
    
    return fragments

def main():
    # Directorio con JSONs de 2026
    data_dir = Path("data/afr_done_2026")
    
    if not data_dir.exists():
        logger.error(f"Directorio no encontrado: {data_dir}")
        sys.exit(1)
    
    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        logger.error(f"No se encontraron archivos JSON en {data_dir}")
        sys.exit(1)
    
    logger.info(f"Encontrados {len(json_files)} archivos JSON")
    
    # Cargar checkpoint
    checkpoint = load_checkpoint()
    processed_files = set(checkpoint.get("processed_files", []))
    
    if processed_files:
        logger.info(f"Checkpoint encontrado: {len(processed_files)} archivos ya procesados")
        logger.info(f"Fragmentos previos: {checkpoint.get('total_fragments', 0)}")
    else:
        logger.info("No hay checkpoint previo. Iniciando desde cero.")
    
    # Conectar a OpenSearch
    client = get_os_client()
    index_name = "tariff_fragments_2026"
    
    # Solo borrar índice si NO hay checkpoint (es la primera ejecución)
    if not processed_files and client.indices.exists(index=index_name):
        logger.warning(f"Borrando índice existente (primera ejecución): {index_name}")
        client.indices.delete(index=index_name)
    elif processed_files:
        logger.info("Usando índice existente y agregando fragmentos nuevos...")
    
    # Procesar archivos no procesados aún
    all_fragments = []
    files_to_process = [f for f in json_files if f.name not in processed_files]
    
    if not files_to_process:
        logger.info("✅ Todos los archivos ya han sido procesados.")
        count = client.count(index=index_name)["count"]
        logger.info(f"Total en índice: {count} documentos")
        return
    
    logger.info(f"Archivos a procesar: {len(files_to_process)} (ya procesados: {len(processed_files)})")
    
    for json_file in files_to_process:
        fragments = process_afr_json(json_file, year=2026)
        all_fragments.extend(fragments)
        
        # Actualizar checkpoint después de cada archivo
        processed_files.add(json_file.name)
        checkpoint["processed_files"] = sorted(list(processed_files))
        checkpoint["total_fragments"] = checkpoint.get("total_fragments", 0) + len(fragments)
        save_checkpoint(checkpoint)
        
        # Ingestar este lote inmediatamente
        if all_fragments:
            logger.info(f"Ingesting {len(all_fragments)} fragments...")
            bulk_ingest_fragments(all_fragments, index_name=index_name, embed=True, batch_size=50)
            all_fragments = []
    
    # Verificar
    count = client.count(index=index_name)["count"]
    logger.info(f"\n✅ Documentos en {index_name}: {count}")
    
    # Verificar capítulos
    logger.info("\nVerificando capítulos en el índice...")
    agg_query = {
        "size": 0,
        "aggs": {
            "chapters": {
                "terms": {"field": "chapter", "size": 30, "order": {"_key": "asc"}}
            }
        }
    }
    result = client.search(index=index_name, body=agg_query)
    chapters = result["aggregations"]["chapters"]["buckets"]
    
    logger.info(f"Capítulos encontrados: {len(chapters)}")
    for ch in chapters[:10]:
        logger.info(f"  Capítulo {ch['key']}: {ch['doc_count']} documentos")
    
    logger.info("\n✅ Reingest completado correctamente.")

if __name__ == "__main__":
    main()
