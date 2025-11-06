# 📚 Arquitectura del Sistema Tariff-RAG

## Índice

1. [Visión General](#visión-general)
2. [Arquitectura de Componentes](#arquitectura-de-componentes)
3. [Flujo de Datos](#flujo-de-datos)
4. [Módulos del Backend](#módulos-del-backend)
5. [Configuración](#configuración)
6. [Despliegue](#despliegue)
7. [Métricas y Evaluación](#métricas-y-evaluación)
8. [Troubleshooting](#troubleshooting)

---

## Visión General

**Tariff-RAG** es un sistema RAG (Retrieval-Augmented Generation) para clasificación arancelaria que combina:

- 🔍 **Búsqueda Híbrida**: Semántica (kNN) + Léxica (BM25)
- 🤖 **LLM**: Google Gemini para generación y embeddings
- 📄 **OCR**: Azure Form Recognizer o Tesseract
- 💾 **Vector DB**: OpenSearch con índices kNN
- 🗄️ **Fuente de Datos**: MySQL como fuente adicional de información para el corpus

**Caso de uso**: Dado un producto (ej: "Neumáticos radiales 205/55R16"), el sistema:
1. Busca fragmentos relevantes en normativa arancelaria y casos previos
2. Genera el código HS correcto (ej: 4011.10.00.00)
3. Proporciona evidencia textual y confianza

---

## Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                       CAPA DE PRESENTACIÓN                  │
├─────────────────────────────────────────────────────────────┤
│  Gradio UI (Puerto 7860)                                    │
│  - Interfaz web interactiva                                 │
│  - Formularios de clasificación                             │
│  - Visualización de resultados                              │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────▼────────────────────────────────────────┐
│                      CAPA DE APLICACIÓN                      │
├─────────────────────────────────────────────────────────────┤
│  FastAPI (Puerto 8000)                                      │
│  ┌───────────────┬──────────────┬─────────────────────┐    │
│  │  /classify    │  /query      │  /health /metrics   │    │
│  └───────┬───────┴──────┬───────┴──────────┬──────────┘    │
│          │              │                   │                │
│  ┌───────▼──────────────▼───────────────────▼──────────┐   │
│  │        Orquestador RAG (chain_rag.py)              │   │
│  │  - Pipeline de retrieval                           │   │
│  │  - Re-ranking                                      │   │
│  │  - Generación con LLM                              │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────┬───────────────────┬────────────────────┘
                     │                   │
        ┌────────────▼─────┐    ┌───────▼──────────┐
        │  Retrieval Layer │    │  Generation Layer│
        │  ────────────────│    │  ────────────────│
        │  - Embeddings    │    │  - Gemini API    │
        │  - Hybrid Search │    │  - Prompt Eng.   │
        │  - Reranking     │    │  - Parsing       │
        └────────┬─────────┘    └──────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│                      CAPA DE DATOS                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   OpenSearch     │  │    MySQL     │  │ Gemini API   │ │
│  │   (Puerto 9200)  │  │ (Puerto 3306)│  │  (Externo)   │ │
│  │ ──────────────── │  │ ──────────── │  │ ──────────── │ │
│  │ • Fragmentos     │  │ • Casos      │  │ • Embeddings │ │
│  │ • Embeddings     │  │ • Productos  │  │ • Generation │ │
│  │ • Índices kNN    │  │ • Histórico  │  │              │ │
│  └──────────────────┘  └──────────────┘  └──────────────┘ │
│         ▲                      │                            │
│         │                      │ ETL                        │
│         └──────────────────────┘                            │
│           Ingestión desde MySQL → OpenSearch                │
└─────────────────────────────────────────────────────────────┘
```

### Servicios Docker

| Servicio | Imagen | Puerto | Función |
|----------|--------|--------|---------|
| **opensearch** | `opensearchproject/opensearch:2.11.0` | 9200, 9600 | Motor de búsqueda vectorial y léxica |
| **dashboards** | `opensearchproject/opensearch-dashboards:2.11.0` | 5601 | UI de monitoreo de OpenSearch |
| **mysql** | `mysql:8.0` | 3306 | **Fuente de datos**: casos de clasificación, productos históricos |
| **api** | `python:3.11-slim` (custom) | 8000 | Backend FastAPI con lógica RAG |
| **ui** | `python:3.11-slim` | 7860 | Frontend Gradio |

---

## Flujo de Datos

### 1. Ingesta de Documentos (Indexación)

```
FUENTES DE DATOS:
┌─────────┐    ┌─────────────┐
│ PDF/IMG │    │   MySQL DB  │
│(Normat.)│    │ (Histórico) │
└────┬────┘    └──────┬──────┘
     │                │
     │ OCR            │ ETL
     ▼                ▼
┌──────────┐    ┌──────────┐
│  Texto   │    │  Texto   │
│  Crudo   │    │ Casos    │
└────┬─────┘    └────┬─────┘
     │               │
     └───────┬───────┘
             ▼
        ┌──────────┐
        │Chunking  │
        └────┬─────┘
             ▼
        ┌───────────┐
        │ Embedding │
        └────┬──────┘
             ▼
        ┌──────────┐
        │OpenSearch│
        │  Índice  │
        └──────────┘
```

#### Paso 1a: OCR (Extracción desde PDFs)

**Azure Form Recognizer** (recomendado para producción):
```python
# app/ocr/azure_provider.py
from azure.ai.formrecognizer import DocumentAnalysisClient

def extract_pdf(file_path: str) -> List[OCRFragment]:
    client = DocumentAnalysisClient(endpoint=ENDPOINT, credential=KEY)
    
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-layout", f)
        result = poller.result()
    
    fragments = []
    for page in result.pages:
        for line in page.lines:
            fragments.append(OCRFragment(
                text=line.content,
                page=page.page_number,
                bbox=(line.polygon[0].x, line.polygon[0].y, 
                      line.polygon[2].x - line.polygon[0].x,
                      line.polygon[2].y - line.polygon[0].y),
                confidence=line.confidence
            ))
    
    return fragments
```

**Tesseract** (alternativa gratuita):
```python
# app/ocr/tesseract_provider.py
import pytesseract
import pypdfium2 as pdfium

def extract_pdf(file_path: str) -> List[OCRFragment]:
    pdf = pdfium.PdfDocument(file_path)
    fragments = []
    
    for page_idx in range(len(pdf)):
        # Renderizar a 300 DPI
        page = pdf.get_page(page_idx)
        bitmap = page.render(scale=300/72.0).to_pil()
        
        # OCR con detección de líneas
        data = pytesseract.image_to_data(
            bitmap, 
            lang="spa+eng",
            output_type=pytesseract.Output.DICT
        )
        
        # Agrupar por líneas
        for i, text in enumerate(data["text"]):
            if text.strip():
                fragments.append(OCRFragment(
                    text=text,
                    page=page_idx + 1,
                    bbox=(data["left"][i], data["top"][i],
                          data["width"][i], data["height"][i]),
                    confidence=float(data["conf"][i]) / 100.0
                ))
    
    pdf.close()
    return fragments
```

#### Paso 1b: ETL desde MySQL (Casos Históricos)

```python
# app/etl_mysql.py
from typing import List, Optional
from pydantic import BaseModel
import pymysql
from app.config import get_settings

class MySQLFragment(BaseModel):
    """Fragmento extraído de MySQL."""
    text: str
    fragment_id: str
    metadata: dict

def extract_mysql_fragments(
    table: str = "product_cases",
    text_column: str = "description",
    id_column: str = "id"
) -> List[MySQLFragment]:
    """
    Extrae fragmentos de texto desde MySQL para indexar en OpenSearch.
    
    Caso de uso típico: 
    - Tabla 'product_cases' con casos históricos de clasificación
    - Tabla 'products' con descripciones de productos
    - Tabla 'rulings' con resoluciones arancelarias
    
    Args:
        table: Nombre de la tabla
        text_column: Columna con el texto a indexar
        id_column: Columna con identificador único
    
    Returns:
        Lista de fragmentos para indexar
    """
    settings = get_settings()
    
    # Conectar a MySQL
    connection = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_db,
        charset='utf8mb4'
    )
    
    fragments = []
    
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Query para extraer datos relevantes
            # Ajustar según tu esquema de BD
            query = f"""
                SELECT 
                    {id_column} as id,
                    {text_column} as text,
                    hs_code,
                    product_name,
                    classification_date,
                    confidence_score
                FROM {table}
                WHERE {text_column} IS NOT NULL 
                  AND LENGTH({text_column}) > 50
                ORDER BY classification_date DESC
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for row in rows:
                # Construir texto enriquecido
                text_parts = [row['text']]
                
                if row.get('product_name'):
                    text_parts.insert(0, f"Producto: {row['product_name']}")
                
                if row.get('hs_code'):
                    text_parts.append(f"Código HS: {row['hs_code']}")
                
                if row.get('confidence_score'):
                    text_parts.append(f"Confianza previa: {row['confidence_score']:.2f}")
                
                full_text = "\n".join(text_parts)
                
                fragments.append(MySQLFragment(
                    text=full_text,
                    fragment_id=f"mysql_{table}_{row['id']}",
                    metadata={
                        "source": "mysql",
                        "table": table,
                        "record_id": row['id'],
                        "hs_code": row.get('hs_code'),
                        "product_name": row.get('product_name'),
                        "classification_date": str(row.get('classification_date')),
                        "confidence_score": row.get('confidence_score'),
                        "bucket": "historico_mysql"
                    }
                ))
        
    finally:
        connection.close()
    
    return fragments


def sync_mysql_to_opensearch(
    tables: List[str] = ["product_cases", "customs_rulings"],
    batch_size: int = 100
):
    """
    Sincroniza múltiples tablas de MySQL a OpenSearch.
    
    Ejemplo:
        sync_mysql_to_opensearch(["product_cases", "customs_rulings"])
    """
    from app.os_ingest import bulk_ingest_fragments
    from app.config import get_settings
    
    settings = get_settings()
    total_indexed = 0
    
    for table in tables:
        print(f"📥 Extrayendo desde tabla: {table}")
        
        fragments = extract_mysql_fragments(table)
        
        if fragments:
            # Convertir a dict para ingestión
            fragments_dict = [f.model_dump() for f in fragments]
            
            # Indexar en batches
            for i in range(0, len(fragments_dict), batch_size):
                batch = fragments_dict[i:i+batch_size]
                bulk_ingest_fragments(batch, settings.opensearch_index)
                total_indexed += len(batch)
                print(f"  ✅ Indexados {len(batch)} fragmentos")
        
        print(f"  Total desde {table}: {len(fragments)}")
    
    print(f"\n🎉 Total indexado desde MySQL: {total_indexed} fragmentos")
```

#### Paso 2: Chunking (Fragmentación)

```python
# scripts/chunk_and_index.py
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Divide el texto en fragmentos solapados para preservar contexto.
    
    Args:
        text: Texto completo del documento
        chunk_size: Tokens por fragmento (~500 tokens ≈ 2000 caracteres)
        overlap: Tokens de solapamiento entre fragmentos
    
    Returns:
        Lista de fragmentos de texto
    """
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks

# Ejemplo de uso
full_text = "\n".join([f.text for f in ocr_fragments])
chunks = chunk_text(full_text, chunk_size=500, overlap=50)
```

#### Paso 3: Generación de Embeddings

```python
# app/embedder_gemini.py
import google.generativeai as genai

class GeminiEmbedder:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "models/embedding-001"  # 768 dimensiones
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para una lista de textos.
        
        Returns:
            Lista de vectores de 768 dimensiones
        """
        embeddings = []
        
        # Procesar en batches de 100 (límite de API)
        for i in range(0, len(texts), 100):
            batch = texts[i:i+100]
            
            for text in batch:
                result = genai.embed_content(
                    content=text,
                    model=self.model,
                    task_type="retrieval_document"
                )
                embeddings.append(result["embedding"])
        
        return embeddings
```

#### Paso 4: Indexación en OpenSearch

```python
# app/os_ingest.py
from opensearchpy import OpenSearch, helpers

def bulk_ingest_fragments(fragments: List[dict], index_name: str):
    """
    Indexa fragmentos en OpenSearch usando bulk API.
    
    Acepta fragmentos de múltiples fuentes:
    - PDFs procesados con OCR
    - Casos históricos desde MySQL
    - Datos estructurados de APIs externas
    
    Args:
        fragments: Lista de dicts con {text, embedding, metadata}
        index_name: Nombre del índice (ej: tariff_fragments)
    """
    client = get_os_client()
    embedder = GeminiEmbedder()
    
    # Generar embeddings en batch
    texts = [f["text"] for f in fragments]
    embeddings = embedder.embed_texts(texts)
    
    # Preparar documentos para bulk insert
    actions = []
    for fragment, embedding in zip(fragments, embeddings):
        doc = {
            "_index": index_name,
            "_source": {
                "text": fragment["text"],
                "embedding": embedding,
                "fragment_id": fragment.get("fragment_id"),
                "bucket": fragment.get("metadata", {}).get("bucket", "normativa"),
                "indexed_at": datetime.utcnow().isoformat()
            }
        }
        
        # Agregar metadata específica según la fuente
        metadata = fragment.get("metadata", {})
        
        # Si viene de PDF (OCR)
        if "page" in fragment:
            doc["_source"]["page"] = fragment["page"]
            doc["_source"]["doc_id"] = fragment.get("doc_id")
        
        # Si viene de MySQL (histórico)
        if metadata.get("source") == "mysql":
            doc["_source"]["source"] = "mysql"
            doc["_source"]["table"] = metadata.get("table")
            doc["_source"]["record_id"] = metadata.get("record_id")
            doc["_source"]["hs_code"] = metadata.get("hs_code")
            doc["_source"]["product_name"] = metadata.get("product_name")
        
        # Campos comunes (capítulo, partida, subpartida)
        for field in ["chapter", "heading", "subheading"]:
            if field in fragment or field in metadata:
                doc["_source"][field] = fragment.get(field) or metadata.get(field)
        
        actions.append(doc)
    
    # Bulk insert
    success, failed = helpers.bulk(client, actions, raise_on_error=False)
    print(f"✅ Indexados: {success} | ❌ Fallidos: {len(failed)}")
```

#### Paso 5: ~~Registro en MySQL~~ (No aplica - MySQL es fuente)

**Nota**: MySQL actúa como **fuente de datos**, no como destino. Los datos de MySQL se extraen mediante ETL y se indexan en OpenSearch junto con los documentos procesados vía OCR.

**Esquema típico en MySQL (ejemplo)**:

```sql
-- Tabla de casos históricos de clasificación
CREATE TABLE product_cases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(500),
    description TEXT,
    hs_code VARCHAR(20),
    classification_date DATE,
    confidence_score FLOAT,
    classifier_name VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_hs_code (hs_code),
    INDEX idx_date (classification_date)
);

-- Tabla de resoluciones aduaneras
CREATE TABLE customs_rulings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ruling_number VARCHAR(50) UNIQUE,
    product_description TEXT,
    hs_classification VARCHAR(20),
    legal_basis TEXT,
    ruling_date DATE,
    country_code CHAR(2),
    INDEX idx_ruling (ruling_number),
    INDEX idx_hs (hs_classification)
);

-- Tabla de productos con clasificación validada
CREATE TABLE validated_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    commercial_name VARCHAR(500),
    technical_specs TEXT,
    hs_code_6_digits VARCHAR(10),
    hs_code_full VARCHAR(20),
    validation_status ENUM('pending', 'approved', 'rejected'),
    validated_by VARCHAR(100),
    validated_at TIMESTAMP,
    INDEX idx_status (validation_status),
    INDEX idx_hs (hs_code_6_digits)
);
```

---

### 2. Consulta y Clasificación (RAG Pipeline)

```
┌───────────┐    ┌──────────────────┐    ┌───────────┐    ┌─────────┐
│  Usuario  │───▶│  Hybrid Search   │───▶│ Re-ranking│───▶│ LLM Gen │
│  (Query)  │    │ (OpenSearch kNN  │    │   (RRF)   │    │ (Gemini)│
└───────────┘    │    + BM25)       │    └───────────┘    └────┬────┘
                 │                  │                          │
                 │ Busca en:        │                          │
                 │ • PDFs normativa │                          │
                 │ • Casos MySQL    │                          ▼
                 └──────────────────┘                   ┌──────────┐
                                                        │ Respuesta│
                                                        │+ Código  │
                                                        │+ Fuentes │
                                                        └──────────┘
```

El flujo de búsqueda recupera fragmentos de **ambas fuentes**:
1. **Documentos normativos** (PDFs procesados con OCR)
2. **Casos históricos** (extraídos de MySQL)

OpenSearch fusiona resultados de ambas fuentes usando el mismo índice vectorial.

#### Endpoint `/classify`

```python
# app/api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Tariff RAG API", version="1.0.0")

class ClassifyRequest(BaseModel):
    query: str
    top_k: int = 5
    min_confidence: float = 0.5

class ClassifyResponse(BaseModel):
    code: str
    description: str
    confidence: float
    evidence: List[str]
    metadata: dict

@app.post("/classify", response_model=ClassifyResponse)
async def classify_endpoint(req: ClassifyRequest):
    """
    Clasifica un producto en el Sistema Armonizado (HS).
    
    Flujo:
    1. Búsqueda híbrida (semántica + léxica)
    2. Re-ranking con RRF
    3. Generación de código con LLM
    4. Búsqueda de evidencia adicional
    5. Validación de confianza
    """
    try:
        # 1. Retrieval
        os_client = get_os_client()
        index_name = get_settings().opensearch_index
        
        hits = hybrid_search_with_fallback(
            os_client=os_client,
            index=index_name,
            query_text=req.query,
            k=req.top_k
        )
        
        if not hits:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron fragmentos relevantes"
            )
        
        # 2. Re-ranking (opcional)
        hits = rerank_hits(hits, req.query)
        
        # 3. Generación con LLM
        result = generate_label(
            query=req.query,
            context=hits,
            min_confidence=req.min_confidence
        )
        
        # 4. Evidencia adicional para el código generado
        support_hits = retrieve_support_for_code(
            os_client=os_client,
            index_name=index_name,
            code=result.code,
            k=3
        )
        
        # 5. Construir respuesta
        evidence = [h["_source"]["text"] for h in hits[:3]]
        evidence.extend([s["text"] for s in support_hits])
        
        return ClassifyResponse(
            code=result.code,
            description=result.description,
            confidence=result.confidence,
            evidence=evidence,
            metadata={
                "num_hits": len(hits),
                "support_docs": len(support_hits),
                "strategy": "hybrid_with_llm"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in /classify: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

#### Búsqueda Híbrida

```python
# app/os_retrieval.py
def hybrid_search_with_fallback(
    os_client: OpenSearch,
    index: str,
    query_text: str,
    k: int = 5
) -> List[dict]:
    """
    Búsqueda híbrida con fallback automático.
    
    Estrategia:
    1. Intenta kNN semántico (embeddings)
    2. Si falla o vacío, usa BM25 léxico con boosts
    
    Returns:
        Lista de hits de OpenSearch con _score y _source
    """
    # Intento 1: kNN Semántico
    try:
        hits = knn_semantic_search(os_client, index, query_text, k)
        if hits and len(hits) >= 3:  # Umbral mínimo
            return hits
    except Exception as e:
        logger.warning(f"kNN search failed: {e}, falling back to BM25")
    
    # Fallback: BM25 con boosts de dominio
    return bm25_search(os_client, index, query_text, k)


def knn_semantic_search(
    os_client: OpenSearch,
    index: str,
    query_text: str,
    k: int = 5
) -> List[dict]:
    """
    Búsqueda semántica usando embeddings y kNN.
    
    OpenSearch query DSL:
    {
      "query": {
        "knn": {
          "embedding": {
            "vector": [0.1, 0.2, ...],  # 768 dims
            "k": 5
          }
        }
      }
    }
    """
    embedder = GeminiEmbedder()
    query_vector = embedder.embed_texts([query_text])[0]
    
    body = {
        "size": k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": k
                }
            }
        },
        "_source": [
            "fragment_id", "text", "bucket", "unit",
            "doc_id", "chapter", "heading", "subheading"
        ]
    }
    
    response = os_client.search(index=index, body=body)
    return response["hits"]["hits"]


def bm25_search(
    os_client: OpenSearch,
    index: str,
    query_text: str,
    k: int = 5
) -> List[dict]:
    """
    Búsqueda léxica BM25 con boosts a términos clave.
    
    Heurísticas:
    - Match phrase en códigos HS (boost 6.0)
    - Match en términos de dominio (boost 2.0)
    - Detección de códigos en query con regex
    """
    # Términos de dominio con boost
    domain_terms = [
        "neumático", "neumáticos", "llanta", "llantas",
        "caucho", "rubber", "pneumatic", "tyre", "tyres"
    ]
    
    should_clauses = [
        {"match": {"text": {"query": query_text, "boost": 3.0}}}
    ]
    
    # Agregar términos de dominio
    for term in domain_terms:
        should_clauses.append({
            "match": {"text": {"query": term, "boost": 2.0}}
        })
    
    # Detectar códigos HS en la query (ej: 4011.10)
    import re
    code_match = re.search(r"\b(\d{4})(?:\.(\d{2}))?(?:\.(\d{2}))?\b", query_text)
    if code_match:
        code = ".".join(filter(None, code_match.groups()))
        heading = code.split(".")[0]
        
        # Variantes del código
        variants = _generate_code_variants(code)
        for variant in variants:
            should_clauses.append({
                "match_phrase": {"text": {"query": variant, "boost": 6.0}}
            })
        
        # Boost al heading (4 dígitos)
        should_clauses.append({
            "match_phrase": {"text": {"query": heading, "boost": 4.0}}
        })
    
    body = {
        "size": k,
        "query": {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        "_source": [
            "fragment_id", "text", "bucket", "unit",
            "doc_id", "chapter", "heading", "subheading"
        ]
    }
    
    response = os_client.search(index=index, body=body)
    return response["hits"]["hits"]


def _generate_code_variants(code: str) -> List[str]:
    """
    Genera variantes de escritura de códigos HS.
    
    Input: "4011.10"
    Output: ["4011.10", "401110", "4011 10", "4011-10", ...]
    """
    no_dot = code.replace(".", "")
    with_space = code.replace(".", " ")
    with_dash = code.replace(".", "-")
    return list(set([code, no_dot, with_space, with_dash]))
```

#### Re-ranking con RRF

```python
# app/chain_rag.py
def rerank_hits(hits: List[dict], query: str) -> List[dict]:
    """
    Re-ranking usando Reciprocal Rank Fusion (RRF).
    
    Formula RRF: score = Σ 1 / (k + rank_i)
    donde k = 60 (constante estándar)
    
    Combina scores de múltiples retrieval strategies.
    """
    k = 60  # Constante de RRF
    
    for i, hit in enumerate(hits):
        rank = i + 1
        hit["_rrf_score"] = 1.0 / (k + rank)
        
        # Opcional: boost por coincidencia de keywords
        text_lower = hit["_source"]["text"].lower()
        keyword_boost = 0.0
        
        keywords = ["neumático", "caucho", "pneumatic", "tire"]
        for kw in keywords:
            if kw in text_lower:
                keyword_boost += 0.1
        
        hit["_rrf_score"] += keyword_boost
    
    # Ordenar por RRF score
    hits.sort(key=lambda x: x["_rrf_score"], reverse=True)
    return hits
```

#### Generación con LLM

```python
# app/generator_gemini.py
import google.generativeai as genai
from dataclasses import dataclass
import re

@dataclass
class ClassificationResult:
    code: str
    description: str
    confidence: float
    reasoning: str

def generate_label(
    query: str,
    context: List[dict],
    min_confidence: float = 0.5
) -> ClassificationResult:
    """
    Genera clasificación HS usando Gemini con contexto RAG.
    
    El contexto puede incluir:
    - Fragmentos de documentos normativos
    - Casos históricos de clasificación desde MySQL
    - Ambos tipos mezclados por relevancia
    """
    # Construir contexto distinguiendo fuentes
    context_text = ""
    for i, hit in enumerate(context[:5], 1):
        src = hit["_source"]
        score = hit.get("_score", 0)
        
        # Identificar fuente
        source_label = "📄 Normativa" if src.get("bucket") == "normativa" else "📊 Caso Histórico"
        
        context_text += f"\n[{source_label} {i}] (relevancia: {score:.2f})\n"
        context_text += f"{src['text']}\n"
        
        # Metadata específica de MySQL
        if src.get("source") == "mysql":
            if src.get("product_name"):
                context_text += f"  Producto: {src['product_name']}\n"
            if src.get("hs_code"):
                context_text += f"  Clasificado como: {src['hs_code']}\n"
            if src.get("confidence_score"):
                context_text += f"  Confianza previa: {src['confidence_score']:.2f}\n"
        
        # Metadata de documentos PDF
        if "chapter" in src and src["chapter"]:
            context_text += f"  Capítulo: {src['chapter']}\n"
        if "heading" in src and src["heading"]:
            context_text += f"  Partida: {src['heading']}\n"
    
    prompt = f"""Eres un experto en clasificación arancelaria según el Sistema Armonizado (HS).

Tu tarea es clasificar el siguiente producto en el código HS más específico posible.

CONTEXTO DISPONIBLE (normativa y casos históricos):
{context_text}

PRODUCTO A CLASIFICAR:
{query}

INSTRUCCIONES:
1. Analiza el producto y el contexto proporcionado
2. Considera tanto la normativa oficial como los casos históricos similares
3. Si hay casos históricos relevantes, úsalos como referencia pero valida contra la normativa
4. Identifica el capítulo, partida, subpartida y código completo
5. Explica tu razonamiento paso a paso
6. Proporciona un nivel de confianza (0-1)

FORMATO DE RESPUESTA (obligatorio):
CÓDIGO: XXXX.XX.XX.XX
DESCRIPCIÓN: [descripción técnica del producto]
CONFIANZA: [número entre 0 y 1]
RAZONAMIENTO: [justificación detallada citando los documentos]

RESPUESTA:"""

    # Llamada a Gemini
    model = genai.GenerativeModel("gemini-pro")
    
    generation_config = {
        "temperature": 0.3,  # Baja temperatura para mayor precisión
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 1024,
    }
    
    response = model.generate_content(
        prompt,
        generation_config=generation_config
    )
    
    # Parsear respuesta estructurada
    text = response.text
    
    code = _extract_field(text, "CÓDIGO:")
    description = _extract_field(text, "DESCRIPCIÓN:")
    confidence_str = _extract_field(text, "CONFIANZA:")
    reasoning = _extract_field(text, "RAZONAMIENTO:")
    
    # Validar y normalizar código
    code = _normalize_hs_code(code)
    
    # Parsear confianza
    try:
        confidence = float(confidence_str)
    except:
        confidence = 0.5
    
    # Validar confianza mínima
    if confidence < min_confidence:
        raise ValueError(
            f"Confianza {confidence:.2f} por debajo del mínimo {min_confidence}"
        )
    
    return ClassificationResult(
        code=code,
        description=description,
        confidence=confidence,
        reasoning=reasoning
    )


def _extract_field(text: str, field_name: str) -> str:
    """Extrae valor de un campo del formato estructurado."""
    pattern = f"{field_name}\\s*(.+?)(?=\\n[A-Z]+:|$)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _normalize_hs_code(code: str) -> str:
    """
    Normaliza código HS al formato estándar XXXX.XX.XX.XX
    
    Ejemplos:
    - "4011.10" -> "4011.10.00.00"
    - "401110" -> "4011.10.00.00"
    - "4011 10" -> "4011.10.00.00"
    """
    # Remover espacios y caracteres no numéricos excepto puntos
    clean = re.sub(r"[^\d.]", "", code)
    
    # Extraer dígitos
    digits = re.findall(r"\d+", clean)
    if not digits:
        return "0000.00.00.00"
    
    # Reconstruir en formato estándar
    parts = "".join(digits)
    
    if len(parts) < 4:
        parts = parts.ljust(4, "0")
    
    # Formato: XXXX.XX.XX.XX
    formatted = f"{parts[:4]}.{parts[4:6] if len(parts)>4 else '00'}"
    formatted += f".{parts[6:8] if len(parts)>6 else '00'}"
    formatted += f".{parts[8:10] if len(parts)>8 else '00'}"
    
    return formatted
```

---

## Módulos del Backend

### Estructura de Directorios

```
d:\MAESTRIA\tariff-rag/
├── app/
│   ├── __init__.py
│   ├── api.py                    # Endpoints FastAPI
│   ├── config.py                 # Configuración (Pydantic Settings)
│   ├── metrics.py                # Prometheus metrics
│   │
│   ├── os_index.py               # Cliente OpenSearch
│   ├── os_retrieval.py           # Búsqueda híbrida
│   ├── os_ingest.py              # Indexación bulk
│   │
│   ├── embedder_gemini.py        # Generación de embeddings
│   ├── generator_gemini.py       # Generación con LLM
│   ├── chain_rag.py              # Orquestación RAG
│   │
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── base.py               # Interfaces abstractas
│   │   ├── azure_provider.py    # Azure Form Recognizer
│   │   └── tesseract_provider.py # Tesseract OCR
│   │
│   └── etl_mysql.py              # ⭐ ETL desde MySQL (FUENTE)
│
├── scripts/
│   ├── init_opensearch.py        # Crear índice
│   ├── ingest_pdf.py             # Ingestar PDF
│   ├── ingest_mysql.py           # ⭐ Ingestar desde MySQL
│   ├── ingest_jsonl.py           # ⭐ Ingestar desde archivos JSONL
│   ├── chunk_and_index.py        # Fragmentación e indexación
│   ├── sync_all.py               # Sincronizar todas las fuentes
│   └── evaluate.py               # Evaluación de métricas
│
├── ui/
│   └── gradio_app.py             # Interfaz Gradio
│
├── tests/
│   ├── test_retrieval.py
│   ├── test_generation.py
│   ├── test_etl_mysql.py         # Tests de ETL
│   └── test_e2e.py
│
├── data/                         # Documentos fuente (PDFs)
├── storage/                      # Datos persistentes
│   └── os/                       # OpenSearch data
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── requirements.ui.txt
├── .env
└── README.md
```

### Script de Ingesta desde MySQL

```python
# scripts/ingest_mysql.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.etl_mysql import extract_mysql_fragments
from app.os_ingest import bulk_ingest_fragments
from app.config import get_settings

def main():
    """
    Script para ingestar datos desde MySQL hacia OpenSearch.
    
    Variables de entorno opcionales:
    - MYSQL_TABLE: tabla a procesar (default: product_cases)
    - MYSQL_TEXT_COL: columna con texto (default: description)
    - MYSQL_ID_COL: columna ID (default: id)
    
    Uso:
        docker exec rag-api python scripts/ingest_mysql.py
        
    O con variables:
        docker exec -e MYSQL_TABLE=customs_rulings rag-api python scripts/ingest_mysql.py
    """
    s = get_settings()
    table = os.environ.get("MYSQL_TABLE", "product_cases")
    text_col = os.environ.get("MYSQL_TEXT_COL", "description")
    id_col = os.environ.get("MYSQL_ID_COL", "id")
    
    print(f"📥 Extrayendo desde MySQL: {table}.{text_col}")
    
    fragments = extract_mysql_fragments(table, text_col, id_col)
    
    if fragments:
        print(f"✨ Generando embeddings para {len(fragments)} fragmentos...")
        fragments_dict = [f.model_dump() for f in fragments]
        bulk_ingest_fragments(fragments_dict, s.opensearch_index)
        print(f"✅ Ingestados {len(fragments)} fragmentos desde MySQL → OpenSearch")
    else:
        print("ℹ️ No se encontraron registros con texto en la tabla especificada")

if __name__ == "__main__":
    main()
```

### Script de Ingesta desde JSONL

```python
# scripts/ingest_jsonl.py
import json
from pathlib import Path

def ingest_jsonl(file_path: str, text_field: str = "text", bucket: str = "jsonl_import"):
    """
    Procesa e indexa un archivo JSONL.
    
    Formato esperado:
    {"text": "Neumáticos radiales...", "hs_code": "4011.10", "product_name": "..."}    
    """
    from app.os_ingest import bulk_ingest_fragments
    from app.embedder_gemini import GeminiEmbedder
    
    embedder = GeminiEmbedder()
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            
            # Cargar objeto JSON
            obj = json.loads(line)
            
            # Mapeo básico
            text = obj.get(text_field, "")
            hs_code = obj.get("hs_code", "").strip()
            product_name = obj.get("product_name", "").strip()
            
            # Filtrar por tamaño mínimo
            if len(text) < 20:
                continue
            
            # Generar embedding
            embedding = embedder.embed_texts([text])[0]
            
            # Documento para indexar
            doc = {
                "_index": "tariff_fragments",
                "_source": {
                    "text": text,
                    "embedding": embedding,
                    "fragment_id": obj.get("id"),
                    "bucket": bucket,
                    "source": obj.get("metadata", {}).get("source", ""),
                    "doc_id": obj.get("metadata", {}).get("doc_id", ""),
                    "page": obj.get("metadata", {}).get("page_num", 1),
                    "role": obj.get("metadata", {}).get("role", ""),
                    "kind": obj.get("metadata", {}).get("kind", ""),
                    "indexed_at": datetime.utcnow().isoformat()
                }
            }
            
            # Indexar documento
            bulk_ingest_fragments([doc], "tariff_fragments")
            print(f"✅ Ingestado fragmento: {obj.get('id')}")
```

### Ingesta desde JSONL (mapeo y filtros)

- Mapeo de campos:
  - id → fragment_id
  - text → text
  - metadata.doc_id → doc_id
  - metadata.source → source (archivo original)
  - metadata.page_num → page
  - metadata.role → role (p.ej. pageHeader, paragraph)
  - metadata.kind → kind (p.ej. paragraph)
  - Se preserva metadata completa en _source.metadata; bucket=jsonl_import

- Filtros:
  - --include-types text table figure
  - --include-roles paragraph heading
  - --exclude-roles pageHeader pageFooter  (default)
  - --min-chars 20

Ejemplo (entrada JSONL):
{"id":"9483d9ca7628f38a_p0","type":"text","text":"VICEMINISTERIO DE POLÍTICA TRIBUTARIA","metadata":{"doc_id":"9483d9ca7628f38a","source":"Arancel_Boliviano_Parte_5.pdf","apiVersion":"2024-11-30","modelId":"prebuilt-layout","role":"pageHeader","page_num":1,"index":0,"span":{"offset":0,"length":37},"kind":"paragraph"}}

Comando:
docker exec rag-api python scripts/ingest_jsonl.py data/archivo.jsonl --exclude-roles pageHeader pageFooter --bucket normativa_jsonl
```
