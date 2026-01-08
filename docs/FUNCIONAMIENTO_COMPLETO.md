# 📚 Asistente de Clasificación Arancelaria - Documentación Completa

## Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Flujo de Conversación](#flujo-de-conversación)
5. [Gestión de Contexto y Persistencia](#gestión-de-contexto-y-persistencia)
6. [Detalles Técnicos](#detalles-técnicos)
7. [Ejemplos de Uso](#ejemplos-de-uso)
8. [Troubleshooting](#troubleshooting)

---

## Visión General

El **Asistente de Clasificación Arancelaria** es un sistema conversacional inteligente diseñado para ayudar usuarios a clasificar productos según el Sistema Armonizado (HS - Harmonized System). El sistema utiliza:

- **Inteligencia Artificial (Gemini)** para interpretar consultas en lenguaje natural
- **OpenSearch** para búsqueda semántica de información arancelaria
- **MySQL** para almacenar metadatos de productos
- **Redis** para persistencia de conversaciones entre sesiones
- **Gradio** para la interfaz de usuario web
- **FastAPI** para el backend de procesamiento

### Objetivo Principal

Proporcionar una experiencia conversacional fluida donde:
1. El usuario describe un producto de forma natural
2. El sistema hace preguntas de seguimiento para obtener detalles
3. Se retorna la partida arancelaria (código HS) más probable
4. El contexto se mantiene persistente entre sesiones

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    USUARIO (Navegador)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP(S)
┌──────────────────────▼──────────────────────────────────────┐
│              GRADIO UI (Puerto 7860)                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ConversationState per conversation_id                  │  │
│  │ - Historial de mensajes                                │  │
│  │ - Contexto de clasificación anterior                   │  │
│  │ - conversation_id único (UUID)                         │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP JSON
┌──────────────────────▼──────────────────────────────────────┐
│            FastAPI Backend (Puerto 8000)                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ POST /classify                                         │  │
│  │ - user_query: consulta del usuario                    │  │
│  │ - conversation_history: historial previo              │  │
│  │ - conversation_id: identificador de sesión            │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Redis Operations                                       │  │
│  │ - load_history(conversation_id)                       │  │
│  │ - save_history(conversation_id, turns)                │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Gemini LLM Integration                                │  │
│  │ - generate_label(): clasificación principal            │  │
│  │ - get_missing_fields(): campos faltantes              │  │
│  │ - Prompt engineering con historial completo           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬─────────────────┐
        │              │              │                 │
        ▼              ▼              ▼                 ▼
┌─────────────┐ ┌──────────────┐ ┌──────────┐ ┌────────────┐
│   Redis     │ │  OpenSearch  │ │  MySQL   │ │  Gemini    │
│  (Cache)    │ │   (RAG/RAD)  │ │ (Metadata)│ │   (LLM)    │
│  24h TTL    │ │  Búsqueda HS │ │          │ │            │
└─────────────┘ └──────────────┘ └──────────┘ └────────────┘
```

---

## Componentes Principales

### 1. **Gradio UI (`ui/gradio_app.py`)**

Interfaz web interactiva construida con Gradio. Implementa tres modos:

#### a) **Chatbot Simplificado (Tab 1)**
- Función: `chat_minimal_validation(message, history, conv_id) -> (response, conversation_id)`
- Características:
  - Interfaz minimalista y rápida
  - Mantiene conversación con `conversation_id` único
  - Maneja cambios de tema automáticamente
  - Respuestas formateadas para legibilidad

#### b) **Validación Chatbot (Tab 2)**
- Función: `chat_response(message, history) -> str`
- Características:
  - Vista completa con evidencia
  - Criterios de clasificación
  - Reglas aplicadas
  - Estado global (legacy)

#### c) **Formulario Clásico (Tab 3)**
- Función: `classify(description, hs_code) -> (candidates, evidence, rgi, missing_fields, warnings)`
- Características:
  - Formulario tradicional punto-a-punto
  - No conversacional
  - Útil para búsquedas rápidas

#### **ConversationState Per conversation_id**

```python
class ConversationState:
    def __init__(self):
        self.last_classification: Dict[str, Any] = None  # Resultado anterior
        self.last_query: str = ""                        # Última consulta
        self.history: List[Tuple[str, str]] = []         # (user, assistant)
    
    def get_history_for_api(self) -> List[Dict]:
        """Convierte historial a formato para backend"""
        return [
            {
                "user": user_msg,
                "assistant": asst_msg,
                "timestamp": datetime.now().isoformat()
            }
            for user_msg, asst_msg in self.history
        ]

# Diccionario indexado por conversation_id
_conversation_states: Dict[str, ConversationState] = {}

def get_conversation_state(conv_id: str) -> ConversationState:
    """Obtiene o crea estado para una conversación"""
    if conv_id not in _conversation_states:
        _conversation_states[conv_id] = ConversationState()
    return _conversation_states[conv_id]
```

---

### 2. **FastAPI Backend (`app/api.py`)**

Servidor que procesa clasificaciones y gestiona conversaciones.

#### **Endpoint Principal: POST /classify**

```python
@app.post("/classify")
async def classify(request: ClassifyRequest):
    """
    Clasifica un producto según su descripción.
    
    Args:
        user_query: Descripción del producto
        conversation_id: UUID de la conversación
        conversation_history: Lista de turnos previos [{user, assistant, timestamp}]
        top_k: Número de candidatos a retornar
    
    Returns:
        {
            "conversation_id": str,
            "top_candidates": [
                {
                    "code": "7208.36",
                    "description": "...",
                    "confidence": 0.95,
                    "evidence": [...]
                }
            ],
            "missing_fields": ["Tipo de acero", "Dimensiones"],
            "applied_rgi": ["RGI 1", "RGI 2"],
            "inclusions": [...],
            "exclusions": [...]
        }
    """
    conv_id = request.conversation_id or str(uuid4())
    
    # Cargar historial previo de Redis
    redis_history = load_history(conv_id)
    
    # Procesar con LLM
    classification = await generator_gemini.generate_label(
        query=request.user_query,
        conversation_history=redis_history,
        context_docs=search_results
    )
    
    # Guardar en Redis
    save_history(conv_id, request.conversation_history)
    
    return {
        "conversation_id": conv_id,
        **classification
    }
```

#### **Flujo de Procesamiento**

1. **Recibir solicitud** con `conversation_id` y `user_query`
2. **Cargar historial de Redis** para contexto
3. **Buscar documentos relevantes** en OpenSearch
4. **Consultar MySQL** para metadatos
5. **Procesar con Gemini** incluyendo:
   - Historial completo de conversación
   - Documentos relevantes del corpus
   - Reglas de interpretación
6. **Guardar resultado** en Redis con TTL 24h
7. **Retornar respuesta** al UI

---

### 3. **LLM Integration (`app/generator_gemini.py`)**

Integración con Google Gemini para procesamiento de lenguaje natural.

#### **Estrategia de Prompt**

El sistema usa un prompt **ingeniería sofisticado** que:

```python
prompt = """
Eres un experto en clasificación arancelaria según el Sistema Armonizado (HS).

INSTRUCCIÓN CRÍTICA: LEE EL HISTORIAL COMPLETO DE CONVERSACIÓN
====================================================================
{conversation_history}

Si el usuario ya ha proporcionado información en mensajes anteriores:
- NO vuelvas a pedir datos que ya fueron dados
- Enriquece tu análisis con el contexto previo
- Sé conciso en las preguntas de seguimiento

CONSULTA ACTUAL DEL USUARIO:
{user_query}

DOCUMENTOS RELEVANTES DEL CORPUS:
{context_docs}

REGLAS GENERALES DE INTERPRETACIÓN (RGI):
{applied_rgi}

Tu tarea:
1. Clasifica el producto mencionado
2. Proporciona los 5 códigos más probables con confianza
3. Lista campos de información faltante (máx 3)
4. Explica criterios de inclusión/exclusión

Responde en JSON con estructura:
{
    "top_candidates": [
        {
            "code": "7208.36",
            "description": "Descripción HS",
            "confidence": 0.95
        }
    ],
    "missing_fields": ["Campo 1", "Campo 2"],
    "applied_rgi": ["RGI aplicada"],
    "inclusions": ["Criterio de inclusión"],
    "exclusions": ["Criterio de exclusión"]
}
"""
```

#### **Soporte de Historial**

El código maneja ambos formatos de historial:

```python
def parse_conversation_history(history):
    """Soporta históricos en ambos formatos (tuple y dict)"""
    formatted = []
    for turn in history:
        if isinstance(turn, dict):
            user_msg = turn.get("user")
            assistant_msg = turn.get("assistant")
        elif isinstance(turn, (list, tuple)) and len(turn) >= 2:
            user_msg, assistant_msg = turn[0], turn[1]
        
        formatted.append(f"Usuario: {user_msg}\nAsistente: {assistant_msg}")
    
    return "\n\n".join(formatted)
```

---

### 4. **Redis (`storage/redis`)**

**Propósito**: Persistencia de conversaciones entre sesiones

#### **Estructura de Datos**

```
Clave: conversation:{conversation_id}
TTL:   86400 segundos (24 horas)
Valor: JSON con estructura:
{
    "conversation_id": "abc123...",
    "turns": [
        {
            "user": "Quiero clasificar láminas de acero",
            "assistant": "¿Puedes confirmar el tipo?",
            "timestamp": "2025-12-16T10:30:00"
        },
        {
            "user": "Es acero laminado en caliente",
            "assistant": "¿Cuál es el espesor?",
            "timestamp": "2025-12-16T10:31:00"
        }
    ]
}
```

#### **Operaciones**

```python
def load_history(conversation_id: str) -> List[Dict]:
    """Carga historial de Redis"""
    key = f"conversation:{conversation_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)["turns"]
    return []

def save_history(conversation_id: str, turns: List[Dict]):
    """Guarda historial en Redis con TTL 24h"""
    key = f"conversation:{conversation_id}"
    redis_client.setex(
        key,
        86400,  # 24 horas
        json.dumps({
            "conversation_id": conversation_id,
            "turns": turns
        })
    )
```

---

### 5. **OpenSearch (`storage/opensearch`)**

**Propósito**: Búsqueda semántica de documentos arancelarios

#### **Estructura de Índice**

```
Índice: arancel_corpus
Documentos:
{
    "id": "WCO_notes_chapter7_001",
    "content": "Las láminas de acero se clasifican en la partida 7208...",
    "source": "WCO_notes",
    "chapter": "72",
    "keywords": ["acero", "lámina", "laminada"]
}
```

#### **Búsqueda en Flujo de Clasificación**

```python
def retrieve_context(query: str, top_k: int = 5) -> List[Dict]:
    """Busca documentos relevantes para la consulta"""
    results = opensearch_client.search(
        index="arancel_corpus",
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content", "keywords"]
                }
            },
            "size": top_k
        }
    )
    
    return [
        {
            "source": hit["_source"]["source"],
            "content": hit["_source"]["content"],
            "score": hit["_score"]
        }
        for hit in results["hits"]["hits"]
    ]
```

---

### 6. **MySQL (`storage/mysql`)**

**Propósito**: Almacenamiento de metadatos y catálogos

#### **Tablas Principales**

```sql
-- Tabla de partidas HS
CREATE TABLE hs_codes (
    id INT PRIMARY KEY,
    code VARCHAR(10) UNIQUE,
    description_es TEXT,
    chapter INT,
    section VARCHAR(5),
    notes TEXT,
    created_at TIMESTAMP
);

-- Tabla de productos clasificados
CREATE TABLE product_classifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(36),
    user_query TEXT,
    classified_code VARCHAR(10),
    confidence FLOAT,
    created_at TIMESTAMP
);

