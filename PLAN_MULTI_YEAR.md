# Plan: Soporte Multi-Año en Chatbot Arancelario

## Objetivo
Permitir al chatbot acceder a información de múltiples años (2025, 2026, etc.) y mostrar el año correspondiente en las respuestas.

## Cambios Realizados

### 1. **Schemas** (`app/schemas.py`)
- ✅ Añadido campo `year: Optional[int]` a `Fragment`
- ✅ Añadido campo `year: Optional[int]` a `EvidenceFragment`
- ✅ Añadido `opensearch_indices` en Settings para lista de índices
- ✅ Añadido `years: Optional[List[int]]` a `ClassifyRequest` para filtrar por años

### 2. **Retrieval** (`app/os_retrieval.py`)
- ✅ Actualizado `retrieve_fragments()` para soportar múltiples índices y filtro de años
- ⏳ Necesita: Actualizar `hybrid_search_with_fallback()` para pasar parámetro `years`

### 3. **API** (`app/api.py`)
- ✅ Importado `List` del typing
- ✅ Añadido `years` a `ClassifyRequest`
- ⏳ Necesita: Actualizar llamada a `hybrid_search_with_fallback()` pasando `req.years`
- ⏳ Necesita: Asegurar que los hits incluyen el campo `year`

### 4. **Índices en OpenSearch**
- ⏳ Necesita: Ejecutar script `scripts/create_2026_index.py` para crear índice con datos 2026
- ⏳ Antes: Copiar datos arancelarios 2026 a `tariff_fragments_2026`

### 5. **UI/Gradio** (`ui/gradio_app.py`)
- ⏳ Necesita: Añadir selector de años (2025, 2026, Ambos)
- ⏳ Necesita: Mostrar año en las respuestas

## Próximas Tareas

1. Actualizar `hybrid_search_with_fallback()` en `os_retrieval.py`
2. Modificar endpoint `/classify` en `api.py` para pasar años
3. Ejecutar script para crear índice 2026
4. Actualizar UI de Gradio

## Uso

### Consulta con años específicos (solo 2025):
```json
{
  "user_query": "Laptop Dell XPS 13",
  "years": [2025]
}
```

### Consulta con múltiples años (2025 y 2026):
```json
{
  "user_query": "Laptop Dell XPS 13",
  "years": [2025, 2026]
}
```

### Consulta sin filtro (todos los años disponibles):
```json
{
  "user_query": "Laptop Dell XPS 13"
}
```

## Respuesta Esperada
```json
{
  "top_candidates": [...],
  "evidence": [
    {
      "fragment_id": "...",
      "text": "...",
      "year": 2025,
      "score": 0.95
    },
    {
      "fragment_id": "...",
      "text": "...",
      "year": 2026,
      "score": 0.93
    }
  ]
}
```
