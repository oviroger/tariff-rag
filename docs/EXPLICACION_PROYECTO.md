# Explicación Completa del Proyecto: Tariff RAG

## 📋 Índice
1. [¿Qué es este proyecto?](#qué-es-este-proyecto)
2. [Arquitectura general](#arquitectura-general)
3. [Estructura de carpetas](#estructura-de-carpetas)
4. [Archivos principales y su función](#archivos-principales-y-su-función)
5. [Flujo de funcionamiento](#flujo-de-funcionamiento)
6. [Tecnologías clave](#tecnologías-clave)
7. [Cómo usar el sistema](#cómo-usar-el-sistema)

---

## ¿Qué es este proyecto?

**Tariff RAG** es un sistema inteligente que ayuda a clasificar productos según el **Sistema Armonizado (HS)**, un código internacional usado en aduanas para identificar mercancías en importación y exportación.

### ¿Qué problema resuelve?
- Clasificar productos correctamente es complejo y requiere conocimiento experto.
- Los documentos arancelarios son extensos y difíciles de buscar manualmente.
- Los errores de clasificación pueden causar multas o retrasos en aduanas.

### ¿Cómo lo resuelve?
Este sistema usa **inteligencia artificial** y **búsqueda avanzada** para:
1. Buscar información relevante en documentos oficiales.
2. Sugerir códigos HS basados en la descripción del producto.
3. Mostrar evidencia textual que justifica la clasificación.
4. Indicar qué información falta para clasificar con mayor precisión.

---

## Arquitectura general

El proyecto se compone de **5 servicios principales** que trabajan juntos:

```
┌─────────────┐
│   Usuario   │
└──────┬──────┘
       │
       ├──────> 🌐 UI (Gradio) - Puerto 7860
       │        └──> Interfaz web conversacional
       │
       └──────> 🔧 API (FastAPI) - Puerto 8000
                └──> Procesa consultas y coordina todo
                     │
                     ├──> 🔍 OpenSearch (Puerto 9200)
                     │    └──> Búsqueda semántica + léxica
                     │
                     ├──> 🗄️ MySQL (Puerto 3306)
                     │    └──> Almacena corpus de productos
                     │
                     ├──> 🤖 Gemini API (Google)
                     │    └──> Genera embeddings y clasificaciones
                     │
                     └──> 📄 Azure Document Intelligence
                          └──> OCR de PDFs (opcional)
```

### Componentes clave:
- **UI (Gradio)**: Interfaz amigable para usuarios finales.
- **API (FastAPI)**: Cerebro del sistema, orquesta todo el flujo.
- **OpenSearch**: Motor de búsqueda híbrido (semántico + palabras clave).
- **MySQL**: Base de datos con productos previamente clasificados.
- **Gemini**: IA de Google para entender consultas y generar respuestas.
- **Azure DI**: Extrae texto de documentos PDF (opcional).

---

## Estructura de carpetas

```
tariff-rag/
│
├── app/                          # Código principal de la aplicación
│   ├── api.py                    # Endpoints REST (FastAPI)
│   ├── chain_rag.py              # Lógica del pipeline RAG
│   ├── config.py                 # Configuración y variables de entorno
│   ├── schemas.py                # Modelos de datos (Pydantic)
│   ├── generator_gemini.py       # Generación con IA (Gemini)
│   ├── embedder_gemini.py        # Creación de embeddings
│   ├── os_retrieval.py           # Búsqueda en OpenSearch
│   ├── os_index.py               # Gestión de índices OpenSearch
│   ├── os_ingest.py              # Ingesta de documentos
│   ├── etl_mysql.py              # Conexión con MySQL
│   ├── ocr_formrec.py            # OCR con Azure Document Intelligence
│   ├── chunking.py               # División de textos en fragmentos
│   ├── guardrails.py             # Validaciones y límites
│   ├── prompts.py                # Plantillas de prompts para IA
│   ├── rules.py                  # Reglas de negocio
│   ├── metrics.py                # Métricas de Prometheus
│   └── missing_fields_detector.py # Detecta información faltante
│
├── ui/                           # Interfaz de usuario
│   └── gradio_app.py             # Aplicación web con Gradio
│
├── scripts/                      # Scripts de utilidad
│   ├── init_index.py             # Crea el índice en OpenSearch
│   ├── ingest_docs.py            # Ingesta documentos al índice
│   ├── ingest_mysql.py           # Carga datos desde MySQL
│   └── validate_search.py        # Pruebas de búsqueda
│
├── tests/                        # Pruebas automatizadas
│   └── test_api.py               # Tests de la API
│
├── data/                         # Datos del proyecto
│   ├── corpus/                   # Documentos fuente
│   ├── afr/                      # Resultados de Azure DI
│   └── gold/                     # Datos de evaluación
│
├── storage/                      # Volúmenes persistentes
│   ├── os/                       # Datos de OpenSearch
│   └── mysql/                    # Datos de MySQL
│
├── evaluation/                   # Scripts de evaluación
│   ├── eval_clasificador.py     # Evalúa precisión de clasificación
│   └── eval_retrieval.py        # Evalúa calidad de búsqueda
│
├── docker-compose.yml            # Orquestación de servicios
├── Dockerfile                    # Imagen Docker para la API
├── .env                          # Variables de entorno
├── requirements.txt              # Dependencias Python
└── README.md                     # Documentación principal
```

---

## Archivos principales y su función

### 🔧 **app/api.py** - El punto de entrada de la API

**¿Qué hace?**
- Define los **endpoints REST** que reciben las consultas del usuario.
- Coordina el flujo completo: recibe → procesa → responde.
- Valida las entradas para evitar errores.

**Endpoints principales:**
```python
GET  /health          # Verifica que todos los servicios estén funcionando
POST /classify        # Clasifica un producto y devuelve códigos HS
GET  /metrics         # Métricas de uso (Prometheus)
```

**Flujo de /classify:**
1. Recibe la descripción del producto (`query`).
2. Valida que la consulta sea válida (mínimo 2 palabras, máximo 4000 caracteres).
3. Llama al pipeline RAG (`chain_rag.py`).
4. Devuelve: códigos candidatos, evidencia, información faltante, advertencias.

**Ejemplo de validación:**
```python
class ClassifyRequest(BaseModel):
    query: str = Field(..., max_length=4000)  # Máximo 4000 caracteres
    top_k: int = Field(default=5, ge=1, le=20)  # Entre 1 y 20 resultados
```

---

### 🧠 **app/chain_rag.py** - El cerebro del sistema

**¿Qué hace?**
- Implementa el **pipeline RAG** (Retrieval-Augmented Generation).
- Orquesta todos los pasos: búsqueda → validación → generación.

**Pipeline paso a paso:**
```python
def classify(text: str, file_url: Optional[str] = None, top_k: int = 5):
    # 1. OCR (si hay PDF)
    if file_url:
        text += extract_text_from_pdf(file_url)
    
    # 2. Búsqueda híbrida (semántica + léxica)
    docs = retrieve_fragments(text, top_k=top_k * 2)
    
    # 3. Validación de evidencia
    valid_docs = filter_by_score(docs, min_score=0.30)
    if len(valid_docs) < 2:
        return warning("Evidencia insuficiente")
    
    # 4. Generación con Gemini
    result = generate_label(text, valid_docs)
    
    # 5. Enriquecimiento y respuesta
    return format_response(result, evidence=valid_docs)
```

**Características clave:**
- **Guardrails**: Valida que haya suficiente evidencia antes de clasificar.
- **Fallback**: Si Gemini falla, usa candidatos derivados de metadatos.
- **Debug mode**: Devuelve información adicional para diagnóstico.

---

### 🔍 **app/os_retrieval.py** - Búsqueda inteligente

**¿Qué hace?**
- Busca fragmentos relevantes en **OpenSearch** usando dos métodos:
  1. **Búsqueda semántica (k-NN)**: Entiende el significado usando embeddings.
  2. **Búsqueda léxica (BM25)**: Busca palabras clave con boosts.

**Estrategia híbrida:**
```python
def hybrid_search_with_fallback(query: str, k: int = 5):
    # 1. Intenta búsqueda semántica
    results = knn_semantic_search(query, k)
    if results:
        return results
    
    # 2. Si falla, usa BM25 con boosts
    return bm25_search(query, k)
```

**Ventajas:**
- **Semántica**: Encuentra textos similares aunque usen palabras diferentes.
- **Léxica**: Útil cuando el usuario menciona códigos HS específicos.
- **Fallback**: Siempre devuelve algo, incluso si un método falla.

---

### 🤖 **app/generator_gemini.py** - Generación con IA

**¿Qué hace?**
- Usa **Gemini** (Google) para analizar evidencia y sugerir códigos HS.
- Genera respuestas estructuradas en formato JSON.
- Maneja consultas vagas y pide información adicional.

**Flujo de generación:**
```python
def generate_label(query: str, context_docs: list):
    # 1. Construye el contexto con evidencia
    context = format_evidence(context_docs)
    
    # 2. Crea el prompt con instrucciones
    prompt = f"""
    CONTEXTO: {context}
    CONSULTA: {query}
    
    Si la consulta es vaga:
      - NO propongas códigos
      - Lista información faltante
    
    Si tiene suficiente detalle:
      - Propón códigos HS candidatos
      - Indica confianza (0-1)
      - Explica inclusiones/exclusiones
    """
    
    # 3. Llama a Gemini con schema estructurado
    response = gemini.generate_content(prompt, schema=OUTPUT_SCHEMA)
    
    # 4. Parsea y valida el JSON
    return parse_and_validate(response.text)
```

**Características avanzadas:**
- **Structured output**: Gemini devuelve JSON válido siguiendo un schema.
- **Safety settings**: Desactiva filtros innecesarios para contenido técnico.
- **Fallback inteligente**: Si Gemini se bloquea, infiere candidatos desde metadatos.

---

### 📊 **app/schemas.py** - Modelos de datos

**¿Qué hace?**
- Define la **estructura de datos** usando Pydantic.
- Valida automáticamente que los datos sean correctos.

**Modelos principales:**
```python
# Candidato de clasificación
class Candidate(BaseModel):
    code: str                    # Código HS (ej: "8517.12")
    description: str             # Descripción del código
    confidence: float            # Confianza 0-1
    level: str                   # "HS2", "HS4", "HS6"

# Respuesta completa
class ClassifyResponse(BaseModel):
    top_candidates: List[Candidate]      # Códigos sugeridos
    evidence: List[Citation]             # Fragmentos recuperados
    applied_rgi: List[str]               # Reglas aplicadas (ej: "RGI 1")
    inclusions: List[str]                # Qué incluye la partida
    exclusions: List[str]                # Qué excluye
    missing_fields: List[str]            # Información faltante
    warnings: List[str]                  # Advertencias
```

---

### 🌐 **ui/gradio_app.py** - Interfaz de usuario

**¿Qué hace?**
- Proporciona una **interfaz web conversacional** fácil de usar.
- Gestiona el historial de conversación.
- Formatea las respuestas de forma legible.

**Componentes de la UI:**
```python
# 1. Interfaz de chat
chatbot = gr.ChatInterface(
    fn=chat_response,
    title="Clasificador Arancelario HS",
    description="Describe tu producto para obtener el código HS"
)

# 2. Gestión del historial
class ConversationState:
    def __init__(self):
        self.last_classification = None
        self.history = []
    
    def add_turn(self, user_msg, assistant_msg):
        self.history.append((user_msg, assistant_msg))
```

**Características:**
- **Formato mejorado**: Usa Markdown con emojis y colores.
- **Seguimiento inteligente**: Detecta preguntas de seguimiento.
- **Validación**: Verifica que la consulta sea sobre aranceles.
- **Expandibles**: Los fragmentos largos se pueden expandir.

---

### ⚙️ **app/config.py** - Configuración central

**¿Qué hace?**
- Centraliza **todas las variables de configuración**.
- Lee desde variables de entorno (`.env` o Docker).

**Configuración por categoría:**
```python
class Settings(BaseSettings):
    # OpenSearch
    opensearch_host: str = "http://opensearch:9200"
    opensearch_index: str = "tariff_fragments"
    opensearch_emb_dim: int = 768
    
    # MySQL
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_db: str = "corpusdb"
    
    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.3
    
    # Parámetros del RAG
    final_pasages: int = 8
    min_evidence: int = 2
    min_score: float = 0.30
    enable_retrieval_fallback: bool = False
```

---

### 🐳 **docker-compose.yml** - Orquestación de servicios

**¿Qué hace?**
- Define y coordina los **5 servicios** del sistema.
- Configura redes, volúmenes y healthchecks.

**Servicios configurados:**
```yaml
services:
  opensearch:           # Motor de búsqueda
    image: opensearchproject/opensearch:2.13.0
    ports: ["9200:9200"]
    volumes: ["./storage/os:/usr/share/opensearch/data"]
  
  dashboards:           # Visualización de OpenSearch
    image: opensearchproject/opensearch-dashboards:2.13.0
    ports: ["5601:5601"]
  
  mysql:                # Base de datos
    image: mysql:8.0
    ports: ["3306:3306"]
    volumes: ["mysql-data:/var/lib/mysql"]
  
  api:                  # API FastAPI
    build: .
    ports: ["8000:8000"]
    environment:
      - GEMINI_API_KEY=${GOOGLE_API_KEY}
      - OPENSEARCH_HOST=http://opensearch:9200
  
  ui:                   # Interfaz Gradio
    build: .
    ports: ["7860:7860"]
    command: python ui/gradio_app.py
```

---

## Flujo de funcionamiento

### Escenario 1: Consulta detallada

**Usuario:** "Smartphone con pantalla OLED de 6.1 pulgadas, 128GB, 5G, nuevo"

```
1. Usuario → UI Gradio
   └─> Envía consulta al endpoint POST /classify

2. API FastAPI
   └─> Valida entrada (longitud, formato)
   └─> Llama a chain_rag.classify()

3. Chain RAG
   └─> Llama a os_retrieval.retrieve_fragments()
       ├─> OpenSearch: Búsqueda k-NN con embeddings de Gemini
       └─> Devuelve 10 fragmentos relevantes (score > 0.30)
   
   └─> Filtra evidencia (mínimo 2 fragmentos válidos)
   
   └─> Llama a generator_gemini.generate_label()
       ├─> Construye prompt con evidencia
       ├─> Llama a Gemini con schema estructurado
       └─> Parsea JSON de respuesta

4. Gemini API
   └─> Analiza evidencia y genera respuesta:
       {
         "top_candidates": [
           {"code": "8517.12", "confidence": 0.95, "level": "HS6"}
         ],
         "applied_rgi": ["RGI 1"],
         "inclusions": ["Smartphones", "Teléfonos móviles"],
         "missing_fields": ["¿Es nuevo o usado?"]
       }

5. API → UI
   └─> Formatea respuesta en Markdown con emojis
   └─> Muestra al usuario:
       - Código: 8517.12 (95% confianza)
       - Evidencia: 5 fragmentos relevantes
       - Falta: Indicar si es nuevo/usado
```

---

### Escenario 2: Consulta vaga

**Usuario:** "¿Cuál es la partida arancelaria de los vehículos?"

```
1. Usuario → UI → API

2. Chain RAG
   └─> Recupera fragmentos sobre "vehículos"
   └─> Llama a Gemini

3. Gemini detecta consulta vaga
   └─> Devuelve:
       {
         "top_candidates": [],  # NO propone códigos
         "missing_fields": [
           "Tipo de vehículo (automóvil, camión, motocicleta)",
           "Uso (personas, mercancías, especial)",
           "Características técnicas (cilindrada, peso)",
           "Nuevo o usado"
         ],
         "warnings": ["Descripción muy general"]
       }

4. UI muestra al usuario:
   ⚠️ No se pueden sugerir códigos.
   🔍 Información adicional requerida:
   - Tipo de vehículo
   - Uso del vehículo
   - ...
```

---

### Escenario 3: Seguimiento conversacional

**Usuario 1:** "Vehículo para transporte de personas"

```
Sistema → "Tipo de vehículo? Cilindrada? Nuevo/usado?"
```

**Usuario 2:** "Es un automóvil, gasolina, 1600cc, nuevo"

```
1. UI detecta que hay contexto previo
   └─> Enriquece la consulta: "automóvil gasolina 1600cc nuevo"

2. Reclasifica con información completa
   └─> Gemini ahora puede proponer código específico:
       8703.23 (Automóvil gasolina 1000-1500cc) - 90% confianza
```

---

## Tecnologías clave

### 1. **OpenSearch** - Motor de búsqueda híbrido

**¿Por qué se usa?**
- Combina búsqueda semántica (k-NN) y léxica (BM25).
- Escala a millones de documentos.
- Compatible con Elasticsearch pero de código abierto.

**Configuración del índice:**
```python
{
  "mappings": {
    "properties": {
      "text": {"type": "text"},          # Para búsqueda BM25
      "embedding": {                      # Para búsqueda k-NN
        "type": "knn_vector",
        "dimension": 768,                 # Dimensión de embeddings
        "method": {
          "name": "hnsw",                 # Algoritmo HNSW (rápido)
          "space_type": "cosinesimil"     # Similitud del coseno
        }
      }
    }
  }
}
```

---

### 2. **Gemini** - IA de Google

**¿Por qué se usa?**
- **Embeddings**: Convierte texto en vectores para búsqueda semántica.
- **Generación**: Analiza evidencia y sugiere códigos HS.
- **Structured output**: Devuelve JSON estructurado automáticamente.

**Modelos utilizados:**
- `text-embedding-004`: Crea embeddings de 768 dimensiones.
- `gemini-2.5-flash`: Genera clasificaciones rápidas y precisas.

---

### 3. **FastAPI** - Framework web moderno

**¿Por qué se usa?**
- **Rápido**: Asíncrono y de alto rendimiento.
- **Validación automática**: Usa Pydantic para validar datos.
- **Documentación automática**: Genera `/docs` (Swagger UI).
- **Type hints**: Detecta errores antes de ejecutar.

---

### 4. **Gradio** - Interfaz de usuario fácil

**¿Por qué se usa?**
- **Rápido de implementar**: Pocas líneas de código.
- **Conversacional**: Soporta chat con historial.
- **Markdown**: Formatea respuestas con colores y emojis.

---

### 5. **Docker** - Contenedores

**¿Por qué se usa?**
- **Portabilidad**: Funciona igual en cualquier computadora.
- **Aislamiento**: Cada servicio tiene su entorno.
- **Reproducibilidad**: Mismas versiones siempre.

---

## Cómo usar el sistema

### Opción 1: API REST (para desarrolladores)

**1. Verificar salud:**
```bash
curl http://localhost:8000/health
```

**2. Clasificar producto:**
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Smartphone con pantalla OLED de 6.1 pulgadas",
    "top_k": 5
  }'
```

**3. Ver documentación interactiva:**
```
http://localhost:8000/docs
```

---

### Opción 2: Interfaz web (para usuarios finales)

**1. Abrir navegador:**
```
http://localhost:7860
```

**2. Escribir descripción del producto:**
```
"Ventilador USB de escritorio, 12cm, 5V"
```

**3. Revisar respuesta:**
- Código HS sugerido
- Nivel de confianza
- Evidencia textual
- Información faltante

**4. Hacer preguntas de seguimiento:**
- "¿Por qué ese código?"
- "¿Qué información falta?"
- "¿Hay alternativas?"

---

## Puntos técnicos destacados

### 1. **Búsqueda híbrida con fallback**
- **Primero**: Búsqueda semántica (k-NN con embeddings).
- **Si falla**: Búsqueda léxica (BM25 con boosts).
- **Resultado**: Siempre encuentra algo relevante.

### 2. **Guardrails de calidad**
- **MIN_EVIDENCE**: Mínimo 2 fragmentos con score > 0.30.
- **MAX_LENGTH**: Consultas limitadas a 4000 caracteres.
- **TOP_K**: Entre 1 y 20 resultados.

### 3. **Fallback por recuperación**
- Si Gemini falla, infiere candidatos desde metadatos (chapter/heading).
- Activable con `ENABLE_RETRIEVAL_FALLBACK=1`.

### 4. **Validación estricta**
- Pydantic valida todos los datos de entrada/salida.
- FastAPI rechaza peticiones inválidas con error 422.

### 5. **Métricas y observabilidad**
- **Prometheus**: Expone métricas en `/metrics`.
- **Logs estructurados**: Toda actividad se registra.
- **Debug mode**: Devuelve información adicional de diagnóstico.

---

## Resumen ejecutivo

| Aspecto | Descripción |
|---------|-------------|
| **Objetivo** | Clasificar productos según el Sistema Armonizado (HS) |
| **Método** | RAG (Retrieval-Augmented Generation) con búsqueda híbrida |
| **IA** | Google Gemini para embeddings y generación |
| **Búsqueda** | OpenSearch con k-NN (semántico) + BM25 (léxico) |
| **Interfaces** | API REST + UI web conversacional |
| **Lenguaje** | Python 3.11 |
| **Infraestructura** | Docker Compose (5 servicios) |
| **Precisión** | Variable según detalle de consulta (50-95% confianza) |
| **Velocidad** | 2-5 segundos por consulta |

---

## Próximos pasos (opcional)

- **Evaluación**: Implementar split 70/15/15 para train/val/test.
- **Métricas**: Agregar accuracy@1, MRR@3, F1 macro/micro.
- **Fine-tuning**: Ajustar embeddings con datos del dominio.
- **UI mejorada**: Agregar filtros por capítulo/sección.
- **Caché**: Guardar consultas frecuentes para mayor velocidad.

---

**Autor**: Sistema Tariff RAG  
**Fecha**: Noviembre 2025  