-- Tabla de metadatos de consultas
CREATE TABLE query_metadata (
    id INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(36),
    product_category VARCHAR(50),
    missing_info JSON,
    timestamp TIMESTAMP
);
```

---

## Flujo de Conversación

### **Flujo Completo: Consulta → Clasificación → Persistencia**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario escribe en UI                                    │
│    Input: "Quiero clasificar láminas de acero"              │
│    Estado: Nuevo conversation_id generado (UUID)            │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 2. UI - chat_minimal_validation()                           │
│    - Detecta saludos / resets / cambios de tema             │
│    - Obtiene ConversationState para este conversation_id    │
│    - Si primer mensaje: envía directamente                  │
│    - Si follow-up y misma categoría: enriquece             │
│    - Si categoría diferente: resetea estado                │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 3. Construcción de Payload para API                         │
│    {                                                        │
│      "user_query": "Quiero clasificar láminas de acero",   │
│      "conversation_id": "a1b2c3d4...",                     │
│      "conversation_history": [                             │
│        {                                                    │
│          "user": "...",                                    │
│          "assistant": "...",                               │
│          "timestamp": "2025-12-16T10:30:00"                │
│        }                                                    │
│      ],                                                     │
│      "top_k": 5                                            │
│    }                                                        │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 4. Backend - POST /classify                                 │
│    - Cargar historial previo de Redis                      │
│    - Buscar documentos en OpenSearch                        │
│    - Consultar metadatos en MySQL                          │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 5. LLM - Gemini Inference                                   │
│    - Construir prompt con historial completo               │
│    - Incluir documentos relevantes                         │
│    - Incluir reglas de interpretación                      │
│    - Enviar a Gemini API                                  │
│    - Parsear respuesta JSON                                │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 6. Persistencia - Redis                                     │
│    - Guardar nuevo turno en historial                      │
│    - Clave: conversation:{conversation_id}                 │
│    - TTL: 24 horas                                         │
│    - Valor: JSON completo con turno nuevo                 │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 7. Formateo de Respuesta para UI                            │
│    - Convertir JSON a Markdown                              │
│    - Mostrar códigos candidatos                             │
│    - Listar campos faltantes                                │
│    - Mostrar criterios de clasificación                    │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 8. Actualización de UI                                      │
│    - Mostrar respuesta formateada                           │
│    - Guardar en ConversationState local                    │
│    - Mantener conversation_id en gr.State                  │
│    - Listo para próximo mensaje                            │
└─────────────────────────────────────────────────────────────┘
```

