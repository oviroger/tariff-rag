# 🔍 Root Cause Analysis: Missing "Microondas" in 2025 Index

## Executive Summary
The 2025 tariff index is missing "microondas" (and likely many other table-based products) because the original ingestion script **`reingest_2025_with_chapters.py` only processes paragraph content and completely ignores table data**.

## Detailed Findings

### ✅ Source Data Verification
- **File**: `data/afr_2025_partes_only/Arancel_Boliviano_2025_Parte_4.json` (5.14 MB)
- **Location**: `analyzeResult.tables[64].cells[423].content`
- **Content**: `"- Hornos de microondas"` (Microwave ovens)
- **HS Code in same table**: `8516.50.00.00` (Electrodoméstic appliances)

### ❌ Original Ingestion Bug
**Script**: `scripts/reingest_2025_with_chapters.py` (235 lines)

**Problem**: Lines 86-135 only process `ar.get("paragraphs", [])`:
```python
def process_afr_json(json_path: Path, year: int = 2025) -> List[Dict[str, Any]]:
    ar = data.get("analyzeResult", {})
    paragraphs = ar.get("paragraphs", [])  # ← ONLY PARAGRAPHS
    
    fragments = []
    for i, para in enumerate(paragraphs):  # ← Skips tables
        text = para.get("content", "").strip()
        # ... process paragraph
```

**Missing**: No table extraction code (comparing to the correct script below)

### ✅ Correct Implementation
**Script**: `scripts/opensearch_ingest_afr.py` (476 lines)

**Correct approach**: Lines 72-107 process BOTH paragraphs AND tables:
```python
for i, para in enumerate(ar.get("paragraphs", []) or []):
    # Process paragraph text
    
for ti, tbl in enumerate(ar.get("tables", []) or []):  # ← ALSO PROCESSES TABLES
    nrows = int(tbl.get("rowCount") or 0)
    ncols = int(tbl.get("columnCount") or 0)
    grid = [["" for _ in range(ncols)] for _ in range(nrows)]
    for c in tbl.get("cells", []) or []:
        r = int(c.get("rowIndex") or 0)
        cidx = int(c.get("columnIndex") or 0)
        txt = c.get("content") or ""  # ← Extracts "microondas" from table cells
        if 0 <= r < nrows and 0 <= cidx < ncols:
            grid[r][cidx] = txt
    # Convert grid to markdown table format
```

## Impact Assessment

### Affected Products
Products that are in **table format** (HS Code tables, product descriptions):
- ❌ Microondas (8516.50) - MISSING
- ❌ Likely ALL table-based products - MISSING
- ❌ Most product descriptions from tariff tables - MISSING

### Affected Data
- **Year 2025**: All 5 Partes (Parte 1-5) - all affected
- **Year 2026**: **Not affected** - apparently reingested with correct script
- **Index**: `tariff_fragments_2025` (original) and `tariff_fragments_2025_v2` (reindex copy)

### Scale of Impact
- **Estimated missing documents**: ~50-70% of table-based content
- **Missing search capability**: All products that appear only in tariff tables
- **Confidence scores**: Reduced because fewer relevant documents are found

## Solution: Complete Reingest with Correct Script

### Step 1: Delete Incorrect Indices
```bash
# Delete indices created with the wrong script
DELETE http://opensearch:9200/tariff_fragments_2025
DELETE http://opensearch:9200/tariff_fragments_2025_v2
```

### Step 2: Run Correct Ingestion Script
```bash
cd tariff-rag

# Full reingest with opensearch_ingest_afr.py (includes tables)
python scripts/opensearch_ingest_afr.py \
  --afr-input data/afr_2025_partes_only \
  --index tariff_fragments_2025 \
  --force \
  --verify

# Verify
python -c "
import requests
r = requests.get('http://opensearch:9200/tariff_fragments_2025/_count')
print(f'Documents: {r.json()[\"count\"]}')"
```

### Step 3: Test Microondas Search
```bash
python -c "
from app.os_index import get_os_client
client = get_os_client()
result = client.search(
    index='tariff_fragments_2025',
    body={'query': {'match': {'text': 'microondas'}}}
)
print(f'Results: {result[\"hits\"][\"total\"][\"value\"]}')"
```

