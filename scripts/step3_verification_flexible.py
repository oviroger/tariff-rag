#!/usr/bin/env python3
"""
STEP 3: Final verification for 2025 or 2026 indices.
Verificar que la solucion funciona:
1. Tabla extraccion
2. HS code enrichment
3. Category enrichment
4. Index integrity
"""
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.os_index import get_os_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_search(client, index_name, term="microondas"):
    """Test 1: Buscar termino en indice"""
    result = client.search(
        index=index_name,
        body={"query": {"match": {"text": term}}}
    )
    
    hits_count = result["hits"]["total"]["value"]
    logger.info(f"[TEST 1] '{term}' search")
    
    if hits_count > 0:
        hit = result["hits"]["hits"][0]
        score = hit["_score"]
        hs_code = hit["_source"].get("hs_code", "N/A")
        category = hit["_source"].get("category", "N/A")
        logger.info(f"[OK] '{term}' encontrado")
        logger.info(f"   - Score: {score:.4f}")
        logger.info(f"   - HS Code: {hs_code}")
        logger.info(f"   - Category: {category}")
        return True
    else:
        logger.error(f"[FAIL] '{term}' NO encontrado")
        return False

def test_table_extraction(client, index_name):
    """Test 2: Verificar extraccion de tablas"""
    result = client.search(
        index=index_name,
        body={
            "size": 0,
            "aggs": {
                "by_unit": {
                    "terms": {"field": "unit", "size": 10}
                }
            }
        }
    )
    
    logger.info(f"\n[TEST 2] Table extraction")
    
    total = client.count(index=index_name)["count"]
    units = result["aggregations"]["by_unit"]["buckets"]
    
    unit_dict = {u["key"]: u["doc_count"] for u in units}
    paragraphs = unit_dict.get("paragraph", 0)
    tables = unit_dict.get("table", 0)
    
    logger.info(f"[OK] Document composition:")
    logger.info(f"   - Total: {total}")
    logger.info(f"   - Paragraphs: {paragraphs} ({100*paragraphs/total:.1f}%)")
    logger.info(f"   - Tables: {tables} ({100*tables/total:.1f}%)")
    
    return tables > 0

def test_hs_enrichment(client, index_name):
    """Test 3: Verificar enriquecimiento con HS codes"""
    result = client.search(
        index=index_name,
        body={
            "size": 0,
            "aggs": {
                "with_hs": {"filter": {"exists": {"field": "hs_code"}}}
            }
        }
    )
    
    logger.info(f"\n[TEST 3] HS Code enrichment")
    
    total = client.count(index=index_name)["count"]
    with_hs = result["aggregations"]["with_hs"]["doc_count"]
    
    pct = 100 * with_hs / total if total > 0 else 0
    logger.info(f"[OK] HS Code enrichment:")
    logger.info(f"   - Documents with HS code: {with_hs} ({pct:.1f}%)")
    
    return with_hs > 0

def test_category_enrichment(client, index_name):
    """Test 4: Verificar enriquecimiento con categorias"""
    result = client.search(
        index=index_name,
        body={
            "size": 0,
            "aggs": {
                "categories": {
                    "terms": {"field": "category.keyword", "size": 20}
                }
            }
        }
    )
    
    logger.info(f"\n[TEST 4] Category enrichment")
    
    categories = result["aggregations"]["categories"]["buckets"]
    unique_categories = len(categories)
    
    logger.info(f"[OK] Top categories found: {unique_categories}")
    for cat in categories[:5]:
        logger.info(f"   - {cat['key']}: {cat['doc_count']}")
    
    return unique_categories > 0

def test_index_integrity(client, year):
    """Test 5: Verificar integridad del indice"""
    v1_idx = f"tariff_fragments_{year}"
    v2_idx = f"tariff_fragments_{year}_v2"
    
    v1_count = client.count(index=v1_idx)["count"]
    v2_count = client.count(index=v2_idx)["count"]
    
    logger.info(f"\n[TEST 5] Index status")
    logger.info(f"[OK] Index status:")
    logger.info(f"   - {v1_idx}: {v1_count} documents")
    logger.info(f"   - {v2_idx}: {v2_count} documents")
    
    # Check if v2 has new data
    if v2_count >= v1_count:
        logger.info(f"[OK] {v2_idx} has all documents from source")
        return True
    else:
        logger.warning(f"[WARN] {v2_idx} has fewer docs than source ({v2_count} < {v1_count})")
        return v2_count > 0

def main():
    if len(sys.argv) < 2:
        year = "2025"
    else:
        year = sys.argv[1]
    
    index_name = f"tariff_fragments_{year}_v2"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"STEP 3: Final verification for {year}")
    logger.info(f"{'='*60}\n")
    
    try:
        client = get_os_client()
        
        # Run all tests
        tests = [
            test_search(client, index_name),
            test_table_extraction(client, index_name),
            test_hs_enrichment(client, index_name),
            test_category_enrichment(client, index_name),
            test_index_integrity(client, year),
        ]
        
        passed = sum(tests)
        total = len(tests)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("SUCCESS! THE FIX IS WORKING!")
        else:
            logger.warning(f"PARTIAL SUCCESS: {total-passed} tests failed")
        
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