### **Flujo de Cambio de Tema**

```
Conversación 1: Usuario pregunta sobre VEHÍCULOS
├─ Query: "Quiero clasificar un automóvil"
├─ conversation_id: "uuid-1"
├─ _detect_category() → "vehicle"
└─ Estado guardado: vehículos

                    ↓

Usuario pregunta sobre ACERO (misma sesión)
├─ Query: "Láminas de acero"
├─ conversation_id: "uuid-1" (heredado)
├─ _detect_category() → "metal"
├─ Compara: "vehicle" != "metal" → CAMBIO DETECTADO ✓
├─ Acciones:
│  ├─ reset_conversation_state("uuid-1")
│  ├─ conversation_id = uuid4().hex  → nuevo ID
│  ├─ conv_state = get_conversation_state(nuevo_id)
│  └─ Envía query LIMPIA sin enriquecimiento
└─ Respuesta: Preguntas sobre acero (SIN contaminar)
```

---

## Gestión de Contexto y Persistencia

### **Aislamiento de Conversación**

El sistema implementa **aislamiento completo** entre conversaciones:

```python
# Cada conversation_id tiene su propia instancia
_conversation_states: Dict[str, ConversationState] = {
    "uuid-1": ConversationState(),  # Conversación A
    "uuid-2": ConversationState(),  # Conversación B
    "uuid-3": ConversationState(),  # Conversación C
}

# Obtener estado específico (no compartido)
conv_state_a = get_conversation_state("uuid-1")
conv_state_b = get_conversation_state("uuid-2")

# Cambios en A no afectan a B
conv_state_a.last_query = "automóvil"
print(conv_state_b.last_query)  # Vacío, no afectado
```

