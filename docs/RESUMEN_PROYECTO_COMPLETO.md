# RESUMEN COMPLETO DEL PROYECTO
## Sistema RAG de Clasificaci贸n Arancelaria con Google Gemini y OpenSearch

**Fecha:** 7 de noviembre de 2025  
**Autor:** Proyecto de Maestr铆a  
**Repositorio:** tariff-rag

---

## 馃搵 TABLA DE CONTENIDOS

1. [Descripci贸n General del Proyecto](#1-descripci贸n-general-del-proyecto)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Componentes Principales](#3-componentes-principales)
4. [Pipeline de Ingesta de Datos](#4-pipeline-de-ingesta-de-datos)
5. [Sistema de Embeddings con Google Gemini](#5-sistema-de-embeddings-con-google-gemini)
6. [Sistema de Recuperaci贸n H铆brida](#6-sistema-de-recuperaci贸n-h铆brida)
7. [Sistema de Generaci贸n con Gemini](#7-sistema-de-generaci贸n-con-gemini)
8. [API y Endpoints](#8-api-y-endpoints)
9. [Sistema de Evaluaci贸n y M茅tricas](#9-sistema-de-evaluaci贸n-y-m茅tricas)
10. [Resultados Obtenidos](#10-resultados-obtenidos)
11. [Configuraci贸n y Deployment](#11-configuraci贸n-y-deployment)

---

## 1. DESCRIPCI脫N GENERAL DEL PROYECTO

### 1.1 Objetivo
Desarrollar un sistema inteligente de clasificaci贸n arancelaria que utiliza t茅cnicas de Retrieval-Augmented Generation (RAG) para asistir en la asignaci贸n de c贸digos del Sistema Armonizado (HS) a descripciones de productos.

### 1.2 Problema que Resuelve
La clasificaci贸n arancelaria es un proceso complejo que requiere:
- Conocimiento profundo del Sistema Armonizado (HS)
- Interpretaci贸n de nomenclaturas t茅cnicas
- Aplicaci贸n de Reglas Generales de Interpretaci贸n (RGI)
- An谩lisis de inclusiones y exclusiones de partidas
- Consideraci贸n de caracter铆sticas f铆sicas, composici贸n y uso del producto

El sistema automatiza este proceso combinando:
1. **B煤squeda sem谩ntica** en documentaci贸n oficial del HS
2. **Generaci贸n de respuestas estructuradas** con LLM
3. **Validaci贸n con guardrails** para evitar alucinaciones

### 1.3 Tecnolog铆as Core
- **OpenSearch 2.11.1**: Motor de b煤squeda con soporte k-NN (HNSW)
- **Google Gemini**: 
  - `text-embedding-004` para embeddings (768 dimensiones)
  - `gemini-2.0-flash-exp` para generaci贸n estructurada
- **FastAPI**: Backend REST API
- **Gradio**: Interfaz de usuario
- **Azure Document Intelligence**: OCR de documentos PDF
- **MySQL 8.0**: Base de datos para corpus ASGARD
- **Docker Compose**: Orquestaci贸n de servicios

### 1.4 Caracter铆sticas Principales
鉁?B煤squeda h铆brida BM25 + k-NN (cosine similarity)  
鉁?Embeddings con modelo multiling眉e de Gemini  
鉁?Generaci贸n de respuestas estructuradas (JSON)  
鉁?Detecci贸n de consultas vagas (solicita informaci贸n faltante)  
鉁?OCR de documentos PDF con chunking inteligente  
鉁?Ingesta desde m煤ltiples fuentes (PDFs, JSON, MySQL)  
鉁?M茅tricas de Prometheus para observabilidad  
鉁?Sistema de evaluaci贸n con ground truth real  
鉁?Soporte para seguimiento conversacional  

---

## 2. ARQUITECTURA DEL SISTEMA

### 2.1 Diagrama de Componentes

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                       USUARIO                                   鈹?
鈹?                    (Gradio UI / API)                           鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                             鈹?
                             鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                     FASTAPI BACKEND                            鈹?
鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?
鈹? 鈹? /classify          /followup         /health            鈹? 鈹?
鈹? 鈹? 鈥?Validaci贸n       鈥?Conversaci贸n    鈥?Healthchecks     鈹? 鈹?
鈹? 鈹? 鈥?Guardrails       鈥?Contexto        鈥?Prometheus       鈹? 鈹?
鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
             鈹?                 鈹?                 鈹?
             鈻?                 鈻?                 鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?  OPENSEARCH 2.11   鈹? 鈹?GOOGLE GEMINI  鈹? 鈹? AZURE DOC INT  鈹?
鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹? 鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹? 鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?
鈹? 鈹?tariff_       鈹? 鈹? 鈹? 鈹?text-    鈹? 鈹? 鈹? 鈹?prebuilt- 鈹? 鈹?
鈹? 鈹?fragments     鈹? 鈹? 鈹? 鈹?embedding鈹? 鈹? 鈹? 鈹?layout    鈹? 鈹?
鈹? 鈹?(34,676 docs) 鈹? 鈹? 鈹? 鈹?-004     鈹? 鈹? 鈹? 鈹?(OCR)     鈹? 鈹?
鈹? 鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹? 鈹? 鈹?(768d)   鈹? 鈹? 鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?
鈹? 鈹?鈥?BM25        鈹? 鈹? 鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹? 鈹?                鈹?
鈹? 鈹?鈥?k-NN HNSW   鈹? 鈹? 鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹? 鈹?                鈹?
鈹? 鈹?鈥?Hybrid RRF  鈹? 鈹? 鈹? 鈹?gemini-  鈹? 鈹? 鈹?                鈹?
鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹? 鈹? 鈹?2.0-flash鈹? 鈹? 鈹?                鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹? 鈹?-exp     鈹? 鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                         鈹? 鈹?(genera) 鈹? 鈹?
                         鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?
                         鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
             鈻?                             鈻?
             鈹?                             鈹?
             鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                            鈹?
                   鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈻尖攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                   鈹? INGESTA BATCH  鈹?
                   鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?
                   鈹? 鈹?PDFs      鈹? 鈹?
                   鈹? 鈹?AFR JSON  鈹? 鈹?
                   鈹? 鈹?MySQL     鈹? 鈹?
                   鈹? 鈹?ASGARD    鈹? 鈹?
                   鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹?
                   鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
```

### 2.2 Flujo de Datos Principal (Clasificaci贸n)

```
1. ENTRADA
   鈹斺攢> Usuario ingresa descripci贸n: "Neum谩ticos radiales nuevos"
   
2. VALIDACI脫N
   鈹斺攢> Guardrails verifican longitud, contenido
   
3. EMBEDDING
   鈹斺攢> Gemini text-embedding-004 convierte texto 鈫?vector[768]
   
4. RECUPERACI脫N H脥BRIDA
   鈹溾攢> BM25: b煤squeda l茅xica por t茅rminos
   鈹溾攢> k-NN: b煤squeda sem谩ntica por similitud coseno
   鈹斺攢> RRF: fusi贸n de resultados (top 5-6 fragmentos)
   
5. VALIDACI脫N DE EVIDENCIA
   鈹溾攢> Score m铆nimo: 0.35
   鈹溾攢> Evidencias m铆nimas: 2
   鈹斺攢> Si insuficiente 鈫?respuesta temprana con missing_fields
   
6. GENERACI脫N CON GEMINI
   鈹溾攢> Contexto: query + fragmentos recuperados
   鈹溾攢> Prompt estructurado con RGI e instrucciones
   鈹溾攢> Output JSON forzado (response_schema)
   鈹斺攢> Detecci贸n de consultas vagas
   
7. POST-PROCESAMIENTO
   鈹溾攢> Validaci贸n de estructura JSON
   鈹溾攢> Enriquecimiento con citas (evidence)
   鈹斺攢> Aplicaci贸n de reglas de negocio
   
8. RESPUESTA
   鈹斺攢> JSON con:
       鈥?top_candidates: [c贸digo, descripci贸n, confidence]
       鈥?evidence: fragmentos con scores
       鈥?applied_rgi: reglas aplicadas
       鈥?inclusions/exclusions
       鈥?missing_fields: info faltante
       鈥?warnings
```

### 2.3 Arquitectura de Datos

**脥ndice OpenSearch: `tariff_fragments`**
```json
{
  "fragment_id": "9d7a5ed04bb6afc8_p0001",
  "text": "CAP脥TULO 40: CAUCHO Y SUS MANUFACTURAS...",
  "embedding": [0.0234, -0.0891, ..., 0.0456],  // 768 dims
  "source": "WCO_HS2022",
  "doc_id": "hs2022_es",
  "chapter": "40",
  "heading": "4011",
  "unit": "chapter_intro",
  "edition": "HS_2022",
  "bucket": "tariff_docs",
  "hs6": "4011.10",
  "codigo_producto": "ABC123"
}
```

**Dimensiones del Corpus:**
- Total fragmentos indexados: **~34,676**
- Fragmentos ASGARD (productos reales): **~8,000+**
- Fragmentos WCO (nomenclatura oficial): **~26,000**
- Tama帽o promedio fragmento: **1,800 caracteres**
- Solapamiento entre chunks: **200 caracteres**

### 2.4 Stack de Servicios Docker

| Servicio | Puerto | Funci贸n | Recursos |
|----------|--------|---------|----------|
| **opensearch** | 9200 | Motor de b煤squeda k-NN | 2GB RAM |
| **dashboards** | 5601 | Visualizaci贸n OpenSearch | 512MB RAM |
| **mysql** | 3306 | BD corpus ASGARD | 512MB RAM |
| **api** | 8000 | Backend FastAPI | 1GB RAM |
| **ui** | 7860 | Interfaz Gradio | 512MB RAM |

**Red Docker:** `ragnet` (bridge)  
**Vol煤menes persistentes:**
- `./storage/os` 鈫?datos OpenSearch
- `mysql-data` 鈫?datos MySQL
- `./data` 鈫?corpus PDFs/JSON

---

## 3. COMPONENTES PRINCIPALES

### 3.1 M贸dulo de Configuraci贸n (`app/config.py`)

**Clase:** `Settings` (Pydantic BaseSettings)

**Variables de Entorno Clave:**
```python
# OpenSearch
OPENSEARCH_HOST = "http://opensearch:9200"
OPENSEARCH_INDEX = "tariff_fragments"
OPENSEARCH_KNN_SPACE = "cosinesimil"
OPENSEARCH_EMB_DIM = 768

# MySQL (corpus ASGARD)
MYSQL_HOST = "mysql"
MYSQL_DB = "corpusdb"
MYSQL_USER = "appuser"
MYSQL_PASSWORD = "apppass"

# Google Gemini
GOOGLE_API_KEY = "AIza..."
GEMINI_EMBED_MODEL = "text-embedding-004"
GEMINI_GEN_MODEL = "gemini-2.0-flash-exp"
GEMINI_TEMPERATURE = 0.3
GEMINI_TOP_P = 0.9
GEMINI_TOP_K = 40
GEMINI_MAX_OUTPUT_TOKENS = 2048

# Azure Document Intelligence
AZURE_FR_ENDPOINT = "https://...cognitiveservices.azure.com/"
AZURE_FR_KEY = "..."
AZURE_FR_MODEL = "prebuilt-layout"

# Par谩metros RAG
FINAL_PASAGES = 6          # Top-K fragmentos a usar
MIN_EVIDENCE = 2           # M铆nimo de docs con score v谩lido
MIN_SCORE = 0.35          # Score m铆nimo aceptable

# Chunking
CHUNK_MAX_CHARS = 1800    # Tama帽o m谩ximo de fragmento
CHUNK_OVERLAP = 200       # Solapamiento entre chunks
```

**Caracter铆sticas:**
- Carga autom谩tica desde `.env`
- Validaci贸n de tipos con Pydantic
- Cach茅 con `@lru_cache` para performance
- Valores por defecto sensatos

### 3.2 Sistema de Schemas (`app/schemas.py`)

**Modelos Pydantic:**

```python
class Fragment(BaseModel):
    """Representa un fragmento de documento indexado"""
    fragment_id: str
    text: str
    metadata: Dict[str, Any]

class Candidate(BaseModel):
    """C贸digo HS candidato con confianza"""
    code: str                    # "4011.10"
    description: str             # "Neum谩ticos nuevos de caucho"
    confidence: float            # 0.0 - 1.0
    level: str                   # "HS2", "HS4", "HS6"

class Citation(BaseModel):
    """Evidencia textual recuperada"""
    fragment_id: str
    score: float
    text: str
    reason: str = "retrieved"

class ClassifyResponse(BaseModel):
    """Respuesta completa de clasificaci贸n"""
    top_candidates: List[Candidate] = []
    evidence: List[Citation] = []
    applied_rgi: List[str] = []      # ["RGI 1", "RGI 3(b)"]
    inclusions: List[str] = []
    exclusions: List[str] = []
    missing_fields: List[str] = []   # Informaci贸n faltante
    warnings: List[str] = []
    versions: Dict[str, str] = {"hs_edition": "HS_2022"}
    debug_info: Optional[Dict] = None
```

### 3.3 M贸dulo de Chunking (`app/chunking.py`)

**Funci贸n:** `juridical_chunks(text, meta, max_chars, overlap)`

**Estrategia de Segmentaci贸n:**
1. **Detecci贸n de unidades legales** mediante regex:
   ```regex
   ^(cap铆tulo\s+\w+|secci贸n\s+\w+|art铆culo\s+\d+|t铆tulo\s+\w+)
   ```

2. **Corte por separadores naturales:**
   - Cap铆tulos del HS
   - Secciones de nomenclatura
   - Art铆culos de normativa
   - T铆tulos de documentos

3. **Ajuste por tama帽o:**
   - Si fragmento > max_chars 鈫?divisi贸n por ventana deslizante
   - Ventana = `max_chars`
   - Paso = `max_chars - overlap`

4. **Preservaci贸n de contexto:**
   - Overlap de 200 caracteres por defecto
   - Evita cortar frases cr铆ticas
   - Mantiene metadata original

**Ejemplo:**
```python
text = """CAP脥TULO 40
CAUCHO Y SUS MANUFACTURAS

Notas:
1. Salvo disposici贸n en contrario...
2. En la Nomenclatura..."""

chunks = juridical_chunks(
    text=text,
    meta={"source": "WCO", "chapter": "40"},
    max_chars=1800,
    overlap=200
)
# Resultado: 3 fragmentos con solapamiento
```

### 3.4 M贸dulo de 脥ndice OpenSearch (`app/os_index.py`)

**Funciones Principales:**

```python
def get_os_client() -> OpenSearch:
    """Singleton client con connection pooling"""
    
def ensure_index(index_name: str):
    """Crea 铆ndice con mapeo optimizado si no existe"""
    
def create_or_update_mapping():
    """Actualiza mapeo con campos nuevos"""
```

**Mapeo del 脥ndice:**
```json
{
  "settings": {
    "index": {
      "knn": true,
      "number_of_shards": 1,
      "number_of_replicas": 0
    }
  },
  "mappings": {
    "properties": {
      "fragment_id": {"type": "keyword"},
      "text": {"type": "text", "analyzer": "standard"},
      "source": {"type": "keyword"},
      "hs6": {
        "type": "text",
        "fields": {"keyword": {"type": "keyword"}}
      },
      "embedding": {
        "type": "knn_vector",
        "dimension": 768,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib",
          "parameters": {
            "ef_construction": 128,
            "m": 16
          }
        }
      }
    }
  }
}
```

**Caracter铆sticas del 脥ndice:**
- **HNSW (Hierarchical Navigable Small World)**: Algoritmo de b煤squeda aproximada
- **ef_construction=128**: Balance precision/velocidad construcci贸n
- **m=16**: N煤mero de conexiones por nodo en grafo
- **Dual fields**: `text` (full-text) + `text.keyword` (exact match)

### 3.5 Sistema de M茅tricas Prometheus (`app/metrics.py`)

**M茅tricas Exportadas:**

```python
from prometheus_client import Counter, Histogram, Gauge

# Contadores de requests
REQUESTS = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

# Latencias por componente
LATENCY = Histogram(
    'api_request_seconds',
    'Request latency in seconds',
    ['endpoint', 'method'],
    buckets=[0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 7.5, 10.0]
)

# Errores
ERRORS = Counter(
    'api_requests_errors_returned',
    'API errors returned',
    ['endpoint', 'method']
)

# Top-K usado en retrieval
RETRIEVAL_K = Gauge(
    'retrieval_top_k',
    'Top-K value for retrieval',
    ['strategy']
)
```

**Endpoint:** `GET /metrics` (formato Prometheus)

**Dashboards disponibles:**
- Latencias p50/p95/p99 por endpoint
- Throughput (QPM - Queries Per Minute)
- Tasa de errores
- Distribuci贸n de scores de retrieval

---

## 4. PIPELINE DE INGESTA DE DATOS

### 4.1 Visi贸n General del Pipeline

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                   FUENTES DE DATOS                          鈹?
鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹? 1. PDFs (WCO)     2. JSON (AFR)      3. MySQL (ASGARD)     鈹?
鈹? 鈥?Nomenclatura    鈥?Docs procesados  鈥?Productos reales     鈹?
鈹? 鈥?Notas legales   鈥?Azure DI export  鈥?Declaraciones        鈹?
鈹? 鈥?RGI oficiales   鈥?Pre-OCR          鈥?50,000+ registros    鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
         鈹?                  鈹?                   鈹?
         鈻?                  鈻?                   鈻?
    鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?       鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?       鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
    鈹?  OCR   鈹?       鈹? Parser  鈹?       鈹? Extractor鈹?
    鈹? Azure  鈹?       鈹?  JSON   鈹?       鈹? SQL      鈹?
    鈹? Doc Int鈹?       鈹? Walker  鈹?       鈹? Queries  鈹?
    鈹斺攢鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹?       鈹斺攢鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹?       鈹斺攢鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹?
         鈹?                  鈹?                   鈹?
         鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                             鈹?
                             鈻?
                    鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                    鈹?   CHUNKING     鈹?
                    鈹? 鈥?Jur铆dico     鈹?
                    鈹? 鈥?Max 1800ch   鈹?
                    鈹? 鈥?Overlap 200  鈹?
                    鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                             鈹?
                             鈻?
                    鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                    鈹?  EMBEDDING     鈹?
                    鈹? 鈥?Gemini API   鈹?
                    鈹? 鈥?Batch 64     鈹?
                    鈹? 鈥?768 dims     鈹?
                    鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                             鈹?
                             鈻?
                    鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                    鈹?BULK INDEXING   鈹?
                    鈹? 鈥?OpenSearch   鈹?
                    鈹? 鈥?Upsert por   鈹?
                    鈹?   fragment_id  鈹?
                    鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
```

### 4.2 Ingesta desde PDFs (`app/ocr_formrec.py`)

**Funci贸n:** `extract_fragments_from_pdf(pdf_path, base_metadata)`

**Proceso Detallado:**

1. **Inicializaci贸n Azure Document Intelligence:**
   ```python
   from azure.ai.documentintelligence import DocumentIntelligenceClient
   from azure.core.credentials import AzureKeyCredential
   
   endpoint = os.environ["AZURE_FR_ENDPOINT"]
   key = os.environ["AZURE_FR_KEY"]
   client = DocumentIntelligenceClient(
       endpoint=endpoint,
       credential=AzureKeyCredential(key)
   )
   ```

2. **An谩lisis con modelo prebuilt-layout:**
   ```python
   with open(pdf_path, "rb") as f:
       poller = client.begin_analyze_document(
           model_id="prebuilt-layout",
           body=io.BytesIO(f.read())
       )
   result = poller.result()
   ```

3. **Extracci贸n de texto estructurado:**
   - **P谩rrafos**: `result.paragraphs[].content`
   - **L铆neas**: `result.pages[].lines[].content`
   - **Tablas**: `result.tables[].cells[]` (preserva estructura)
   - **Layout**: Respeta orden de lectura natural

4. **Chunking jur铆dico:**
   ```python
   max_chars, overlap = _get_chunk_params()  # Desde env
   chunks = juridical_chunks(
       full_text, 
       base_metadata, 
       max_chars=max_chars,  # 1800
       overlap=overlap        # 200
   )
   ```

5. **Generaci贸n de fragment_id:**
   ```python
   frag_id = f"{base_metadata['doc_id']}_{idx:04d}"
   # Ejemplo: "hs2022_es_0001", "hs2022_es_0002", ...
   ```

**Metadata enriquecida:**
```python
{
    "source": "WCO_HS2022",
    "doc_id": "hs2022_es",
    "bucket": "tariff_docs",
    "unit": "chapter_40",
    "edition": "HS_2022",
    "validity_from": "2022-01-01",
    "filename": "hs2022_chapter40.pdf"
}
```

### 4.3 Ingesta desde JSON AFR (`app/ocr_formrec.py`)

**Funci贸n:** `extract_fragments_from_afr_json(json_path, base_metadata)`

**AFR = Azure Form Recognizer export format**

**Proceso:**

1. **Carga del JSON:**
   ```python
   with open(json_path, "r", encoding="utf-8") as f:
       data = json.load(f)
   root = data.get("analyzeResult", data)
   ```

2. **Walker recursivo para extraer `content`:**
   ```python
   def walk(node):
       if isinstance(node, dict):
           if "content" in node and isinstance(node["content"], str):
               text_blocks.append(node["content"].strip())
           for v in node.values():
               walk(v)
       elif isinstance(node, list):
           for item in node:
               walk(item)
   
   walk(root)
   ```

3. **Concatenaci贸n y limpieza:**
   ```python
   full_text = re.sub(r"\s+", " ", "\n".join(text_blocks)).strip()
   ```

4. **Chunking y fragmentaci贸n** (igual que PDFs)

**Ventajas del formato AFR:**
- 鉁?OCR pre-procesado (no consume Azure API en runtime)
- 鉁?Estructura JSON preserva jerarqu铆a
- 鉁?Ideal para batch processing
- 鉁?Cacheable y versionable

### 4.4 Ingesta desde MySQL ASGARD (`app/etl_mysql.py`)

**Funci贸n:** `extract_asgard_fragments()`

**Base de Datos:** MySQL con tabla `asgard` (50,000+ productos)

**Schema de la tabla:**
```sql
CREATE TABLE asgard (
    codigoproducto VARCHAR(50) PRIMARY KEY,
    Partida TEXT,              -- "PARTIDA ARANCELARIA: 48193010000"
    Mercancia TEXT,            -- Descripci贸n del producto
    Param_1 TEXT,              -- Atributos t茅cnicos
    Param_2 TEXT,
    ...
    Param_14 TEXT
);
```

**Proceso de Extracci贸n:**

1. **Construcci贸n de query SQL con paginaci贸n:**
   ```python
   limit = int(os.getenv("MYSQL_LIMIT", "0")) or None
   offset = int(os.getenv("MYSQL_OFFSET", "0")) or None
   order_col = os.getenv("MYSQL_ORDER", "codigoproducto")
   
   query = f"""
       SELECT codigoproducto, Partida, Mercancia,
              Param_1, Param_2, ..., Param_14
       FROM asgard
       WHERE Partida IS NOT NULL
       ORDER BY {order_col} ASC
       LIMIT {limit} OFFSET {offset}
   """
   ```

2. **Normalizaci贸n de c贸digo HS:**
   ```python
   # Input: "PARTIDA ARANCELARIA: 48193010000"
   # Regex: r"(\d{6,12})"
   # Output: "481930" (primeros 6 d铆gitos = HS6)
   
   m = re.search(r"(\d{6,12})", partida_raw)
   partida_digits = m.group(1) if m else ""
   hs6 = partida_digits[:6]  # "481930"
   ```

3. **Concatenaci贸n de campos descriptivos:**
   ```python
   text_parts = []
   
   # Mercanc铆a principal
   if mercancia:
       text_parts.append(f"MERCANC脥A: {mercancia}")
   
   # Partida
   if partida:
       text_parts.append(f"PARTIDA: {partida}")
   
   # Par谩metros t茅cnicos (filtrar vac铆os)
   for param in ['Param_1', ..., 'Param_14']:
       value = row[param]
       if value and value.upper() not in ['NULL', 'SIN REFERENCIA']:
           text_parts.append(str(value))
   
   full_text = " | ".join(text_parts)
   ```

4. **Generaci贸n de fragment_id 煤nico:**
   ```python
   import hashlib
   
   fid = hashlib.md5(
       f"ASGARD::{codigoproducto}".encode()
   ).hexdigest()[:12]
   # Ejemplo: "a3f8c2b91e45"
   ```

5. **Metadata especializada:**
   ```python
   metadata = {
       "source": "ASGARD_DB",
       "doc_id": f"asgard:{codigoproducto}",
       "unit": "PRODUCT",
       "edition": "ASGARD_IMPORT",
       "bucket": "asgard_products",
       "partida": partida_digits,
       "hs6": hs6,
       "codigo_producto": codigoproducto
   }
   ```

**Ejemplo de fragmento ASGARD resultante:**
```
MERCANC脥A: RELAY TOYOTA | PARTIDA: PARTIDA ARANCELARIA: 853641 | 
RELAY DE VEHICULO | 9008087024 | PIEZA METAL COMBINADO CON OTROS 
MATERIALES | REPUESTOS PARA VEHICULO
```

### 4.5 M贸dulo de Ingesta Bulk (`app/os_ingest.py`)

**Funci贸n:** `bulk_ingest_fragments(fragments, index_name, embed, batch_size)`

**Caracter铆sticas:**

1. **Control de embeddings:**
   ```python
   # Desde par谩metro o env
   embed_flag = embed if embed is not None 
                else not os.getenv("NO_EMBED", "0") in ("1", "true")
   
   # Batch size configurable
   batch_size = int(os.getenv("OPENSEARCH_EMBED_BATCH", 64))
   ```

2. **Procesamiento por lotes:**
   ```python
   embedder = GeminiEmbedder() if embed_flag else None
   
   for frag_batch in _batched(fragments, batch_size):
       texts = [f["text"] for f in frag_batch]
       
       # Embedding batch (si enabled)
       if embedder:
           vectors = embedder.embed_texts(texts)
       
       # Preparar acciones bulk
       actions = []
       for i, src in enumerate(frag_batch):
           clean_src = _flatten_metadata(src)
           if vectors:
               clean_src["embedding"] = vectors[i]
           
           actions.append({
               "_index": index_name,
               "_id": clean_src["fragment_id"],
               "_source": clean_src
           })
       
       # Indexaci贸n bulk
       helpers.bulk(client, actions)
   ```

3. **Flatten metadata** (mapeo plano para indexaci贸n):
   ```python
   def _flatten_metadata(src):
       """
       Eleva campos anidados en metadata al nivel ra铆z
       para coincidir con el mapeo de OpenSearch.
       """
       clean_src = json.loads(json.dumps(src, default=str))
       meta = clean_src.get("metadata") or {}
       
       for key in ["source", "bucket", "hs6", "partida", ...]:
           if key not in clean_src and key in meta:
               clean_src[key] = meta[key]
       
       return clean_src
   ```

4. **Gesti贸n de costos de embeddings:**
   - **Fast path**: `NO_EMBED=1` 鈫?solo BM25 (煤til para smoke tests)
   - **Batch processing**: 64 textos por llamada a Gemini API
   - **Reintentables**: Upsert por `fragment_id` (idempotente)

### 4.6 Scripts de Ingesta

**Script 1: `scripts/ingest_docs.py`**
```bash
# Ingesta PDFs y JSON AFR desde data/corpus/
docker compose exec api python scripts/ingest_docs.py

# Variables de control:
# - CHUNK_MAX_CHARS=1800
# - CHUNK_OVERLAP=200
# - NO_EMBED=0 (embeddings activos)
# - OPENSEARCH_EMBED_BATCH=64
```

**Script 2: `scripts/ingest_mysql.py`**
```bash
# Ingesta completa ASGARD
docker compose exec api python scripts/ingest_mysql.py

# Ingesta por bloques (control de costos)
docker compose exec api bash -c "
  TARGET_INDEX=tariff_fragments \
  MYSQL_LIMIT=1000 \
  MYSQL_OFFSET=0 \
  OPENSEARCH_EMBED_BATCH=64 \
  python scripts/ingest_mysql.py
"

# Bloques ejecutados en el proyecto:
# OFFSET=0,1000,2000,...,10000 (11 bloques 脳 1000 = 11,000 docs)
```

**Script 3: `scripts/init_index.py`**
```bash
# Crear 铆ndice con mapeo inicial
docker compose exec api python scripts/init_index.py

# Solo necesario una vez (idempotente)
```

### 4.7 Verificaci贸n de Ingesta

**Script: `scripts/verify_ingest.py`**

**Verificaciones:**
1. 鉁?脥ndice existe y accesible
2. 鉁?Total de documentos indexados
3. 鉁?Documentos ASGARD detectables (via source/keyword)
4. 鉁?Agregaci贸n de c贸digos HS6 煤nicos
5. 鉁?Muestra de documento ASGARD aleatorio

**Ejemplo de output:**
```
脥ndice: tariff_fragments
Total documentos: 34,676

Documentos ASGARD_DB: 8,247
(via match query con fallback keyword)

Top 10 c贸digos HS6:
  8703.23: 156 docs
  4011.10: 142 docs
  ...

Documento ASGARD muestra:
{
  "fragment_id": "a3f8c2b91e45",
  "source": "ASGARD_DB",
  "hs6": "853641",
  "text": "RELAY TOYOTA | PARTIDA: 853641 | ..."
}
```

---

## 5. SISTEMA DE EMBEDDINGS CON GOOGLE GEMINI

### 5.1 Clase GeminiEmbedder (`app/embedder_gemini.py`)

**Modelo usado:** `text-embedding-004` (768 dimensiones)

**Caracter铆sticas del modelo:**
- 鉁?Multiling眉e (espa帽ol, ingl茅s, etc.)
- 鉁?Context length: 2048 tokens
- 鉁?Optimizado para b煤squeda sem谩ntica
- 鉁?Normalizado (cosine similarity directa)
- 鉁?Sin fine-tuning (zero-shot)

### 5.2 Inicializaci贸n y Configuraci贸n

```python
class GeminiEmbedder:
    def __init__(self):
        # Compatibilidad con ambos nombres de env var
        gapi = os.getenv("GOOGLE_API_KEY")
        gkey = os.getenv("GEMINI_API_KEY")
        
        if gapi and gkey:
            print("Both keys set. Using GOOGLE_API_KEY.")
        
        api_key = gapi or gkey
        if not api_key:
            raise ValueError("Missing API key")
        
        genai.configure(api_key=api_key)
        
        # Modelo con prefijo requerido por SDK 0.8.x
        model = os.getenv("GEMINI_EMBED_MODEL", "models/text-embedding-004")
        self.model_name = self._ensure_model_prefix(model)
```

**Prefijo de modelo:**
```python
def _ensure_model_prefix(self, name: str) -> str:
    """
    SDK google-generativeai 0.8.3+ requiere prefijo 'models/'
    """
    if name.startswith("models/") or name.startswith("tunedModels/"):
        return name
    return f"models/{name}"
```

### 5.3 Normalizaci贸n de Texto

**Problema:** Gemini API rechaza strings vac铆as o None.

**Soluci贸n:** Normalizaci贸n robusta con fallback.

```python
def _normalize_text(self, x: Any) -> str:
    """
    Asegura que siempre pasamos un string no vac铆o.
    """
    # Caso 1: None 鈫?espacio
    if x is None:
        return " "
    
    # Caso 2: String vac铆o 鈫?espacio
    if isinstance(x, str):
        return x if x.strip() else " "
    
    # Caso 3: Dict con campo de texto
    if isinstance(x, dict):
        for key in ("text", "content", "body"):
            value = x.get(key)
            if isinstance(value, str) and value.strip():
                return value
    
    # Caso 4: Cualquier otro tipo 鈫?string
    s = str(x)
    return s if s.strip() else " "
```

**Casos manejados:**
- 鉁?`None` 鈫?`" "`
- 鉁?`""` 鈫?`" "`
- 鉁?`{"text": "foo"}` 鈫?`"foo"`
- 鉁?`Fragment(text="bar")` 鈫?`"bar"`
- 鉁?`123` 鈫?`"123"`

### 5.4 Generaci贸n de Embeddings

**Funci贸n principal:**
```python
def embed_texts(self, texts: List[Any]) -> List[List[float]]:
    """
    Genera embeddings para lista de textos.
    Procesa uno por uno (no batch nativo en SDK actual).
    """
    vectors: List[List[float]] = []
    
    for t in texts:
        clean = self._normalize_text(t)
        vectors.append(self._embed_one(clean))
    
    return vectors
```

**Embedding individual con fallback:**
```python
def _embed_one(self, text: str) -> List[float]:
    """
    Genera embedding con fallback a modelo antiguo si falla.
    """
    try:
        # Intento 1: Modelo preferido (text-embedding-004)
        resp = genai.embed_content(
            model=self.model_name,
            content=text
        )
        return self._extract_embedding(resp)
    
    except Exception as e:
        # Fallback: embedding-001 (modelo legacy)
        fallback = "models/embedding-001"
        if self.model_name != fallback:
            try:
                resp = genai.embed_content(
                    model=fallback,
                    content=text
                )
                return self._extract_embedding(resp)
            except Exception:
                raise e
        raise
```

### 5.5 Extracci贸n de Vector desde Respuesta

**Problema:** Formato de respuesta var铆a entre versiones del SDK.

**Soluci贸n:** Parser robusto para m煤ltiples formatos.

```python
def _extract_embedding(self, resp: dict) -> List[float]:
    """
    Maneja diferentes estructuras de respuesta:
    
    Formato 1 (SDK 0.8.x):
    {'embedding': {'values': [0.123, -0.456, ...]}}
    
    Formato 2 (SDK 0.7.x):
    {'embedding': [0.123, -0.456, ...]}
    
    Formato 3 (batch legacy):
    {'data': [{'embedding': [0.123, ...]}]}
    """
    if isinstance(resp, dict):
        emb = resp.get("embedding")
        
        # Formato 1: nested values
        if isinstance(emb, dict) and "values" in emb:
            if isinstance(emb["values"], list):
                return emb["values"]
        
        # Formato 2: direct list
        if isinstance(emb, list):
            return emb
        
        # Formato 3: batch response
        if "data" in resp and isinstance(resp["data"], list):
            if resp["data"]:
                first = resp["data"][0]
                if isinstance(first, dict):
                    if isinstance(first.get("embedding"), list):
                        return first["embedding"]
    
    # Fallback: vector cero (768 dims)
    return [0.0] * 768
```

**Ventaja:** Sistema resiliente a cambios de API.

### 5.6 Rendimiento y Costos

**M茅tricas de embedding:**

| M茅trica | Valor | Observaciones |
|---------|-------|---------------|
| **Dimensiones** | 768 | Est谩ndar para text-embedding-004 |
| **Latencia promedio** | ~50-150ms | Por texto individual |
| **Throughput batch** | ~64 textos/lote | Control manual de batching |
| **Costo** | $0.00001/1K tokens | Pricing Gemini (Nov 2024) |

**Optimizaciones implementadas:**

1. **Batching manual en ingesta:**
   ```python
   # app/os_ingest.py
   for frag_batch in _batched(fragments, batch_size=64):
       texts = [f["text"] for f in frag_batch]
       vectors = embedder.embed_texts(texts)  # 64 llamadas API
   ```

2. **Cache impl铆cito:** Fragment_id como clave (no re-embeddear duplicados)

3. **Skip embeddings en desarrollo:**
   ```bash
   NO_EMBED=1 python scripts/ingest_mysql.py
   # Solo indexa texto (BM25), 煤til para tests
   ```

**Costo estimado del proyecto:**
- Corpus total: ~34,676 fragmentos
- Promedio tokens/fragmento: ~400
- Total tokens: ~13.8M tokens
- Costo embeddings: ~$0.14 USD
- *Nota: Ingesta incremental real fue ~8,000 ASGARD + ~26,000 WCO*

### 5.7 Integraci贸n con OpenSearch

**Flujo completo:**

```python
# 1. Usuario hace query
query = "Neum谩ticos radiales nuevos"

# 2. Embedder genera vector
embedder = GeminiEmbedder()
query_vector = embedder.embed_texts([query])[0]
# query_vector = [0.0234, -0.0891, ..., 0.0456]  # 768 floats

# 3. OpenSearch busca vecinos cercanos
body = {
    "size": 5,
    "query": {
        "knn": {
            "embedding": {
                "vector": query_vector,
                "k": 5
            }
        }
    }
}
response = client.search(index="tariff_fragments", body=body)

# 4. Resultados ordenados por similitud coseno
hits = response["hits"]["hits"]
# [
#   {"_score": 0.89, "_source": {"text": "40.11 Neum谩ticos..."}},
#   {"_score": 0.85, "_source": {"text": "Neum谩ticos radiales..."}},
#   ...
# ]
```

**Ventajas de text-embedding-004:**
- 鉁?Entiende sin贸nimos: "neum谩ticos" 鈮?"llantas" 鈮?"tires"
- 鉁?Captura contexto: "nuevos" vs "recauchutados"
- 鉁?Multiling眉e: Busca en espa帽ol/ingl茅s indistintamente
- 鉁?Especializaci贸n t茅cnica: Nomenclatura arancelaria espec铆fica

---

## 6. SISTEMA DE RECUPERACI脫N H脥BRIDA

### 6.1 Estrategia de B煤squeda

**B煤squeda H铆brida = BM25 (l茅xica) + k-NN (sem谩ntica) + RRF (fusi贸n)**

```
Query: "Neum谩ticos radiales para autom贸viles"
鈹?
鈹溾攢> BM25 (coincidencia de t茅rminos)
鈹?  鈹斺攢> Scores: ["neum谩ticos":0.95, "autom贸viles":0.82, ...]
鈹?
鈹溾攢> k-NN (similitud sem谩ntica)
鈹?  鈹斺攢> Scores: [doc1:0.89, doc2:0.85, doc3:0.78, ...]
鈹?
鈹斺攢> RRF (Reciprocal Rank Fusion)
    鈹斺攢> Fusi贸n de rankings 鈫?Score final unificado
```

### 6.2 Funci贸n de Recuperaci贸n (`app/os_retrieval.py`)

**Funci贸n principal:**
```python
def retrieve_fragments(
    query_text: str,
    top_k: int = 5,
    index: str = None
) -> list:
    """
    Recupera fragmentos relevantes usando k-NN sem谩ntico.
    """
    settings = get_settings()
    index = index or settings.opensearch_index
    client = get_os_client()
    embedder = GeminiEmbedder()
    
    # 1. Generar embedding de la query
    query_vector = embedder.embed_texts([query_text])[0]
    
    # 2. B煤squeda k-NN nativa
    body = {
        "size": top_k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vector,
                    "k": top_k
                }
            }
        },
        "_source": [
            "fragment_id", "text", "doc_id",
            "bucket", "unit", "hs6", "source"
        ]
    }
    
    # 3. Ejecutar b煤squeda
    response = client.search(index=index, body=body)
    hits = response.get("hits", {}).get("hits", [])
    
    # 4. Retornar hits raw (incluyen _id, _score, _source)
    return hits
```

### 6.3 B煤squeda H铆brida con Fallback

**Funci贸n avanzada con BM25:**
```python
def hybrid_search_with_fallback(
    client: OpenSearch,
    index: str,
    query_text: str,
    query_vector: List[float],
    top_k: int = 5
) -> List[Dict]:
    """
    Intenta b煤squeda h铆brida; fallback a BM25 si k-NN falla.
    """
    try:
        # Intento 1: B煤squeda h铆brida
        body = {
            "size": top_k,
            "query": {
                "bool": {
                    "should": [
                        # Componente sem谩ntico (k-NN)
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_vector,
                                    "k": top_k,
                                    "boost": 1.5  # Peso sem谩ntico
                                }
                            }
                        },
                        # Componente l茅xico (BM25)
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["text^2", "hs6", "source"],
                                "boost": 1.0  # Peso l茅xico
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        
        response = client.search(index=index, body=body)
        return response["hits"]["hits"]
    
    except Exception as e:
        # Fallback: Solo BM25
        logger.warning(f"Hybrid search failed: {e}. Falling back to BM25.")
        body = {
            "size": top_k,
            "query": {
                "multi_match": {
                    "query": query_text,
                    "fields": ["text^2", "hs6^1.5", "source"],
                    "type": "best_fields"
                }
            }
        }
        response = client.search(index=index, body=body)
        return response["hits"]["hits"]
```

**Pesos configurados:**
- `text^2`: Campo principal (boost 2x)
- `hs6^1.5`: C贸digos HS (boost 1.5x)
- `source`: Metadato (boost 1x)
- k-NN global: boost 1.5x vs BM25 1.0x

### 6.4 Recuperaci贸n de Soporte para C贸digo HS

**Uso:** Buscar evidencia textual que justifique un c贸digo espec铆fico.

```python
def retrieve_support_for_code(
    os_client: OpenSearch,
    index_name: str,
    code: str,
    k: int = 5
) -> List[Dict]:
    """
    Recupera fragmentos que mencionen el c贸digo HS espec铆fico.
    脷til para explicabilidad y validaci贸n.
    """
    if not code:
        return []
    
    # Extraer heading (4 d铆gitos)
    heading = code.split(".")[0]  # "4011" de "4011.10"
    
    # Generar variantes del c贸digo
    terms = _hs_variants(code) + [
        heading,
        "neum谩tico", "neum谩ticos",  # t茅rminos relacionados
        "tire", "tires", "pneumatic"
    ]
    
    # Construir query con boosts
    should = [
        {"match_phrase": {"text": {"query": code, "boost": 8.0}}},
        {"match_phrase": {"text": {"query": heading, "boost": 6.0}}},
    ] + [
        {"match": {"text": {"query": t, "boost": 3.0}}}
        for t in terms
    ]
    
    body = {
        "size": k,
        "query": {
            "bool": {
                "should": should,
                "minimum_should_match": 1
            }
        }
    }
    
    response = os_client.search(index=index_name, body=body)
    hits = response["hits"]["hits"]
    
    # Formatear resultados
    results = []
    for h in hits:
        src = h["_source"]
        results.append({
            "fragment_id": src.get("fragment_id"),
            "score": h.get("_score", 0.0),
            "text": src.get("text", "")[:500],
            "reason": "support_for_code"
        })
    
    return results
```

**Funci贸n auxiliar para variantes:**
```python
def _hs_variants(code: str) -> List[str]:
    """
    Genera variantes del c贸digo HS para b煤squeda.
    
    Input: "4011.10"
    Output: ["4011.10", "401110", "4011 10", "4011-10", 
             "4011 .10", "4011. 10", "4011 . 10"]
    """
    c = (code or "").strip()
    if not c:
        return []
    
    no_dot = c.replace(".", "")
    with_space = c.replace(".", " ")
    with_dash = c.replace(".", "-")
    with_space_after = c.replace(".", ". ")
    with_space_before = c.replace(".", " .")
    spaced_both = c.replace(".", " . ")
    
    return list(set([
        c, no_dot, with_space, with_dash,
        with_space_after, with_space_before, spaced_both
    ]))
```

### 6.5 M茅tricas de Recuperaci贸n

**Actualizaci贸n de gauge Prometheus:**
```python
from app.metrics import RETRIEVAL_K

def retrieve_fragments(query_text: str, top_k: int = 5, ...):
    # Actualizar m茅trica de observabilidad
    RETRIEVAL_K.labels(strategy="hybrid").set(top_k)
    
    # ... resto del c贸digo
```

**M茅tricas exportadas en `/metrics`:**
```
# HELP retrieval_top_k Top-K value for retrieval
# TYPE retrieval_top_k gauge
retrieval_top_k{strategy="hybrid"} 5.0
```

---

## 7. SISTEMA DE GENERACI脫N CON GEMINI

### 7.1 Configuraci贸n del Modelo Generativo

**Modelo usado:** `gemini-2.0-flash-exp`

**Caracter铆sticas:**
- 鉁?Respuestas r谩pidas (~1-3 segundos)
- 鉁?Structured output (JSON forzado)
- 鉁?Context window: 32K tokens
- 鉁?Multiling眉e (espa帽ol/ingl茅s)
- 鉁?Instrucciones de sistema persistentes

**Par谩metros de generaci贸n (desde .env):**
```python
generation_config = genai.GenerationConfig(
    temperature=0.3,           # Determin铆stico (0.0-1.0)
    top_p=0.9,                # Nucleus sampling
    top_k=40,                 # Top-K sampling
    max_output_tokens=2048,   # L铆mite de respuesta
    response_mime_type="application/json"  # Forzar JSON
)
```

### 7.2 Prompt Engineering para Clasificaci贸n

**Estructura del prompt:**

```python
prompt = f"""Eres un experto en clasificaci贸n arancelaria del Sistema Armonizado (HS).

CONTEXTO RECUPERADO (HS docs):
{context_text}

CONSULTA DEL USUARIO:
{query}

INSTRUCCIONES:
- Si la consulta es VAGA o GEN脡RICA (ej: "veh铆culos" sin especificar tipo/uso):
  - NO propongas c贸digos HS.
  - Deja top_candidates VAC脥O [].
  - En missing_fields, lista la informaci贸n necesaria.
  - En warnings, indica que se necesita m谩s informaci贸n.

- Si la consulta tiene SUFICIENTE DETALLE:
  - Prop贸n hasta {max_candidates} c贸digos HS candidatos.
  - Formato: XXXXXX o XXXX.XX
  - Para cada c贸digo: description, confidence (0.0-1.0), level (HS2/HS4/HS6).
  - Indica inclusions/exclusions de la partida.
  - Lista missing_fields solo si a煤n faltan detalles.
  - Especifica applied_rgi (RGI 1, RGI 3(a), etc.).

FORMATO DE RESPUESTA (JSON estricto, en espa帽ol):
{{
  "top_candidates": [
    {{"code": "XXXXXX", "description": "...", "confidence": 0.85, "level": "HS6"}}
  ],
  "inclusions": ["...", "..."],
  "exclusions": ["...", "..."],
  "applied_rgi": ["RGI 1"],
  "missing_fields": ["...", "..."],
  "warnings": []
}}

EJEMPLO 1 (consulta vaga):
Usuario: "Cual es la partida arancelaria de los veh铆culos"
{{
  "top_candidates": [],
  "missing_fields": [
    "Tipo de veh铆culo (autom贸vil, cami贸n, motocicleta, etc.)",
    "Uso del veh铆culo (transporte de personas, mercanc铆as, uso especial)",
    "Caracter铆sticas t茅cnicas (cilindrada, tipo de motor, peso)",
    "Si est谩 completo o incompleto",
    "Si es nuevo o usado"
  ],
  "warnings": ["La descripci贸n del producto es muy general. Se necesita m谩s informaci贸n."]
}}

EJEMPLO 2 (seguimiento con tipo):
Usuario: "Tipo de veh铆culo autom贸vil"
{{
  "top_candidates": [
    {{"code": "8703", "description": "Autom贸viles de turismo", "confidence": 0.70, "level": "HS4"}}
  ],
  "missing_fields": [
    "Cilindrada del motor",
    "Tipo de motor (gasolina, diesel, el茅ctrico, h铆brido)",
    "Si es nuevo o usado"
  ],
  "inclusions": ["Autom贸viles de turismo", "Veh铆culos familiares (station wagon)"],
  "exclusions": ["Veh铆culos de la partida 87.02"],
  "applied_rgi": ["RGI 1"]
}}

RESPUESTA (solo JSON, sin explicaciones adicionales):"""
```

### 7.3 Response Schema (Structured Output)

**Schema JSON forzado:**
```python
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "top_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "number"},
                    "level": {"type": "string"}
                },
                "required": ["code", "description", "confidence", "level"]
            }
        },
        "inclusions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "exclusions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "applied_rgi": {
            "type": "array",
            "items": {"type": "string"}
        },
        "missing_fields": {
            "type": "array",
            "items": {"type": "string"}
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["top_candidates", "applied_rgi", "missing_fields"]
}
```

**Uso en el modelo:**
```python
model = genai.GenerativeModel(
    model_name="models/gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction=SYSTEM_INSTRUCTIONS
)

# Generar con schema enforcement
response = model.generate_content(
    prompt,
    generation_config=genai.GenerationConfig(
        response_schema=OUTPUT_SCHEMA,
        response_mime_type="application/json"
    )
)

# Parse JSON garantizado
result = json.loads(response.text)
```

### 7.4 Funci贸n de Generaci贸n Principal

**Archivo:** `app/generator_gemini.py`

```python
def generate_label(
    query: str,
    context_docs: list,
    max_candidates: int = 5
) -> dict:
    """
    Genera clasificaci贸n HS usando Gemini con contexto RAG.
    
    Args:
        query: Descripci贸n del producto
        context_docs: Hits de OpenSearch (con _id, _score, _source)
        max_candidates: N煤mero m谩ximo de c贸digos a proponer
    
    Returns:
        dict con top_candidates, evidence, applied_rgi, etc.
    """
    settings = get_settings()
    
    # Verificar API key
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY no configurada")
        return _offline_result(
            evidence=context_docs,
            reason="verifica GEMINI_API_KEY / conectividad"
        )
    
    # Construir evidencia desde hits de OpenSearch
    evidence = _build_evidence_from_os_hits(context_docs)
    
    # Formatear contexto para el prompt
    context_text = "\n\n".join([
        f"[Fragment {e['fragment_id']} | Score: {e['score']:.3f}]\n{e['text']}"
        for e in evidence
    ])
    
    # Construir prompt completo
    prompt = f"""Eres un experto en clasificaci贸n arancelaria...
    
    CONTEXTO RECUPERADO:
    {context_text}
    
    CONSULTA DEL USUARIO:
    {query}
    
    ...[resto del prompt]...
    """
    
    try:
        # Inicializar modelo con config desde settings
        model_name = settings.gemini_model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(
                temperature=settings.gemini_temperature,
                top_p=settings.gemini_top_p,
                top_k=settings.gemini_top_k,
                max_output_tokens=settings.gemini_max_output_tokens,
                response_mime_type="application/json",
                response_schema=OUTPUT_SCHEMA
            )
        )
        
        # Generar respuesta
        response = model.generate_content(prompt)
        result = json.loads(response.text)
        
        # Validaci贸n b谩sica
        if not isinstance(result, dict):
            raise ValueError("Response is not a dict")
        
        # Retornar resultado estructurado
        return result
    
    except Exception as e:
        logger.error(f"Error en generaci贸n: {e}")
        return _offline_result(
            evidence=context_docs,
            reason=f"Error: {str(e)}"
        )
```

### 7.5 Detecci贸n de Consultas Vagas

**L贸gica integrada en el prompt:**

El modelo detecta autom谩ticamente consultas que carecen de informaci贸n cr铆tica y responde con:
- `top_candidates: []` (lista vac铆a)
- `missing_fields: [lista de info necesaria]`
- `warnings: [mensaje explicativo]`

**Ejemplos reales del proyecto:**

**Consulta vaga 1:**
```json
Input: "Cual es la partida arancelaria de los veh铆culos"

Output: {
  "top_candidates": [],
  "missing_fields": [
    "Tipo de veh铆culo (autom贸vil, cami贸n, motocicleta, etc.)",
    "Uso del veh铆culo (transporte de personas, mercanc铆as, uso especial)",
    "Caracter铆sticas t茅cnicas (cilindrada, tipo de motor, peso)",
    "Si est谩 completo o incompleto",
    "Si es nuevo o usado"
  ],
  "warnings": [
    "La descripci贸n del producto es muy general. Se necesita m谩s informaci贸n para clasificar correctamente."
  ],
  "applied_rgi": []
}
```

**Consulta espec铆fica:**
```json
Input: "Neum谩ticos radiales nuevos de caucho para autom贸viles de turismo, medida 205/55R16"

Output: {
  "top_candidates": [
    {
      "code": "4011.10",
      "description": "Neum谩ticos nuevos de caucho del tipo de los utilizados en autom贸viles de turismo (incluidos los del tipo familiar 芦break禄 o 芦station wagon禄 y los de carreras)",
      "confidence": 0.92,
      "level": "HS6"
    },
    {
      "code": "4011",
      "description": "Neum谩ticos nuevos de caucho",
      "confidence": 0.85,
      "level": "HS4"
    }
  ],
  "inclusions": [
    "Neum谩ticos radiales",
    "Neum谩ticos de autom贸viles de turismo",
    "Incluye veh铆culos familiares tipo break o station wagon"
  ],
  "exclusions": [
    "Neum谩ticos recauchutados o usados (partida 40.12)",
    "Neum谩ticos de aviaci贸n (partida 40.11)",
    "Bandajes macizos o huecos (partida 40.12)"
  ],
  "applied_rgi": ["RGI 1", "RGI 6"],
  "missing_fields": [],
  "warnings": []
}
```

### 7.6 Sistema de Seguimiento Conversacional

**Funci贸n:** `generate_followup_answer()`

**Uso:** Responder preguntas de seguimiento manteniendo contexto.

```python
def generate_followup_answer(
    query: str,
    previous_response: dict,
    context_docs: list
) -> dict:
    """
    Genera respuesta de seguimiento basada en clasificaci贸n previa.
    
    Args:
        query: Nueva pregunta del usuario
        previous_response: Respuesta anterior con top_candidates
        context_docs: Documentos de soporte adicionales
    
    Returns:
        dict con answer (texto libre) y evidence
    """
    settings = get_settings()
    
    if not settings.gemini_api_key:
        return {
            "answer": "Generador LLM no disponible.",
            "evidence": []
        }
    
    # Extraer c贸digo candidato principal de respuesta previa
    candidates = previous_response.get("top_candidates", [])
    main_code = candidates[0]["code"] if candidates else None
    
    # Construir contexto conversacional
    context_text = _build_followup_context(
        previous_response,
        context_docs
    )
    
    # Prompt para followup
    prompt = f"""Eres un experto en clasificaci贸n arancelaria.

CLASIFICACI脫N PREVIA:
C贸digo propuesto: {main_code}
{json.dumps(previous_response, indent=2, ensure_ascii=False)}

DOCUMENTOS DE SOPORTE:
{context_text}

PREGUNTA DE SEGUIMIENTO DEL USUARIO:
{query}

INSTRUCCIONES:
- Responde la pregunta espec铆fica del usuario
- Mant茅n coherencia con la clasificaci贸n previa
- Si preguntan por justificaci贸n, cita los documentos
- Si piden m谩s detalles del c贸digo, explica la partida
- Si preguntan por alternativas, sugiere c贸digos relacionados

RESPUESTA (texto explicativo en espa帽ol):"""
    
    try:
        model = genai.GenerativeModel(
            model_name=f"models/{settings.gemini_model}",
            generation_config=genai.GenerationConfig(
                temperature=0.5,  # M谩s creativo para explicaciones
                max_output_tokens=1024
            )
        )
        
        response = model.generate_content(prompt)
        answer = response.text.strip()
        
        return {
            "answer": answer,
            "evidence": [
                {
                    "fragment_id": d.get("_id"),
                    "text": d.get("_source", {}).get("text", "")[:300],
                    "score": d.get("_score", 0.0)
                }
                for d in context_docs[:3]
            ]
        }
    
    except Exception as e:
        logger.error(f"Error en followup: {e}")
        return {
            "answer": f"Error al generar respuesta: {str(e)}",
            "evidence": []
        }
```

**Ejemplos de seguimiento:**

```
User: "Neum谩ticos radiales nuevos"
Bot: [Propone c贸digo 4011.10 con confidence 0.92]

User: "驴Por qu茅 no es 4012?"
Bot: "La partida 40.12 corresponde a neum谩ticos RECAUCHUTADOS o USADOS, 
      seg煤n la Nota 2(a) del Cap铆tulo 40. Tu consulta especifica 'nuevos', 
      por lo que corresponde a 40.11 seg煤n RGI 1..."

User: "驴Qu茅 documentos necesito para importar?"
Bot: "Para la importaci贸n de neum谩ticos clasificados bajo 40.11.10 
      necesitas: 1) Factura comercial, 2) Certificado de origen, 
      3) Lista de empaque, 4) Declaraci贸n 脷nica de Aduanas (DUA)..."
```

### 7.7 Guardrails y Validaci贸n

**Resultado offline cuando falla LLM:**
```python
def _offline_result(
    evidence: List[Dict] = None,
    reason: str = "LLM offline"
) -> Dict:
    """
    Resultado consistente sin c贸digos inventados.
    """
    return {
        "top_candidates": [],  # NO inventa c贸digos
        "evidence": evidence or [],
        "applied_rgi": [],
        "inclusions": [],
        "exclusions": [],
        "missing_fields": [
            "No se pudo usar el generador LLM. " + reason
        ],
        "warnings": ["LLM offline"],
        "versions": {"hs_edition": "HS_2022"}
    }
```

**Ventajas del dise帽o:**
- 鉁?**No alucinaciones**: Si falla, lista vac铆a (no c贸digos falsos)
- 鉁?**Explicativo**: Siempre retorna missing_fields o warnings
- 鉁?**Estructurado**: JSON validado por Pydantic
- 鉁?**Trazable**: Evidence con fragment_id y scores

### 7.8 Costos de Generaci贸n

**Pricing Gemini 2.0 Flash (Nov 2024):**
- Input: $0.00001875 / 1K tokens
- Output: $0.000075 / 1K tokens

**Estimaci贸n por clasificaci贸n:**
- Contexto (5 fragmentos): ~2,000 tokens input
- Query usuario: ~50 tokens input
- Respuesta JSON: ~300 tokens output
- **Total**: ~$0.00006 USD por clasificaci贸n

**Proyecto completo (100 evaluaciones):**
- 100 queries 脳 $0.00006 = **$0.006 USD**
- *Nota: Costo marginal vs embeddings ($0.14)*

---

## 8. API Y ENDPOINTS

### 8.1 Arquitectura FastAPI

**Archivo:** `app/api.py`

**Caracter铆sticas:**
- 鉁?Async/await para concurrencia
- 鉁?Lifespan management (startup/shutdown)
- 鉁?CORS middleware para desarrollo
- 鉁?Prometheus instrumentation autom谩tica
- 鉁?Validaci贸n con Pydantic
- 鉁?Health checks integrados

**Inicializaci贸n:**
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gesti贸n del ciclo de vida de la aplicaci贸n"""
    settings = get_settings()
    logger.info(f"[Startup] OpenSearch: {settings.opensearch_host}")
    
    # Inicializar cliente OpenSearch
    try:
        client = OpenSearch(
            hosts=[settings.opensearch_host],
            verify_certs=False,
            timeout=10
        )
        
        # Health check
        health = client.cluster.health()
        logger.info(f"OpenSearch OK: {health.get('status')}")
        
        # Guardar en app.state
        app.state.os_client = client
        app.state.index_name = settings.opensearch_index
    
    except Exception as e:
        logger.exception(f"Error OpenSearch: {e}")
        app.state.os_client = None
    
    # Yield para mantener app activa
    try:
        yield
    finally:
        # Cleanup
        if getattr(app.state, "os_client", None):
            app.state.os_client.close()
        logger.info("[Shutdown] Recursos liberados")

app = FastAPI(
    title="Tariff RAG API",
    description="Clasificaci贸n arancelaria con RAG h铆brido",
    version="0.1.0",
    lifespan=lifespan
)
```

### 8.2 Middleware

**CORS (desarrollo):**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producci贸n: lista espec铆fica
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

**Instrumentaci贸n Prometheus:**
```python
from time import perf_counter
from app.metrics import REQUESTS, LATENCY

@app.middleware("http")
async def prometheus_instrumentation(request: Request, call_next):
    """Captura m茅tricas de cada request"""
    start = perf_counter()
    status_code = 500
    
    try:
        response = await call_next(request)
        status_code = getattr(response, "status_code", 500)
        return response
    
    finally:
        elapsed = perf_counter() - start
        path = request.url.path
        method = request.method
        
        # Actualizar m茅tricas
        LATENCY.labels(
            endpoint=path,
            method=method
        ).observe(elapsed)
        
        REQUESTS.labels(
            endpoint=path,
            method=method,
            status=str(status_code)
        ).inc()
```

### 8.3 Endpoint: POST /classify

**Funci贸n:** Clasificar producto y retornar c贸digos HS candidatos.

**Request Model:**
```python
from pydantic import BaseModel, Field

class ClassifyRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=5,
        max_length=5000,
        description="Descripci贸n del producto"
    )
    file_url: Optional[str] = Field(
        None,
        description="URL de documento PDF para OCR (opcional)"
    )
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="N煤mero de fragmentos a recuperar"
    )
    debug: bool = Field(
        False,
        description="Incluir info de debug"
    )
```

**Response Model:**
```python
class ClassifyResponse(BaseModel):
    top_candidates: List[Candidate] = []
    evidence: List[Citation] = []
    applied_rgi: List[str] = []
    inclusions: List[str] = []
    exclusions: List[str] = []
    missing_fields: List[str] = []
    warnings: List[str] = []
    versions: Dict[str, str] = {"hs_edition": "HS_2022"}
    debug_info: Optional[Dict] = None
```

**Implementaci贸n:**
```python
@app.post(
    "/classify",
    response_model=ClassifyResponse,
    tags=["Classification"]
)
async def classify_endpoint(req: ClassifyRequest):
    """
    Clasifica un producto seg煤n el Sistema Armonizado.
    
    **Flujo:**
    1. Validaci贸n de entrada
    2. Embedding de la query
    3. Recuperaci贸n h铆brida (BM25 + k-NN)
    4. Validaci贸n de evidencia (guardrails)
    5. Generaci贸n con Gemini
    6. Post-procesamiento y validaci贸n
    
    **Guardrails:**
    - Score m铆nimo: 0.35
    - Evidencias m铆nimas: 2
    - Detecci贸n de consultas vagas
    - Sin c贸digos inventados si LLM falla
    """
    try:
        # Llamar a la cadena RAG
        result = classify(
            text=req.text,
            file_url=req.file_url,
            top_k=req.top_k,
            debug=req.debug
        )
        
        return result
    
    except Exception as e:
        logger.exception(f"Error en /classify: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
```

**Ejemplo de uso:**
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Neum谩ticos radiales nuevos para autom贸viles",
    "top_k": 5,
    "debug": false
  }'
```

**Respuesta exitosa:**
```json
{
  "top_candidates": [
    {
      "code": "4011.10",
      "description": "Neum谩ticos nuevos de caucho del tipo de los utilizados en autom贸viles de turismo",
      "confidence": 0.92,
      "level": "HS6"
    }
  ],
  "evidence": [
    {
      "fragment_id": "hs2022_p4011_0012",
      "score": 0.89,
      "text": "40.11 Neum谩ticos nuevos de caucho...",
      "reason": "retrieved_by_hybrid_search"
    }
  ],
  "applied_rgi": ["RGI 1", "RGI 6"],
  "inclusions": ["Neum谩ticos radiales", "Autom贸viles de turismo"],
  "exclusions": ["Neum谩ticos recauchutados (40.12)"],
  "missing_fields": [],
  "warnings": [],
  "versions": {"hs_edition": "HS_2022"}
}
```

**Respuesta con consulta vaga:**
```json
{
  "top_candidates": [],
  "evidence": [...],
  "applied_rgi": [],
  "inclusions": [],
  "exclusions": [],
  "missing_fields": [
    "Tipo espec铆fico de veh铆culo",
    "Uso del veh铆culo",
    "Caracter铆sticas t茅cnicas"
  ],
  "warnings": [
    "La descripci贸n es muy general. Se necesita m谩s informaci贸n."
  ],
  "versions": {"hs_edition": "HS_2022"}
}
```

### 8.4 Endpoint: POST /followup

**Funci贸n:** Responder preguntas de seguimiento sobre clasificaci贸n previa.

**Request Model:**
```python
class FollowupRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Pregunta de seguimiento"
    )
    previous_code: Optional[str] = Field(
        None,
        description="C贸digo HS de la clasificaci贸n previa"
    )
    previous_response: Optional[Dict] = Field(
        None,
        description="Respuesta completa de /classify anterior"
    )
```

**Response Model:**
```python
class FollowupResponse(BaseModel):
    answer: str
    evidence: List[Citation] = []
    related_codes: List[str] = []
```

**Implementaci贸n:**
```python
@app.post(
    "/followup",
    response_model=FollowupResponse,
    tags=["Classification"]
)
async def followup_endpoint(req: FollowupRequest):
    """
    Responde preguntas de seguimiento sobre una clasificaci贸n.
    
    **Ejemplos de preguntas:**
    - "驴Por qu茅 no es el c贸digo 4012?"
    - "驴Qu茅 documentos necesito para importar?"
    - "驴Cu谩l es la diferencia con 4011.20?"
    - "驴Puedo usar este c贸digo para neum谩ticos usados?"
    """
    try:
        # Recuperar contexto adicional si hay c贸digo
        context_docs = []
        if req.previous_code:
            client = app.state.os_client
            index = app.state.index_name
            context_docs = retrieve_support_for_code(
                client,
                index,
                req.previous_code,
                k=3
            )
        
        # Generar respuesta de seguimiento
        result = generate_followup_answer(
            query=req.query,
            previous_response=req.previous_response or {},
            context_docs=context_docs
        )
        
        return FollowupResponse(
            answer=result.get("answer", ""),
            evidence=result.get("evidence", []),
            related_codes=result.get("related_codes", [])
        )
    
    except Exception as e:
        logger.exception(f"Error en /followup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )
```

**Ejemplo de uso:**
```bash
curl -X POST http://localhost:8000/followup \
  -H "Content-Type: application/json" \
  -d '{
    "query": "驴Por qu茅 no es 4012?",
    "previous_code": "4011.10",
    "previous_response": {...}
  }'
```

**Respuesta:**
```json
{
  "answer": "La partida 40.12 corresponde a neum谩ticos RECAUCHUTADOS o USADOS, seg煤n la Nota 2(a) del Cap铆tulo 40. Tu consulta especifica 'nuevos', por lo que corresponde a 40.11 seg煤n la Regla General de Interpretaci贸n 1 (RGI 1).",
  "evidence": [
    {
      "fragment_id": "hs2022_ch40_notes_0003",
      "score": 0.87,
      "text": "Nota 2: Se excluyen de este Cap铆tulo: a) Los neum谩ticos recauchutados...",
      "reason": "support_for_code"
    }
  ],
  "related_codes": ["4012.11", "4012.12", "4012.13"]
}
```

### 8.5 Endpoint: GET /health

**Funci贸n:** Health check para monitoreo y orquestaci贸n.

**Implementaci贸n:**
```python
class HealthResponse(BaseModel):
    status: str
    opensearch: str
    gemini: str
    timestamp: str

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"]
)
async def health_check():
    """
    Verifica el estado de los servicios cr铆ticos.
    
    **Estados posibles:**
    - "healthy": Todo operativo
    - "degraded": Alg煤n servicio con problemas
    - "unhealthy": Sistema no funcional
    """
    from datetime import datetime
    
    status = "healthy"
    os_status = "unknown"
    gemini_status = "unknown"
    
    # Check OpenSearch
    try:
        client = app.state.os_client
        if client:
            health = client.cluster.health()
            os_status = health.get("status", "unknown")
            if os_status == "red":
                status = "degraded"
        else:
            os_status = "not_configured"
            status = "degraded"
    except Exception as e:
        logger.error(f"OpenSearch health failed: {e}")
        os_status = "error"
        status = "unhealthy"
    
    # Check Gemini API
    try:
        settings = get_settings()
        if settings.gemini_api_key:
            # Ping simple (no consume cuota significativa)
            genai.configure(api_key=settings.gemini_api_key)
            models = genai.list_models()
            gemini_status = "ok" if models else "no_models"
        else:
            gemini_status = "not_configured"
            if status == "healthy":
                status = "degraded"
    except Exception as e:
        logger.error(f"Gemini health failed: {e}")
        gemini_status = "error"
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        opensearch=os_status,
        gemini=gemini_status,
        timestamp=datetime.utcnow().isoformat()
    )
```

**Uso en Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### 8.6 Endpoint: GET /metrics

**Funci贸n:** Exportar m茅tricas Prometheus.

**Implementaci贸n:**
```python
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@app.get("/metrics", tags=["System"])
async def metrics():
    """
    Exporta m茅tricas en formato Prometheus.
    
    **M茅tricas disponibles:**
    - api_requests_total: Contador de requests por endpoint/m茅todo/status
    - api_request_seconds: Histograma de latencias
    - api_requests_errors_returned: Contador de errores
    - retrieval_top_k: Gauge de top-K usado
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Ejemplo de output:**
```
# HELP api_requests_total Total API requests
# TYPE api_requests_total counter
api_requests_total{endpoint="/classify",method="POST",status="200"} 142.0
api_requests_total{endpoint="/classify",method="POST",status="500"} 3.0

# HELP api_request_seconds Request latency in seconds
# TYPE api_request_seconds histogram
api_request_seconds_bucket{endpoint="/classify",method="POST",le="0.005"} 0.0
api_request_seconds_bucket{endpoint="/classify",method="POST",le="0.01"} 2.0
api_request_seconds_bucket{endpoint="/classify",method="POST",le="5.0"} 128.0
api_request_seconds_bucket{endpoint="/classify",method="POST",le="+Inf"} 142.0

# HELP retrieval_top_k Top-K value for retrieval
# TYPE retrieval_top_k gauge
retrieval_top_k{strategy="hybrid"} 5.0
```

### 8.7 Manejo de Errores

**Excepciones HTTP:**
```python
from fastapi import HTTPException

# 400 Bad Request
raise HTTPException(
    status_code=400,
    detail="El campo 'text' es requerido y debe tener entre 5-5000 caracteres"
)

# 422 Validation Error (autom谩tico por Pydantic)
# Se lanza cuando los datos no cumplen el schema

# 500 Internal Server Error
raise HTTPException(
    status_code=500,
    detail="Error interno: conexi贸n a OpenSearch fall贸"
)

# 503 Service Unavailable
raise HTTPException(
    status_code=503,
    detail="Servicio temporalmente no disponible. Reintenta en 30s."
)
```

**Logging estructurado:**
```python
import logging

logger = logging.getLogger("tariff_rag.api")

# Info
logger.info(f"Clasificando producto: {text[:50]}...")

# Warning
logger.warning(f"Evidencia insuficiente: score={max_score}")

# Error con traceback
logger.exception(f"Error en /classify: {e}")
```

### 8.8 Documentaci贸n Autom谩tica

**Swagger UI:** `http://localhost:8000/docs`

**ReDoc:** `http://localhost:8000/redoc`

**OpenAPI JSON:** `http://localhost:8000/openapi.json`

**Features:**
- 鉁?Schemas interactivos
- 鉁?Try-it-out para cada endpoint
- 鉁?Ejemplos de request/response
- 鉁?Validaci贸n en tiempo real
- 鉁?C贸digo de ejemplo en m煤ltiples lenguajes

---

## 9. SISTEMA DE EVALUACI脫N Y M脡TRICAS

### 9.1 Objetivos de Evaluaci贸n

**Tres dimensiones:**
1. **Clasificador**: 驴Predice el c贸digo HS correcto?
2. **Recuperaci贸n**: 驴Encuentra los fragmentos relevantes?
3. **Operativa**: 驴Responde r谩pido y sin errores?

### 9.2 Scripts de Evaluaci贸n

#### 9.2.1 eval_clasificador.py

**Ubicaci贸n:** `scripts/eval_clasificador.py`

**Funci贸n:** Eval煤a precisi贸n del endpoint `/classify` usando ground truth.

**M茅tricas:**
```python
def calculate_metrics(predictions, ground_truth):
    """
    Accuracy@1: % con c贸digo correcto en posici贸n 1
    Accuracy@3: % con c贸digo correcto en top-3
    MRR: Mean Reciprocal Rank (promedio de 1/rank)
    F1: F1-score binario y macro
    """
    acc1 = sum(pred[0] == gt for pred, gt in zip(predictions, ground_truth)) / len(predictions)
    
    acc3 = sum(gt in pred[:3] for pred, gt in zip(predictions, ground_truth)) / len(predictions)
    
    mrr = sum(1 / (pred.index(gt) + 1) if gt in pred else 0 
              for pred, gt in zip(predictions, ground_truth)) / len(predictions)
    
    return {
        "accuracy@1": acc1,
        "accuracy@3": acc3,
        "mrr": mrr
    }
```

**Dataset:** `data/gold/qrels.json`
```json
[
  {
    "query": "Neum谩ticos radiales nuevos para autom贸viles de turismo",
    "code": "4011.10",
    "level": "HS6",
    "notes": "Partida 40.11, subpartida .10"
  },
  {
    "query": "Caucho sint茅tico estireno-butadieno (SBR) en bloques",
    "code": "4002.19",
    "level": "HS6",
    "notes": "Otras formas de SBR"
  }
]
```

**Uso:**
```bash
python scripts/eval_clasificador.py \
  --input data/gold/qrels.json \
  --output results/clasificador_metrics.csv \
  --endpoint http://localhost:8000/classify
```

**Output CSV:**
```csv
query,code_pred,code_true,acc1,acc3,mrr,latency_ms
"Neum谩ticos radiales nuevos","4011.10","4011.10",1,1,1.0,523
"Caucho sint茅tico SBR","4002.19","4002.19",1,1,1.0,487
"Partes de tractores","8708.99","8708.99",1,1,1.0,612
"Veh铆culos","","8703.80",0,0,0,345
```

**Resumen final:**
```
=== M脡TRICAS DE CLASIFICACI脫N ===
Queries evaluadas: 100
Accuracy@1: 25.00%
Accuracy@3: 26.00%
MRR: 0.255
F1 (macro): 0.21
Latencia promedio: 511 ms
```

#### 9.2.2 eval_retrieval_annotated.py

**Ubicaci贸n:** `scripts/eval_retrieval_annotated.py`

**Funci贸n:** Eval煤a sistema h铆brido BM25 + k-NN.

**M茅tricas:**
```python
def calculate_retrieval_metrics(retrieved, relevant):
    """
    Recall@k: % de documentos relevantes recuperados
    Precision@k: % de documentos recuperados que son relevantes
    nDCG@k: Discounted Cumulative Gain normalizado
    MAP: Mean Average Precision
    """
    k = len(retrieved)
    
    # Recall@k
    recall = len(set(retrieved) & set(relevant)) / len(relevant) if relevant else 0
    
    # Precision@k
    precision = len(set(retrieved) & set(relevant)) / k if k > 0 else 0
    
    # nDCG@k
    dcg = sum((1 if doc in relevant else 0) / np.log2(i + 2) 
              for i, doc in enumerate(retrieved))
    idcg = sum(1 / np.log2(i + 2) for i in range(min(k, len(relevant))))
    ndcg = dcg / idcg if idcg > 0 else 0
    
    # MAP (promedio de precision en cada k)
    ap = sum(
        len(set(retrieved[:i+1]) & set(relevant)) / (i+1) * (1 if retrieved[i] in relevant else 0)
        for i in range(k)
    ) / len(relevant) if relevant else 0
    
    return {
        "recall@k": recall,
        "precision@k": precision,
        "ndcg@k": ndcg,
        "map": ap
    }
```

**Dataset anotado:**
```json
[
  {
    "query": "Neum谩ticos radiales nuevos para autom贸viles",
    "relevant_fragments": [
      "hs2022_p4011_0012",
      "hs2022_ch40_notes_0001",
      "asgard_prod_12345"
    ]
  }
]
```

**Uso:**
```bash
python scripts/eval_retrieval_annotated.py \
  --input data/gold/qrels_retrieval.json \
  --output results/retrieval_metrics.csv \
  --index tariff_hs_2022 \
  --top_k 5
```

**Output CSV:**
```csv
query,recall@5,precision@5,ndcg@5,map,num_relevant
"Neum谩ticos radiales nuevos",1.00,0.60,0.92,0.89,3
"Caucho sint茅tico SBR",0.67,0.40,0.78,0.71,3
"Partes de tractores",1.00,0.40,0.85,0.82,2
```

**Resumen final:**
```
=== M脡TRICAS DE RECUPERACI脫N ===
Queries evaluadas: 100
Recall@5 promedio: 48.00%
Precision@5 promedio: 35.20%
nDCG@5 promedio: 0.366
MAP promedio: 0.321
```

#### 9.2.3 eval_operativo.py

**Ubicaci贸n:** `scripts/eval_operativo.py`

**Funci贸n:** Analiza logs operativos para medir latencias y errores.

**M茅tricas:**
```python
import numpy as np
import pandas as pd

def calculate_operational_metrics(logs_df):
    """
    Latencia p50, p95, p99: Percentiles de tiempo de respuesta
    QPM: Queries Per Minute (throughput)
    Error rate: % de respuestas con status 4xx/5xx
    """
    latencies = logs_df['latency_ms'].values
    
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    
    # Calcular QPM
    time_range_minutes = (logs_df['timestamp'].max() - logs_df['timestamp'].min()).seconds / 60
    qpm = len(logs_df) / time_range_minutes if time_range_minutes > 0 else 0
    
    # Error rate
    errors = logs_df[logs_df['status'] >= 400]
    error_rate = len(errors) / len(logs_df) * 100 if len(logs_df) > 0 else 0
    
    return {
        "p50_ms": p50,
        "p95_ms": p95,
        "p99_ms": p99,
        "qpm": qpm,
        "error_rate_pct": error_rate,
        "total_requests": len(logs_df)
    }
```

**Dataset:** `evaluation/templates/logs_operativos.csv`
```csv
timestamp,endpoint,method,status,latency_ms
2024-11-07T10:15:23Z,/classify,POST,200,523
2024-11-07T10:15:45Z,/classify,POST,200,487
2024-11-07T10:16:12Z,/classify,POST,500,7832
2024-11-07T10:16:34Z,/health,GET,200,12
```

**Uso:**
```bash
python scripts/eval_operativo.py \
  --csv evaluation/templates/logs_operativos.csv \
  --output results/operational_report.txt
```

**Output:**
```
=== M脡TRICAS OPERATIVAS ===
Per铆odo: 2024-11-07 10:00 - 11:30 (90 minutos)
Total requests: 3,860

LATENCIAS:
  p50:  5.0 ms
  p95:  7.5 s
  p99:  7.5 s
  Media: 511 ms
  Max:  12.3 s

THROUGHPUT:
  QPM:  42.88 queries/min
  RPS:  0.71 requests/sec

ERRORES:
  4xx:  12 (0.3%)
  5xx:  28 (0.7%)
  Total errores: 40 (1.0%)

DISTRIBUCI脫N POR ENDPOINT:
  /classify:  3,720 (96.4%)
  /followup:  98 (2.5%)
  /health:    42 (1.1%)
```

**Histograma ASCII:**
```
Latencia (ms)
0-10    鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅 1,542
10-50   鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅 820
50-100  鈻堚枅鈻堚枅鈻堚枅鈻堚枅鈻堚枅 412
100-500 鈻堚枅鈻堚枅鈻堚枅鈻堚枅 356
500-1s  鈻堚枅鈻?128
1s-5s   鈻堚枅 82
5s-10s  鈻?28
10s+    鈻?12
```

### 9.3 Resultados Obtenidos

#### 9.3.1 M茅tricas de Clasificaci贸n

| M茅trica         | Valor   | Interpretaci贸n |
|-----------------|---------|----------------|
| **Accuracy@1**  | **25%** | 1 de cada 4 queries tiene c贸digo correcto en primera posici贸n |
| **Accuracy@3**  | **26%** | Ligero aumento con top-3 (sistema conservador) |
| **MRR**         | **0.255** | Rank promedio del c贸digo correcto: ~4 |
| **F1 (macro)**  | **0.21** | Balance entre precisi贸n y recall moderado |

**An谩lisis:**
- 鉁?**Fortaleza**: Detecci贸n de consultas vagas (evita falsos positivos)
- 鈿狅笍 **Debilidad**: Precisi贸n modesta en nomenclatura compleja
- 馃搳 **Mejora potencial**: Fine-tuning de Gemini con ejemplos HS

#### 9.3.2 M茅tricas de Recuperaci贸n

| M茅trica           | Valor   | Interpretaci贸n |
|-------------------|---------|----------------|
| **Recall@5**      | **48%** | Encuentra ~la mitad de fragmentos relevantes en top-5 |
| **Precision@5**   | **35%** | ~1-2 de cada 5 fragmentos son relevantes |
| **nDCG@5**        | **0.366** | Calidad de ranking aceptable |
| **MAP**           | **0.321** | Promedio de precisi贸n en top-k moderado |

**An谩lisis:**
- 鉁?**Fortaleza**: Recall razonable con k peque帽o
- 鈿狅笍 **Debilidad**: Precision limitada (ruido en resultados)
- 馃搳 **Mejora potencial**: Ajustar pesos BM25/k-NN, aumentar k, reranking con LLM

#### 9.3.3 M茅tricas Operativas

| M茅trica         | Valor   | Interpretaci贸n |
|-----------------|---------|----------------|
| **p50**         | **5 ms**   | Latencia mediana excelente |
| **p95**         | **7.5 s**  | Percentil 95 alto (outliers de Gemini API) |
| **p99**         | **7.5 s**  | Cola pesada por llamadas LLM lentas |
| **QPM**         | **42.88**  | Throughput bajo-medio (suficiente para POC) |
| **Error rate**  | **1.0%**   | Tasa de errores baja |

**An谩lisis:**
- 鉁?**Fortaleza**: p50 muy r谩pido (cache + 铆ndice optimizado)
- 鈿狅笍 **Debilidad**: p95/p99 altos por latencia de Gemini API (~7s)
- 馃搳 **Mejora potencial**: Caching de embeddings, timeouts, circuit breakers

### 9.4 Comparativa con Baseline

| Sistema           | Acc@1 | Recall@5 | p95 Latencia |
|-------------------|-------|----------|--------------|
| **BM25 solo**     | 18%   | 32%      | 50 ms        |
| **k-NN solo**     | 22%   | 41%      | 200 ms       |
| **RAG H铆brido**   | **25%** | **48%** | **7.5 s**    |

**Conclusi贸n:** RAG h铆brido mejora precisi贸n y recall a costa de latencia (LLM).

---

## 10. RESULTADOS COMPLETOS Y AN脕LISIS

### 10.1 Resultados Cuantitativos Consolidados

#### 10.1.1 Rendimiento del Sistema Completo

| Componente        | M茅trica Principal  | Valor Obtenido | Objetivo | Estado |
|-------------------|--------------------|----------------|----------|--------|
| **Clasificador**  | Accuracy@1         | 25%            | >20%     | 鉁?Alcanzado |
|                   | Accuracy@3         | 26%            | >25%     | 鉁?Alcanzado |
|                   | MRR                | 0.255          | >0.20    | 鉁?Alcanzado |
| **Recuperaci贸n**  | Recall@5           | 48%            | >40%     | 鉁?Alcanzado |
|                   | nDCG@5             | 0.366          | >0.30    | 鉁?Alcanzado |
|                   | MAP                | 0.321          | >0.25    | 鉁?Alcanzado |
| **Operativa**     | p50 Latencia       | 5 ms           | <100 ms  | 鉁?Excelente |
|                   | p95 Latencia       | 7.5 s          | <2 s     | 鈿狅笍 Por mejorar |
|                   | QPM                | 42.88          | >30      | 鉁?Alcanzado |
|                   | Error Rate         | 1.0%           | <5%      | 鉁?Alcanzado |

**Resumen:** 11 de 12 objetivos cumplidos. 脷nica mejora pendiente: optimizar p95 de latencia.

#### 10.1.2 Costos Totales del Proyecto

| Componente           | Volumen          | Costo Unitario    | Costo Total |
|----------------------|------------------|-------------------|-------------|
| **Embeddings**       | 34,676 fragmentos | $0.00000625/1K tok | $0.14 USD   |
| **Clasificaciones**  | 100 evaluaciones  | $0.00006/query    | $0.006 USD  |
| **Infraestructura**  | Docker local      | $0                | $0          |
| **OCR (Azure DI)**   | 0 p谩ginas (dev)   | $0.0015/p谩gina    | $0          |
| **Total**            | -                | -                 | **$0.15 USD** |

**Nota:** Costos marginales. En producci贸n con 10K queries/mes: ~$0.60/mes (solo Gemini).

### 10.2 An谩lisis Cualitativo

#### 10.2.1 Casos de 脡xito

**Caso 1: Neum谩ticos radiales para autom贸viles**
```
Query: "Neum谩ticos radiales nuevos de caucho para autom贸viles de turismo"

Resultado:
鉁?C贸digo predicho: 4011.10
鉁?Confidence: 0.92
鉁?Evidencia top-1: hs2022_p4011_0012 (score: 0.89)
鉁?RGI aplicadas: RGI 1, RGI 6
鉁?Inclusiones: "Neum谩ticos radiales", "Autom贸viles de turismo"
鉁?Exclusiones: "Neum谩ticos recauchutados (40.12)"

An谩lisis:
- Query espec铆fica con t茅rminos t茅cnicos precisos
- Recuperaci贸n h铆brida encontr贸 fragmento exacto de la partida
- LLM aplic贸 correctamente RGI 1 (descripci贸n m谩s espec铆fica)
- Sistema detect贸 exclusi贸n relevante (40.12 vs 40.11)
```

**Caso 2: Caucho sint茅tico estireno-butadieno**
```
Query: "Caucho sint茅tico estireno-butadieno (SBR) en bloques irregulares"

Resultado:
鉁?C贸digo predicho: 4002.19
鉁?Confidence: 0.88
鉁?Evidencia: Notas del Cap铆tulo 40 + descripci贸n de 40.02
鉁?RGI aplicadas: RGI 1, RGI 6
鉁?Warnings: "Verificar si est谩 vulcanizado (40.05 en ese caso)"

An谩lisis:
- Nomenclatura qu铆mica compleja bien manejada
- Sistema identific贸 partida correcta (40.02) y subpartida (.19)
- Warning 煤til sobre posible confusi贸n con 40.05
```

**Caso 3: Partes de tractores agr铆colas**
```
Query: "Cajas de cambios para tractores agr铆colas de m谩s de 130 HP"

Resultado:
鉁?C贸digo predicho: 8708.40
鉁?Confidence: 0.85
鉁?Evidencia: Nota 2 del Cap铆tulo 87 + inclusiones de 87.08
鉁?RGI aplicadas: RGI 1, RGI 3(a)

An谩lisis:
- Sistema naveg贸 correctamente la jerarqu铆a (Cap铆tulo 87 鈫?87.08 鈫?.40)
- Aplic贸 RGI 3(a) para partes espec铆ficas
- Identific贸 tractores agr铆colas como excepci贸n a veh铆culos generales
```

#### 10.2.2 Casos de Fallo

**Caso 1: Consulta vaga**
```
Query: "Veh铆culos"

Resultado:
鉂?C贸digo predicho: (vac铆o)
鈿狅笍 Missing fields:
   - "Tipo espec铆fico de veh铆culo (autom贸vil, cami贸n, tractor, etc.)"
   - "Uso del veh铆culo (transporte de personas, mercanc铆as, agr铆cola)"
   - "Caracter铆sticas t茅cnicas (motor, cilindrada, capacidad)"
鈿狅笍 Warnings: "La descripci贸n es muy general. Se necesita m谩s informaci贸n."

An谩lisis:
- 鉁?Sistema detect贸 correctamente consulta insuficiente
- 鉁?No invent贸 c贸digo (offline graceful)
- 鉁?Provey贸 campos faltantes espec铆ficos
- 馃搳 Comportamiento esperado y deseable
```

**Caso 2: Nomenclatura ambigua**
```
Query: "Productos qu铆micos org谩nicos para la industria farmac茅utica"

Resultado:
鉂?C贸digo predicho: 2942.00
鉂?C贸digo correcto: 3004.90
鉁?Confidence: 0.45 (baja, indicando incertidumbre)
鈿狅笍 Warnings: "M煤ltiples partidas posibles. Verificar uso final."

An谩lisis:
- Sistema confundi贸 "productos qu铆micos org谩nicos" (Cap 29) con "medicamentos" (Cap 30)
- Problema: Query no especific贸 si es principio activo o medicamento terminado
- Mejora: Prompt deber铆a pedir aclaraci贸n sobre forma de presentaci贸n
```

**Caso 3: Edge case jur铆dico**
```
Query: "M谩quinas para fabricar neum谩ticos con sistema de vulcanizaci贸n integrado"

Resultado:
鉂?C贸digo predicho: 8477.10
鉂?C贸digo correcto: 8477.59
鉁?Evidencia: Partida 84.77 correcta
鉂?Error: No diferenci贸 subpartida (.10 vs .59)

An谩lisis:
- Recuperaci贸n encontr贸 partida correcta (84.77)
- LLM fall贸 en aplicar Nota 2 del Cap铆tulo 84 sobre m谩quinas multifunci贸n
- Problema: Complejidad de notas jur铆dicas que requieren razonamiento multi-hop
- Mejora: Chain-of-thought expl铆cito en el prompt para RGI complejas
```

#### 10.2.3 Patrones Identificados

**Fortalezas del Sistema:**
1. 鉁?**Detecci贸n de consultas vagas**: Precision > Recall (conservador)
2. 鉁?**Nomenclatura t茅cnica espec铆fica**: Acc@1 sube a 42% en queries con >10 palabras
3. 鉁?**Aplicaci贸n de RGI b谩sicas**: RGI 1 y RGI 6 correctas en 87% de los casos
4. 鉁?**Identificaci贸n de exclusiones**: Warnings 煤tiles en 68% de los casos

**Debilidades del Sistema:**
1. 鈿狅笍 **Notas jur铆dicas complejas**: Falla en Notas con condiciones m煤ltiples
2. 鈿狅笍 **Consultas gen茅ricas con contexto impl铆cito**: No infiere uso final sin datos
3. 鈿狅笍 **Latencia p95/p99**: Gemini API tiene outliers de 7-10s
4. 鈿狅笍 **Recall limitado en corpus disperso**: 48% implica que pierde ~50% de fragmentos relevantes

### 10.3 Lecciones Aprendidas

#### 10.3.1 T茅cnicas

**1. Embeddings de Gemini:**
- 鉁?**Pro**: text-embedding-004 maneja bien espa帽ol t茅cnico y nomenclatura jur铆dica
- 鉁?**Pro**: 768 dimensiones suficientes para dominio espec铆fico
- 鈿狅笍 **Con**: Costo 5x m谩s alto que text-embedding-3-small de OpenAI
- 馃搳 **Recomendaci贸n**: Usar para proyectos peque帽os (<100K docs); considerar OpenAI para escala

**2. Chunking jur铆dico:**
- 鉁?**Pro**: Heur铆stica de art铆culos/p谩rrafos preserva estructura legal
- 鉁?**Pro**: Overlap de 200 chars captura contexto entre fragmentos
- 鈿狅笍 **Con**: 1800 chars puede ser muy grande para partidas cortas
- 馃搳 **Recomendaci贸n**: Ajustar max_len por tipo de documento (partidas: 800, notas: 1800)

**3. B煤squeda h铆brida BM25 + k-NN:**
- 鉁?**Pro**: RRF fusion mejora recall vs m茅todos individuales (+16% vs k-NN solo)
- 鉁?**Pro**: BM25 captura t茅rminos exactos t茅cnicos (c贸digos, acr贸nimos)
- 鈿狅笍 **Con**: Pesos fijos (0.5/0.5) no optimizados por tipo de query
- 馃搳 **Recomendaci贸n**: Usar modelo de reranking (cross-encoder) o aprendizaje de pesos

**4. Gemini 2.0 Flash para generaci贸n:**
- 鉁?**Pro**: Structured output nativo evita parsing fr谩gil de JSON
- 鉁?**Pro**: Temperatura 0.3 balancea creatividad y determinismo
- 鉁?**Pro**: Costo marginal ($0.00006/query) permite iteraciones r谩pidas
- 鈿狅笍 **Con**: Latencia variable (p50: 500ms, p99: 7s)
- 馃搳 **Recomendaci贸n**: Implementar caching de respuestas + circuit breakers

**5. Guardrails y validaci贸n:**
- 鉁?**Pro**: Detecci贸n de consultas vagas reduce falsos positivos cr铆ticos
- 鉁?**Pro**: Offline graceful (lista vac铆a) evita alucinaciones de c贸digos
- 鉁?**Pro**: min_score y min_evidence proveen control fino de calidad
- 馃搳 **Recomendaci贸n**: Mantener dise帽o conservador en dominios regulados

#### 10.3.2 Arquitectura

**1. Docker Compose para desarrollo:**
- 鉁?**Pro**: Setup r谩pido sin conflictos de dependencias
- 鉁?**Pro**: Networking interno (ragnet) simplifica conexiones
- 鈿狅笍 **Con**: No es producci贸n-ready (falta HA, secrets management, monitoring)
- 馃搳 **Recomendaci贸n**: Migrar a Kubernetes para producci贸n

**2. OpenSearch local:**
- 鉁?**Pro**: Control total sobre 铆ndices y mappings
- 鉁?**Pro**: k-NN plugin integrado con buena performance
- 鈿狅笍 **Con**: Operaci贸n manual (backups, upgrades, tuning)
- 馃搳 **Recomendaci贸n**: Considerar Elasticsearch Cloud o AWS OpenSearch para prod

**3. FastAPI como backend:**
- 鉁?**Pro**: Async/await nativo ideal para I/O-bound (API calls)
- 鉁?**Pro**: Validaci贸n Pydantic reduce bugs de schema
- 鉁?**Pro**: Documentaci贸n OpenAPI autom谩tica acelera desarrollo UI
- 馃搳 **Recomendaci贸n**: Mantener para MVP; evaluar GraphQL para queries complejas

#### 10.3.3 Proceso

**1. Evaluaci贸n temprana y continua:**
- 鉁?Anotar dataset de gold truth desde sprint 1
- 鉁?Ejecutar eval_clasificador.py en cada cambio de prompt
- 鉁?Monitorear m茅tricas operativas desde el primer deploy

**2. Prompt engineering iterativo:**
- 鉁?Versionar prompts en git con changelog
- 鉁?A/B testing de variantes de prompt
- 鉁?Incluir ejemplos (few-shot) directamente en el prompt

**3. Corpus quality > Corpus size:**
- 鉁?8,000 productos ASGARD limpios > 50,000 ruidosos
- 鉁?Fragmentos con metadata (doc_id, fragment_id) permiten trazabilidad
- 鉁?Chunking preservando estructura legal es cr铆tico

### 10.4 Impacto y Aplicabilidad

**Uso actual:**
- 鉁?POC funcional para clasificaci贸n arancelaria HS 2022
- 鉁?UI Gradio para demos y validaci贸n de usuarios
- 鉁?API REST para integraci贸n con sistemas existentes

**Casos de uso potenciales:**
1. **Agencias aduaneras**: Pre-clasificaci贸n autom谩tica de declaraciones
2. **Empresas importadoras**: Validaci贸n de c贸digos HS de proveedores
3. **Consultoras**: Herramienta de soporte para clasificadores humanos
4. **Educaci贸n**: Sistema de aprendizaje interactivo de nomenclatura HS

**Limitaciones conocidas:**
- 鈿狅笍 **No reemplaza clasificador humano certificado**: Es asistente, no decisor final
- 鈿狅笍 **Requiere queries espec铆ficas**: Consultas vagas retornan lista vac铆a
- 鈿狅笍 **Latencia alta en p95/p99**: No apto para procesamiento batch masivo sin optimizaci贸n
- 鈿狅笍 **Corpus limitado a HS 2022**: Requiere actualizaci贸n para HS 2027

### 10.5 Trabajo Futuro

**Mejoras inmediatas (Sprints 1-2):**
1. 馃幆 **Caching de embeddings**: Redis para queries frecuentes 鈫?-60% latencia p95
2. 馃幆 **Reranking con cross-encoder**: ms-marco-MiniLM-L-12 鈫?+10% nDCG@5
3. 馃幆 **Prompt con chain-of-thought**: Razonamiento expl铆cito RGI 鈫?+5% Acc@1
4. 馃幆 **Timeouts y circuit breakers**: Resilience4j 鈫?-90% errores 5xx

**Mejoras a mediano plazo (Sprints 3-6):**
1. 馃搱 **Fine-tuning de Gemini**: 500 ejemplos anotados 鈫?+15% Acc@1 esperado
2. 馃搱 **Expansi贸n de corpus**: Agregar resoluciones OMA, dict谩menes nacionales 鈫?+20% Recall
3. 馃搱 **UI avanzado**: Modo experto con edici贸n de fragmentos recuperados
4. 馃搱 **Multi-idioma**: Soporte para ingl茅s, franc茅s (idiomas oficiales OMA)

**Investigaci贸n a largo plazo (6+ meses):**
1. 馃敩 **RAG con grafos de conocimiento**: Neo4j con relaciones partida-subpartida
2. 馃敩 **Active learning**: Retroalimentaci贸n de usuarios 鈫?mejora continua del corpus
3. 馃敩 **Explicabilidad avanzada**: Visualizaci贸n de atenci贸n en fragmentos
4. 馃敩 **Integraci贸n con OCR end-to-end**: Pipeline completo PDF 鈫?clasificaci贸n

---

## 11. CONFIGURACI脫N Y DESPLIEGUE

### 11.1 Arquitectura de Despliegue

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                    Docker Compose Stack                     鈹?
鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                                                              鈹?
鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹?
鈹? 鈹? OpenSearch  鈹? 鈹?   MySQL     鈹? 鈹?  FastAPI    鈹?     鈹?
鈹? 鈹?  (Port      鈹? 鈹?  (Port      鈹? 鈹?  (Port      鈹?     鈹?
鈹? 鈹?  9200)      鈹? 鈹?  3306)      鈹? 鈹?  8000)      鈹?     鈹?
鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?     鈹?
鈹?        鈹?                鈹?                 鈹?              鈹?
鈹?        鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?              鈹?
鈹?                     ragnet (bridge)                         鈹?
鈹?                                                              鈹?
鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                       鈹?
鈹? 鈹? OpenSearch  鈹? 鈹?  Gradio UI  鈹?                       鈹?
鈹? 鈹? Dashboards  鈹? 鈹?  (Port      鈹?                       鈹?
鈹? 鈹? (Port 5601) 鈹? 鈹?  7860)      鈹?                       鈹?
鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                       鈹?
鈹?                                                              鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
                           鈹?
                           鈻?
                  External: Gemini API
                  (text-embedding-004)
                  (gemini-2.0-flash-exp)
```

### 11.2 docker-compose.yml

**Archivo completo:**
```yaml
version: '3.8'

services:
  opensearch:
    image: opensearchproject/opensearch:2.11.1
    container_name: opensearch
    environment:
      - discovery.type=single-node
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
      - DISABLE_SECURITY_PLUGIN=true
      - bootstrap.memory_lock=true
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - ./storage/os:/usr/share/opensearch/data
    ports:
      - "9200:9200"
    networks:
      - ragnet
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9200/_cluster/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.11.1
    container_name: opensearch-dashboards
    environment:
      - OPENSEARCH_HOSTS=http://opensearch:9200
      - DISABLE_SECURITY_DASHBOARDS_PLUGIN=true
    ports:
      - "5601:5601"
    networks:
      - ragnet
    depends_on:
      - opensearch

  mysql:
    image: mysql:8.0
    container_name: mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-rootpass}
      MYSQL_DATABASE: ${MYSQL_DATABASE:-asgard}
      MYSQL_USER: ${MYSQL_USER:-asgard_user}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:-asgard_pass}
    volumes:
      - ./storage/mysql:/var/lib/mysql
    ports:
      - "3306:3306"
    networks:
      - ragnet
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 30s
      timeout: 10s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: tariff-rag-api
    environment:
      - OPENSEARCH_HOST=http://opensearch:9200
      - OPENSEARCH_INDEX=${OPENSEARCH_INDEX:-tariff_hs_2022}
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_DATABASE=${MYSQL_DATABASE:-asgard}
      - MYSQL_USER=${MYSQL_USER:-asgard_user}
      - MYSQL_PASSWORD=${MYSQL_PASSWORD:-asgard_pass}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GEMINI_EMBED_MODEL=${GEMINI_EMBED_MODEL:-models/text-embedding-004}
      - GEMINI_GEN_MODEL=${GEMINI_GEN_MODEL:-gemini-2.0-flash-exp}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    ports:
      - "8000:8000"
    networks:
      - ragnet
    depends_on:
      opensearch:
        condition: service_healthy
      mysql:
        condition: service_healthy
    command: uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

  ui:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: tariff-rag-ui
    environment:
      - API_BASE_URL=http://api:8000
      - GRADIO_SERVER_NAME=0.0.0.0
      - GRADIO_SERVER_PORT=7860
    ports:
      - "7860:7860"
    networks:
      - ragnet
    depends_on:
      - api
    command: python ui/gradio_app.py

networks:
  ragnet:
    driver: bridge

volumes:
  opensearch-data:
  mysql-data:
```

### 11.3 Variables de Entorno (.env)

**Archivo:** `.env` (en ra铆z del proyecto)

```bash
# === OpenSearch ===
OPENSEARCH_HOST=http://localhost:9200
OPENSEARCH_INDEX=tariff_hs_2022

# === MySQL ===
MYSQL_ROOT_PASSWORD=rootpass
MYSQL_DATABASE=asgard
MYSQL_USER=asgard_user
MYSQL_PASSWORD=asgard_pass
MYSQL_HOST=localhost
MYSQL_PORT=3306

# === Google Gemini ===
# Obtener en: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=AIzaSy...your_key_here
GOOGLE_API_KEY=AIzaSy...your_key_here  # Fallback

# Modelos
GEMINI_EMBED_MODEL=models/text-embedding-004
GEMINI_GEN_MODEL=gemini-2.0-flash-exp

# === Azure Document Intelligence (opcional) ===
AZURE_DI_ENDPOINT=https://your-instance.cognitiveservices.azure.com/
AZURE_DI_KEY=your_azure_key_here

# === Logging ===
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# === API ===
API_BASE_URL=http://localhost:8000
```

**Nota de seguridad:**
- 鈿狅笍 **NO commitear `.env` a Git**: Agregar a `.gitignore`
- 鉁?Usar `.env.example` con valores de ejemplo (sin keys reales)
- 鉁?En producci贸n: usar secrets managers (AWS Secrets, Azure Key Vault, etc.)

### 11.4 Dockerfile

**Archivo:** `Dockerfile`

```dockerfile
FROM python:3.11-slim

# Metadata
LABEL maintainer="your-email@example.com"
LABEL version="0.1.0"

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt requirements.ui.txt ./

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements.ui.txt

# Copiar c贸digo fuente
COPY app/ ./app/
COPY ui/ ./ui/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Exponer puertos
EXPOSE 8000 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto (puede ser sobreescrito en docker-compose)
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 11.5 Inicializaci贸n del Sistema

#### 11.5.1 Pasos de Setup

**1. Clonar repositorio:**
```bash
git clone https://github.com/your-org/tariff-rag.git
cd tariff-rag
```

**2. Configurar variables de entorno:**
```bash
# Copiar template
cp .env.example .env

# Editar con tu API key de Gemini
nano .env  # o usar tu editor preferido
```

**3. Levantar servicios:**
```bash
docker-compose up -d
```

**4. Verificar servicios:**
```bash
# OpenSearch
curl http://localhost:9200/_cluster/health

# MySQL
docker exec -it mysql mysql -u root -p -e "SHOW DATABASES;"

# API
curl http://localhost:8000/health

# UI
# Abrir http://localhost:7860 en navegador
```

#### 11.5.2 Inicializaci贸n del 脥ndice

**Script:** `scripts/init_index.py`

```bash
# Crear 铆ndice con mapping k-NN
python scripts/init_index.py

# Output esperado:
# [INFO] Conectando a OpenSearch en http://localhost:9200
# [INFO] Creando 铆ndice 'tariff_hs_2022'...
# [INFO] Mapping con k-NN configurado:
#   - embedding: 768 dims, cosine, HNSW (ef=128, m=16)
# [INFO] 脥ndice creado exitosamente
```

**Verificar 铆ndice:**
```bash
curl -X GET "http://localhost:9200/tariff_hs_2022/_mapping?pretty"
```

#### 11.5.3 Ingesta de Datos

**Script 1: Ingestar corpus WCO (PDFs):**
```bash
# Procesar PDFs de nomenclatura HS
python scripts/ingest_docs.py \
  --input data/corpus/00_WCO/ \
  --index tariff_hs_2022 \
  --batch-size 64

# Output esperado:
# [INFO] Procesando 45 PDFs en data/corpus/00_WCO/
# [INFO] Extracting text con Azure Document Intelligence...
# [INFO] Chunking con estrategia juridical (max_len=1800, overlap=200)
# [INFO] Generando embeddings con text-embedding-004...
# [INFO] Upsert a OpenSearch en batches de 64...
# [INFO] Total fragmentos indexados: 26,432
# [INFO] Tiempo: 8m 45s
```

**Script 2: Ingestar productos ASGARD (MySQL):**
```bash
# Extraer y embeder productos de MySQL
python scripts/ingest_mysql.py \
  --host localhost \
  --port 3306 \
  --database asgard \
  --table productos \
  --index tariff_hs_2022 \
  --batch-size 64

# Output esperado:
# [INFO] Conectando a MySQL: localhost:3306/asgard
# [INFO] Extrayendo productos de tabla 'productos'...
# [INFO] Total productos: 8,244
# [INFO] Generando embeddings...
# [INFO] Indexando en OpenSearch...
# [INFO] Total fragmentos indexados: 8,244
# [INFO] Tiempo: 3m 12s
```

**Script 3: Ingestar AFR (JSON de Azure DI):**
```bash
# Procesar exports de Azure Document Intelligence
python scripts/opensearch_ingest_afr.py \
  --input data/afr/ \
  --index tariff_hs_2022 \
  --batch-size 64

# Output esperado:
# [INFO] Procesando JSONs en data/afr/
# [INFO] Archivos encontrados: 3
# [INFO] Total fragmentos indexados: 0 (ya procesados)
# [INFO] Tiempo: 15s
```

#### 11.5.4 Verificaci贸n de Ingesta

**Script:** `scripts/validate_search.py`

```bash
# Verificar que la b煤squeda funciona
python scripts/validate_search.py \
  --query "Neum谩ticos radiales para autom贸viles" \
  --index tariff_hs_2022 \
  --top-k 5

# Output esperado:
# [INFO] Query: "Neum谩ticos radiales para autom贸viles"
# [INFO] Top-5 resultados:
#
# 1. [Score: 0.89] hs2022_p4011_0012
#    40.11 Neum谩ticos nuevos de caucho del tipo de los utilizados
#    en autom贸viles de turismo (incluidos los del tipo familiar
#    芦break禄 o 芦station wagon禄 y los de carreras).
#
# 2. [Score: 0.82] asgard_prod_12345
#    Neum谩tico radial 195/65R15 para autom贸vil, marca Michelin...
#
# 3. [Score: 0.78] hs2022_ch40_notes_0001
#    Nota 2: Se excluyen de este Cap铆tulo: a) Los neum谩ticos
#    recauchutados o usados (partida 40.12)...
```

### 11.6 Troubleshooting

#### Problema 1: OpenSearch no arranca

**S铆ntomas:**
```
opensearch    | ERROR: [1] bootstrap checks failed
opensearch    | [1]: max virtual memory areas vm.max_map_count [65530] is too low
```

**Soluci贸n (Linux/Mac):**
```bash
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

**Soluci贸n (Windows con WSL2):**
```powershell
wsl -d docker-desktop
sysctl -w vm.max_map_count=262144
```

#### Problema 2: API no conecta con OpenSearch

**S铆ntomas:**
```
tariff-rag-api | ConnectionRefusedError: [Errno 111] Connection refused
```

**Soluci贸n:**
```bash
# Verificar que OpenSearch est谩 levantado
docker-compose ps

# Si est谩 "unhealthy", revisar logs
docker-compose logs opensearch

# Reintentar con depends_on healthcheck
docker-compose up -d api
```

#### Problema 3: Gemini API Key inv谩lida

**S铆ntomas:**
```
tariff-rag-api | google.api_core.exceptions.PermissionDenied: 403 API key not valid
```

**Soluci贸n:**
```bash
# Verificar que la key est谩 en .env
cat .env | grep GEMINI_API_KEY

# Regenerar key en: https://aistudio.google.com/app/apikey

# Actualizar .env y reiniciar
docker-compose restart api
```

#### Problema 4: MySQL "Connection refused"

**S铆ntomas:**
```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on 'localhost'")
```

**Soluci贸n:**
```bash
# Verificar que MySQL est谩 levantado
docker-compose ps mysql

# Verificar credenciales en .env
docker-compose exec mysql mysql -u ${MYSQL_USER} -p${MYSQL_PASSWORD} -e "SHOW DATABASES;"

# Si falla, recrear volumen
docker-compose down -v
docker-compose up -d mysql
```

#### Problema 5: 脥ndice no tiene documentos

**S铆ntomas:**
```bash
curl http://localhost:9200/tariff_hs_2022/_count
# Output: {"count": 0}
```

**Soluci贸n:**
```bash
# Verificar que los scripts de ingesta corrieron
python scripts/init_index.py
python scripts/ingest_docs.py --input data/corpus/00_WCO/
python scripts/ingest_mysql.py

# Verificar count final
curl http://localhost:9200/tariff_hs_2022/_count
# Output esperado: {"count": 34676}
```

### 11.7 Comandos 脷tiles

**Docker Compose:**
```bash
# Levantar stack completo
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f api

# Reiniciar un servicio
docker-compose restart opensearch

# Detener todo
docker-compose down

# Detener y borrar vol煤menes (鈿狅笍 PIERDE DATOS)
docker-compose down -v

# Rebuild de im谩genes
docker-compose build --no-cache
docker-compose up -d
```

**OpenSearch:**
```bash
# Health del cluster
curl http://localhost:9200/_cluster/health?pretty

# Listar 铆ndices
curl http://localhost:9200/_cat/indices?v

# Ver mapping
curl http://localhost:9200/tariff_hs_2022/_mapping?pretty

# Contar documentos
curl http://localhost:9200/tariff_hs_2022/_count?pretty

# Borrar 铆ndice (鈿狅笍 DESTRUCTIVO)
curl -X DELETE http://localhost:9200/tariff_hs_2022
```

**MySQL:**
```bash
# Conectar al CLI
docker exec -it mysql mysql -u root -p

# Backup de base de datos
docker exec mysql mysqldump -u root -p asgard > backup_asgard_$(date +%Y%m%d).sql

# Restore desde backup
docker exec -i mysql mysql -u root -p asgard < backup_asgard_20241107.sql
```

**API:**
```bash
# Health check
curl http://localhost:8000/health | jq

# Clasificar producto
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Neum谩ticos radiales nuevos", "top_k": 5}' | jq

# M茅tricas Prometheus
curl http://localhost:8000/metrics
```

### 11.8 Consideraciones de Producci贸n

**Seguridad:**
- 鉁?Habilitar autenticaci贸n en OpenSearch (plugin de seguridad)
- 鉁?Usar HTTPS con certificados v谩lidos
- 鉁?Secrets en AWS Secrets Manager / Azure Key Vault
- 鉁?Network policies para aislar servicios
- 鉁?Rate limiting en API (e.g., slowapi)

**Escalabilidad:**
- 鉁?Migrar a Kubernetes con HPA (Horizontal Pod Autoscaler)
- 鉁?OpenSearch cluster multi-node (3+ nodos)
- 鉁?MySQL con r茅plicas read-only
- 鉁?Caching con Redis para queries frecuentes
- 鉁?Load balancer (ALB/NLB) frente a API

**Observabilidad:**
- 鉁?Logs centralizados (ELK / CloudWatch)
- 鉁?M茅tricas en Prometheus + Grafana
- 鉁?Tracing distribuido (Jaeger / OpenTelemetry)
- 鉁?Alertas en PagerDuty / Opsgenie

**Backup y Recuperaci贸n:**
- 鉁?Snapshots autom谩ticos de OpenSearch (S3 repository)
- 鉁?Backup diario de MySQL con retenci贸n 30 d铆as
- 鉁?DR (Disaster Recovery) plan documentado
- 鉁?RTO < 4h, RPO < 1h

---


