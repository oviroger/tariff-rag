#!/usr/bin/env python3
"""
STEP 2: Reindex with metadata enrichment (flexible for any year).

Toma los documentos de tariff_fragments_YYYY y crea tariff_fragments_YYYY_v2
con enriquecimiento de metadatos (hs_code, category, description)
"""
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.os_index import get_os_client, ensure_index
from opensearchpy import helpers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# HS code categories mapping
HS_CATEGORIES = {
    "01": "Animales vivos",
    "02": "Carne y despojos comestibles",
    "03": "Pescados y crustaceos",
    "04": "Leche, huevos, miel",
    "05": "Otros productos de origen animal",
    "06": "Plantas vivas y productos de floricultura",
    "07": "Legumbres, plantas, raices",
    "08": "Frutas y frutos comestibles",
    "09": "Cafe, te, especias",
    "10": "Cereales",
    "11": "Productos de la molineria",
    "12": "Semillas y frutos oleaginosos",
    "13": "Gomas, resinas, jugos",
    "14": "Materias primas vegetales",
    "15": "Grasas y aceites animales",
    "16": "Carnes, pescados y crustaceos preparados",
    "17": "Azucares y articulos de confiteria",
    "18": "Cacao y sus preparaciones",
    "19": "Productos de cereales, harina, almidon",
    "20": "Preparaciones de verduras, frutas",
    "21": "Preparaciones alimenticias diversas",
    "22": "Bebidas, vinagre",
    "23": "Residuos de industrias alimentarias",
    "24": "Tabaco y sucedaneos",
    "25": "Sal, azufre, tierra y piedra",
    "26": "Minerales, escorias y cenizas",
    "27": "Combustibles minerales, aceites",
    "28": "Productos quimicos inorganicos",
    "29": "Productos quimicos organicos",
    "30": "Productos farmaceuticos",
    "31": "Abonos",
    "32": "Extractos curtientes, colorantes",
    "33": "Aceites esenciales, cosmeticos",
    "34": "Jabon, detergentes, ceras",
    "35": "Materias primas para industria textil",
    "36": "Polvora y articulos pirotecnicos",
    "37": "Fotografia, cinematografia",
    "38": "Productos quimicos diversos",
    "39": "Plasticos y sus manufactura",
    "40": "Caucho y manufactura de caucho",
    "41": "Pieles y cueros",
    "42": "Artículos de cuero",
    "43": "Peleteria y articulos de peleteria",
    "44": "Madera y articulos de madera",
    "45": "Corcho y articulos de corcho",
    "46": "Manufactura de esparto",
    "47": "Pasta de madera, papel",
    "48": "Papel, carton, articulos de papel",
    "49": "Libros, articulos impresos",
    "50": "Seda",
    "51": "Lana y pelo fino",
    "52": "Algodon",
    "53": "Fibras vegetales textiles",
    "54": "Filamentos sinteticos",
    "55": "Fibras sinteticas discontinuas",
    "56": "Lana cardada",
    "57": "Alfombras y revestimientos textiles",
    "58": "Tejidos especiales, anudados",
    "59": "Telas impregnadas, recubiertas",
    "60": "Tejidos de punto",
    "61": "Prendas y complementos de punto",
    "62": "Prendas y complementos textiles",
    "63": "Otros articulos textiles",
    "64": "Calzado",
    "65": "Sombreria",
    "66": "Paraguas, bastones",
    "67": "Plumas, rellenos de plumas",
    "68": "Articulos de piedra",
    "69": "Productos ceramicos",
    "70": "Vidrio y manufactura de vidrio",
    "71": "Perlas, piedras, metales preciosos",
    "72": "Hierro y acero",
    "73": "Articulos de hierro y acero",
    "74": "Cobre y articulos de cobre",
    "75": "Niquel y articulos de niquel",
    "76": "Aluminio y articulos de aluminio",
    "78": "Plomo y articulos de plomo",
    "79": "Zinc y articulos de zinc",
    "80": "Estaño y articulos de estaño",
    "81": "Metales diversos",
    "82": "Herramientas y cutlery",
    "83": "Manufactura diversa de metales",
    "84": "Reactores nucleares, calderas, maquinas",
    "85": "Maquinas, aparatos electricos",
    "86": "Vehiculos y piezas de vehiculos",
    "87": "Vehiculos que no sean ferroviarios",
    "88": "Aeronaves y piezas de aeronaves",
    "89": "Navegacion maritima",
    "90": "Instrumentos de optica, medida",
    "91": "Relojes y partes de relojes",
    "92": "Instrumentos musicales",
    "93": "Armas y municiones",
    "94": "Muebles, articulos de cama",
    "95": "Juguetes, articulos deportivos",
    "96": "Articulos diversos",
    "97": "Objetos de arte, antiguedades",
}