### **Persistencia en Redis**

Cuando usuario cierra sesión o cambia de pestaña:

```
1. Conversación se guarda en Redis con TTL 24h
2. Usuario regresa a la misma URL
3. conversation_id se restaura (si estaba guardado en URL)
4. Sistema carga historial de Redis
5. Conversación continúa sin pérdida de contexto
```

### **Enriquecimiento Inteligente**

```python
# En chat_minimal_validation()

# Detectar si es completar información
last_missing = conv_state.last_classification.get("missing_fields", [])
is_completing = len(msg.split()) <= 15 and \
                any(keyword in msg.lower() for keyword in extract_keywords(last_missing))

if is_completing:
    # Enriquecer: "Láminas de acero. 10 mm de espesor"
    enriched = f"{conv_state.last_query}. {msg}"
else:
    # Nueva consulta independiente
    enriched = msg
```

---

## Detalles Técnicos

### **Detección de Categoría**

```python
def _detect_category(text: str) -> Optional[str]:
    """Heurística para detectar categoría de producto"""
    t = text.lower()
    
    # Vehículos
    if any(w in t for w in ["automóvil", "auto", "motor", "coche", "camión"]):
        return "vehicle"
    
    # Metales
    if any(w in t for w in ["acero", "lámina", "hierro", "aluminio", "cobre"]):
        return "metal"
    
    # Textiles
    if any(w in t for w in ["textil", "tela", "algodón", "ropa", "prenda"]):
        return "textile"
    
    # Electrónica
    if any(w in t for w in ["smartphone", "laptop", "electrónico", "dispositivo"]):
        return "electronics"
    
    # Alimentos
    if any(w in t for w in ["alimento", "comida", "carne", "fruta", "café"]):
        return "food"
    
    return None
```

