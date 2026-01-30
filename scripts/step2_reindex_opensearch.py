#!/usr/bin/env python3
"""
STEP 2: Reindex 2025 to v2 with metadata enrichment.

Toma los documentos de tariff_fragments_2025 y crea tariff_fragments_2025_v2
con enriquecimiento de metadatos:
- hs_code (chapter.heading.subheading)
- category (description del heading)
- description (enrichment)
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
    "22": "Bebidas, vinagres, alcoholes",
    "23": "Residuos industrias alimentarias",
    "24": "Tabaco y sucedaneos",
    "25": "Sal, azufre, tierras, piedras",
    "26": "Menas, escorias, cenizas",
    "27": "Combustibles minerales, aceites",
    "28": "Productos quimicos inorganicos",
    "29": "Productos quimicos organicos",
    "30": "Productos farmaceuticos",
    "31": "Abonos",
    "32": "Taninos, colorantes, pinturas",
    "33": "Aceites esenciales, cosmeticos",
    "34": "Jabon, detergentes, cera",
    "35": "Materias proteinicas, colas",
    "36": "Polvora, explosivos, articulos pirotecnicos",
    "37": "Fotografia, cinematografia",
    "38": "Productos quimicos diversos",
    "39": "Materias plasticas",
    "40": "Caucho y articulos de caucho",
    "41": "Pieles y cueros",
    "42": "Articulos de cuero, talabarteria",
    "43": "Peleria y articulos de peleteria",
    "44": "Madera y articulos de madera",
    "45": "Corcho y articulos de corcho",
    "46": "Articulos de esparto",
    "47": "Pasta de madera, papel reciclado",
    "48": "Papel y carton",
    "49": "Articulos de papel, carton impresos",
    "50": "Seda",
    "51": "Lana y pelos finos",
    "52": "Algodon",
    "53": "Otras fibras textiles",
    "54": "Filamentos sinteticos, artificiales",
    "55": "Fibras sinteticas, artificiales discontinuas",
    "56": "Lana cardada, peinada, hilados textiles",
    "57": "Alfombras y revestimientos textiles",
    "58": "Tejidos especiales, superficies textiles",
    "59": "Tejidos recubiertos, textiles encolados",
    "60": "Tejidos de punto",
    "61": "Prendas de vestir punto",
    "62": "Prendas de vestir tejidos",
    "63": "Articulos textiles confeccionados diversos",
    "64": "Calzado, polainas",
    "65": "Sombreria",
    "66": "Paraguas, sombrillas, bastones",
    "67": "Plumas, plumones, articulos",
    "68": "Articulos de piedra, yeso",
    "69": "Productos ceramicos",
    "70": "Vidrio y articulos de vidrio",
    "71": "Perlas finas, metales preciosos",
    "72": "Hierro y acero",
    "73": "Articulos de hierro, acero",
    "74": "Cobre y articulos de cobre",
    "75": "Niquel y articulos de niquel",
    "76": "Aluminio y articulos de aluminio",
    "78": "Plomo y articulos de plomo",
    "79": "Cinc y articulos de cinc",
    "80": "Estano y articulos de estano",
    "81": "Otros metales comunes, cermets",
    "82": "Herramientas, cutleria, articulos metales",
    "83": "Articulos diversos de metales comunes",
    "84": "Reactores nucleares, calderas, maquinas",
    "85": "Maquinas, aparatos electricos",
    "86": "Vehiculos y material ferrocarril",
    "87": "Vehiculos automoviles, partes",
    "88": "Aeronaves, vehiculos espaciales",
    "89": "Buques y estructuras flotantes",
    "90": "Instrumentos optica, fotografia",
    "91": "Relojeria",
    "92": "Instrumentos musica, partes",
    "93": "Armas, municiones, accesorios",
    "94": "Muebles, articulos alumbrado",
    "95": "Juguetes, articulos deportivos",
    "96": "Articulos manufacturados diversos",
    "97": "Objetos de arte, antiguedades",
    "98": "Conjuntos, remanufacturados",
    "99": "Clasificacion especial, no especificado",
}

def enrich_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Enriquece documento con metadata."""
    source = doc.get("_source", {})
    
    # Extraer HS code si existe
    chapter = source.get("chapter")
    heading = source.get("heading")
    subheading = source.get("subheading")
    
    hs_code = None
    if subheading:
        hs_code = subheading
    elif heading:
        hs_code = heading
    elif chapter:
        hs_code = chapter
    
    # Enriquecer con categoria
    category = None
    if chapter:
        category = HS_CATEGORIES.get(str(chapter).zfill(2), "Otros productos")
    
    # Enriquecer documento
    enriched = dict(source)
    if hs_code:
        enriched["hs_code"] = hs_code
    if category:
        enriched["category"] = category
    enriched["enriched_at"] = "2026-01-28"
    
    return enriched

def main():
    s = get_settings()
    client = get_os_client()
    
    source_index = "tariff_fragments_2025"
    target_index = "tariff_fragments_2025_v2"
    
    logger.info(f"\n{'='*60}")
    logger.info("STEP 2: Reindexing with metadata enrichment")
    logger.info(f"{'='*60}\n")
    
    logger.info(f"[INFO] Source index: {source_index}")
    logger.info(f"[INFO] Target index: {target_index}")
    
    # Asegurar que el índice destino existe
    ensure_index(target_index)
    
    # Contar documentos
    source_count = client.count(index=source_index)["count"]
    logger.info(f"[INFO] Documentos a procesar: {source_count}")
    
    # Reindexar con enriquecimiento
    docs_processed = 0
    batch = []
    batch_size = 100
    
    # Usar scroll para procesar todos los documentos
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
        
        # Siguiente página
        response = client.scroll(scroll_id=scroll_id, scroll="5m")
        scroll_id = response["_scroll_id"]
    
    # Procesar último batch
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
    
    # Verificación de enriquecimiento
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
    
    # Verificar "microondas" en v2
    logger.info(f"\n[SEARCH] Verificando 'microondas' en v2...")
    search_result = client.search(
        index=target_index,
        body={"query": {"match": {"text": "microondas"}}}
    )
    hits = search_result["hits"]["total"]["value"]
    
    if hits > 0:
        logger.info(f"[OK] 'microondas' encontrado en {hits} documentos en v2")
        first_hit = search_result["hits"]["hits"][0]
        logger.info(f"   - HS Code: {first_hit['_source'].get('hs_code', 'N/A')}")
        logger.info(f"   - Categoria: {first_hit['_source'].get('category', 'N/A')}")
    else:
        logger.warning(f"[ERROR] 'microondas' NO encontrado en v2")
    
    logger.info(f"\n{'='*60}")
    logger.info("Step 2 completado exitosamente.")
    logger.info(f"{'='*60}\n")

if __name__ == "__main__":
    main()