def extract_hs_code(text: str) -> Optional[str]:
    """Extraer codigo HS del texto"""
    # Buscar patron XXXX.XX.XX
    import re
    patterns = [
        r'\b(\d{4}\.\d{2}\.\d{2})\b',
        r'\b(\d{4}\.\d{2})\b',
        r'\bCÓDIGO[:\s]+(\d{4}(?:\.\d{2})?(?:\.\d{2})?)\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def get_category_from_hs(hs_code: str) -> Optional[str]:
    """Obtener categoria del codigo HS"""
    if not hs_code:
        return None
    
    chapter = hs_code.split('.')[0]
    return HS_CATEGORIES.get(chapter)

def enrich_document(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Enriquecer documento con metadatos"""
    source = hit["_source"].copy()
    
    # Si ya tiene hs_code y category, devolver tal cual
    if "hs_code" in source and "category" in source:
        return source
    
    # Intentar extraer del titulo o descripcion
    full_text = f"{source.get('title', '')} {source.get('text', '')}".upper()
    
    hs_code = extract_hs_code(full_text)
    if hs_code:
        source["hs_code"] = hs_code
        category = get_category_from_hs(hs_code)
        if category:
            source["category"] = category
    
    source["enriched_at"] = "2026-01-28"
    return source

def main():
    s = get_settings()
    client = get_os_client()
    
    # Determinar que ano procesar
    if len(sys.argv) > 1:
        year = sys.argv[1]
    else:
        year = "2026"  # Default a 2026 para continuar
    
    source_index = f"tariff_fragments_{year}"
    target_index = f"tariff_fragments_{year}_v2"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"STEP 2: Reindexing {year} with metadata enrichment")
    logger.info(f"{'='*60}\n")
    
    logger.info(f"[INFO] Source index: {source_index}")
    logger.info(f"[INFO] Target index: {target_index}")
    
    # Verificar que source existe
    if not client.indices.exists(index=source_index):
        logger.error(f"[ERROR] Source index {source_index} no existe!")
        return
    
    # Limpiar target si existe (para reconstruir con nuevos datos)
    if client.indices.exists(index=target_index):
        logger.info(f"[INFO] Borrando {target_index} existente para reconstruir...")
        client.indices.delete(index=target_index)
    
    # Crear target index
    ensure_index(target_index)
    
    # Contar documentos
    source_count = client.count(index=source_index)["count"]
    logger.info(f"[INFO] Documentos a procesar: {source_count}")
    
    # Reindexar con enriquecimiento
    docs_processed = 0
    batch = []
    batch_size = 100
    
    logger.info(f"\n[PROCESSING] Iniciando reindexing...")
    
    response = client.search(
        index=source_index,
        scroll="5m",
        size=batch_size,
        body={"query": {"match_all": {}}}
    )
    
    scroll_id = response["_scroll_id"]
    
    while True:
        hits = response["hits"]["hits"]
        if not hits:
            break
        
        for hit in hits:
            enriched = enrich_document(hit)
            
            batch.append({
                "_index": target_index,
                "_id": hit["_id"],
                "_source": enriched,
            })
            
            if len(batch) >= batch_size:
                helpers.bulk(client, batch)
                docs_processed += len(batch)
                logger.info(f"[PROGRESS] {docs_processed}/{source_count} documentos procesados")
                batch = []
        
        # Siguiente pagina
        response = client.scroll(scroll_id=scroll_id, scroll="5m")
        scroll_id = response["_scroll_id"]
    
    # Procesar ultimo batch
    if batch:
        helpers.bulk(client, batch)
        docs_processed += len(batch)
    
    # Finalizar scroll
    try:
        client.clear_scroll(scroll_id=scroll_id)
    except:
        pass
    
    logger.info(f"\n[OK] Reindexing completado")
    logger.info(f"[STATS] Documentos en {target_index}: {docs_processed}")
    
    # Verificacion de enriquecimiento
    agg_query = {
        "size": 0,
        "aggs": {
            "with_hs_code": {
                "filter": {"exists": {"field": "hs_code"}}
            },
            "with_category": {
                "filter": {"exists": {"field": "category"}}
            },
            "by_category": {
                "terms": {"field": "category.keyword", "size": 20}
            }
        }
    }
    
    result = client.search(index=target_index, body=agg_query)
    
    logger.info(f"\n[STATS] Enriquecimiento:")
    logger.info(f"   - Con HS code: {result['aggregations']['with_hs_code']['doc_count']}")
    logger.info(f"   - Con categoria: {result['aggregations']['with_category']['doc_count']}")
    
    logger.info(f"\n[STATS] Top categorias:")
    for cat in result['aggregations']['by_category']['buckets'][:10]:
        logger.info(f"   - {cat['key']}: {cat['doc_count']}")
    
    logger.info(f"\n{'='*60}")
    logger.info("Step 2 completado exitosamente.")
    logger.info(f"{'='*60}\n")

if __name__ == "__main__":
    main()