### **Manejo de Formato de Historial**

El sistema soporta historial en múltiples formatos:

```python
# Formato desde UI (tuples)
history_ui = [
    ("Usuario: ¿Qué falta?", "Asistente: Respuesta"),
    ("Usuario: 10mm", "Asistente: Respuesta 2")
]

# Formato en Redis/API (dicts)
history_api = [
    {
        "user": "¿Qué falta?",
        "assistant": "Respuesta",
        "timestamp": "2025-12-16T10:30:00"
    },
    {
        "user": "10mm",
        "assistant": "Respuesta 2",
        "timestamp": "2025-12-16T10:31:00"
    }
]

# Conversión automática
def get_history_for_api(self):
    return [
        {
            "user": user,
            "assistant": assistant,
            "timestamp": datetime.now().isoformat()
        }
        for user, assistant in self.history
    ]
```

### **Prompt Engineering Avanzado**

El sistema construye prompts dinámicos que incluyen:

```
1. Instrucción crítica: LEE EL HISTORIAL COMPLETO
2. Historial formateado de todos los turnos previos
3. Consulta actual del usuario
4. Documentos relevantes de OpenSearch
5. Reglas generales de interpretación
6. Estructura esperada de JSON de salida
7. Restricciones: "NO vuelvas a pedir datos que ya fueron dados"
```

---

## Ejemplos de Uso

### **Ejemplo 1: Consulta Simple**