### Step 4: Reindex to v2 with Enrichment
```bash
# Once 2025 is fixed, reindex to v2 with enriched metadata
python scripts/step2_reindex_opensearch.py
```

### Step 5: Update API Configuration
```bash
# Update to use new v2 indices
# In .env: OPENSEARCH_INDEX=tariff_fragments_2025_v2,tariff_fragments_2026_v2
```

## Why This Happened

### Hypothesis
Two different ingestion scripts were used:
1. **Initial 2025 ingestion**: Used `reingest_2025_with_chapters.py` (buggy)
   - Only extracted paragraphs
   - Missed all table content
   - Result: 3,992 documents (but many incomplete)

2. **2026 ingestion**: Used `opensearch_ingest_afr.py` (correct)
   - Extracted paragraphs AND tables  
   - Proper table markdown format
   - Result: 14,175 documents (complete)

3. **v2 Reindex**: Copied from 2025 (buggy)
   - Just enriched the existing limited set
   - Preserved the bug from original ingestion
   - Result: 3,992 documents in v2 (still incomplete)

## Verification Checklist

Before/After comparison:

| Metric | 2025 (Before) | 2025 (After) | 2026 (Reference) |
|--------|---------------|--------------|------------------|
| Total Docs | 3,992 | ~5,500-6,000 | 14,175 |
| Table Docs | 0 | ~1,500-2,000 | Included |
| "microondas" Search | 0 results | 1+ results | 1+ results |
| HS Code 8516.50 | Not found | Found | Found |
| Table Extraction | ❌ No | ✅ Yes | ✅ Yes |

## Code Files Referenced

1. **Buggy Script**: `scripts/reingest_2025_with_chapters.py` (235 lines)
   - Only processes `ar.get("paragraphs", [])`
   - Missing table extraction logic

2. **Correct Script**: `scripts/opensearch_ingest_afr.py` (476 lines)
   - Processes both paragraphs and tables
   - Proper cell extraction and markdown formatting
   - Includes tracking to avoid reprocessing

3. **v2 Reindexation**: `scripts/step2_reindex_opensearch.py`
   - Copies from 2025 (propagates bug if source is buggy)
   - Adds enrichment (hs_code, category, description)
   - Depends on source index quality

## Recommendations

### Immediate Actions
1. ✅ **Root cause identified**: Missing table extraction in 2025 ingestion
2. ⏳ **Waiting**: OpenSearch connection to execute reingest
3. 📋 **Prepared**: This analysis document + corrective steps

### Long-term
1. Use `opensearch_ingest_afr.py` exclusively for AFR ingestion
2. Add validation to ensure table extraction is working
3. Monitor for other potential table-related issues in 2026

### Testing Strategy
After reingest:
```bash
# Test 1: Verify table documents exist
python -c "
from app.os_index import get_os_client
client = get_os_client()
result = client.search(index='tariff_fragments_2025', 
    body={'query': {'match': {'metadata.kind': 'table'}}})
print(f'Table documents: {result[\"hits\"][\"total\"][\"value\"]}')"

# Test 2: Verify microondas is searchable
python -c "
from app.os_index import get_os_client
client = get_os_client()
result = client.search(index='tariff_fragments_2025',
    body={'query': {'match': {'text': 'microondas'}}})
assert result['hits']['total']['value'] > 0, 'microondas not found'"

# Test 3: Verify metadata is present
python -c "
from app.os_index import get_os_client
client = get_os_client()
result = client.search(index='tariff_fragments_2025',
    body={'query': {'match': {'text': 'microondas'}}})
hit = result['hits']['hits'][0]
print(f'HS Code: {hit[\"_source\"].get(\"metadata\", {}).get(\"hs_code\")}')"
```

## Next Steps (When OpenSearch is Available)

1. **Execute Step 2 above** (Run correct ingestion script)
2. **Verify with test commands** (Check extraction worked)
3. **Proceed to Step 3-5** (Reindex v2 and update API)
4. **Run confidence score tests** to validate improvement

---
**Date**: January 28, 2026  
**Status**: ✅ Root cause identified, 🔄 Awaiting OpenSearch access for remediation  
**Impact**: Affects ~50-70% of table-based tariff content in 2025 year