```
Usuario: Quiero clasificar láminas de acero

[Sistema detecta: "acero" → categoría "metal"]
[Busca documentos sobre acero en OpenSearch]
[Envía a Gemini con contexto]

Sistema: 🔍 Necesito más información para clasificar
¿Puedes confirmar tipo de acero (inoxidable, al carbono, etc.)?

También ayuda:
- Proceso de fabricación (laminadas en caliente/frío)
- Dimensiones específicas (espesor, ancho, largo)
```

### **Ejemplo 2: Enriquecimiento de Contexto**

```
Usuario: Quiero clasificar un automóvil

Sistema: ¿Puedes confirmar tipo (turismo, SUV, etc.)?

Usuario: Es de pasajeros

[Sistema detecta: misma categoría "vehicle"]
[Enriquece: "automóvil. Es de pasajeros"]
[Envía a Gemini con contexto enriquecido]

Sistema: ¿Cuál es el tipo específico (sedan, hatchback, etc.)?
```

### **Ejemplo 3: Cambio de Tema**

```
Usuario: Quiero clasificar un automóvil
[conversation_id: uuid-1, categoría: vehicle]

Sistema: ¿Tipo específico?

Usuario: Ahora quiero láminas de acero

[Detecta: "acero" → categoría "metal"]
[Compara: "vehicle" ≠ "metal" → CAMBIO]
[Resetea estado de uuid-1]
[Genera nuevo conversation_id: uuid-2]
[Inicia conversación NUEVA sin contaminación]

Sistema: 🔍 ¿Puedes confirmar tipo de acero?
(No pregunta sobre tipo de automóvil)
```

### **Ejemplo 4: Persistencia en Redis**

```
Sesión 1:
┌─────────────────────┐
│ Usuario: "Acero"    │
│ Respuesta: "..."    │
│ Guardado en Redis:  │
│ Key: conversation:  │
│ abc123              │
│ TTL: 24h            │
└─────────────────────┘

[Usuario cierra navegador]
[Espera 1 hora]

Sesión 2:
┌─────────────────────────────────┐
│ URL contiene conversation_id    │
│ Sistema carga de Redis          │
│ Historial restaurado            │
│ Usuario: "¿Cuáles son opciones?"│
│ Respuesta usa contexto previo   │
│ (SIN preguntar "¿qué es acero?")│
└─────────────────────────────────┘
```

---

## Troubleshooting

### **Problema: Sistema re-pregunta información ya proporcionada**

**Causa**: `ConversationState` global contaminado

**Solución**: 
- Sistema ahora usa `get_conversation_state(conv_id)`
- Cada conversación tiene estado independiente
- Verificar que `conversation_id` se pasa correctamente

### **Problema: Cambio de tema no se detecta**

**Causa**: Función `_detect_category()` no reconoce nueva categoría

**Solución**:
- Revisar que la palabra clave está en diccionario de categorías
- Agregar palabras clave faltantes
- Ejemplo: "láminas de acero" contiene "acero" → categoría "metal"

### **Problema: Historial no persiste entre sesiones**

**Causa**: Redis no está guardando o `conversation_id` no se pasa

**Solución**:
1. Verificar que Redis está corriendo: `docker ps | grep redis`
2. Verificar que `conversation_id` está en `gr.State`
3. Verificar TTL: `redis-cli TTL conversation:abc123`

### **Problema: Respuestas lentas**

**Causa**: Gemini API latency o búsqueda en OpenSearch

**Solución**:
- Reducir `top_k` en búsqueda (default 5)
- Optimizar índice de OpenSearch
- Usar caché en Redis para queries similares

### **Problema: Enriquecimiento incorrecto**

**Causa**: Lógica de `should_enrich` activada incorrectamente

**Solución**:
```python
# Revisar condiciones
- is_short_message = len(msg.split()) <= 15
- same_category = (_detect_category(last_query) == _detect_category(msg))
- should_enrich = is_short_message or same_category
```

---

## Flujo Completo en Diagrama

```
┌─────────────────────────────────────────────────────────────┐
│                    INICIO DE SESIÓN                         │
│              conversation_id = uuid4().hex                  │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────▼────────────────┐
    │  ¿Mensaje nuevo?             │
    └────────────┬────────────────┘
                 │
        ┌────────▼────────┐
        │ Sí      No       │
        │                 │
        ▼                 ▼
   ┌────────┐        ┌─────────────┐
   │Envío   │        │Hay contexto │
   │directo │        │previo?      │
   └────────┘        └─────────────┘
                     ├─ No → envío
                     └─ Sí ↓
                        ┌──────────────┐
                        │Detectar      │
                        │categoría     │
                        └──────────────┘
                             │
                    ┌────────┴────────┐
                    │ ¿Cambio de tema?│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Sí      No       │
                    │                 │
                    ▼                 ▼
          ┌──────────────┐    ┌──────────────┐
          │Reset Estado  │    │Enriquecer    │
          │Nuevo conv_id │    │query con     │
          └──────────────┘    │contexto      │
                              └──────────────┘
                                    │
                    ┌───────────────┘
                    │
                    ▼
         ┌────────────────────┐
         │Enviar a Backend    │
         │/classify           │
         └────────┬───────────┘
                  │
         ┌────────▼───────────┐
         │Procesar con Gemini │
         │+ OpenSearch        │
         │+ MySQL             │
         └────────┬───────────┘
                  │
         ┌────────▼───────────┐
         │Guardar en Redis    │
         │TTL: 24h            │
         └────────┬───────────┘
                  │
         ┌────────▼───────────┐
         │Retornar resultado  │
         │al UI               │
         └────────┬───────────┘
                  │
         ┌────────▼───────────┐
         │Mostrar formateado  │
         │en Gradio           │
         └────────┬───────────┘
                  │
         ┌────────▼───────────┐
         │¿Más mensajes?      │
         └────────┬───────────┘
                  │
         ┌────────▼─────────┐
         │ Sí ───────┐ No   │
         │           │      │
         │      ┌────▼──┐   │
         │      │Guardar│   │
         │      │en Redis   │
         │      └─────────┘  │
         │           │       │
         └───────────▼───────┘
                  │
                  ▼
             [FIN DE SESIÓN]
```

---

## Resumen de Características Clave

| Característica | Implementación | Beneficio |
|---|---|---|
| **Aislamiento de contexto** | `Dict[conversation_id, ConversationState]` | Evita contaminación entre conversaciones |
| **Detección de cambio de tema** | `_detect_category()` con cambio automático | Resetea contexto cuando usuario cambia de producto |
| **Persistencia** | Redis con TTL 24h | Conversación continúa entre sesiones |
| **Historial dual-format** | Soporta tuple y dict | Compatible con UI y backend |
| **Enriquecimiento inteligente** | Condiciones basadas en longitud y categoría | Mantiene contexto sin contaminar |
| **Prompt engineering** | Instrucción crítica + historial completo | LLM entiende contexto previo |
| **Búsqueda semántica** | OpenSearch + MySQL | Encuentra documentos relevantes rápidamente |
| **Interfaz conversacional** | Gradio ChatInterface | UX intuitiva y moderna |

---

## Conclusión

El **Asistente de Clasificación Arancelaria** es un sistema robusto que combina:

✅ **Conversación inteligente** con aislamiento de contexto  
✅ **Persistencia** de sesiones entre navegadas  
✅ **Detección automática** de cambios de tema  
✅ **Enriquecimiento contextual** sin contaminación  
✅ **Integración LLM** con prompt engineering avanzado  
✅ **Búsqueda semántica** en corpus arancelario  
✅ **Interfaz moderna** y responsive  

Cada componente está optimizado para proporcionar una experiencia conversacional fluida donde el usuario puede describir productos en lenguaje natural y recibir clasificaciones precisas con contexto persistente.
