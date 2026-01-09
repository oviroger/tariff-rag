# Guía: Soporte Multi-Año en el Chatbot Arancelario

## Resumen de Cambios

Se ha implementado soporte para consultar información de múltiples años (2025, 2026, etc.) en el chatbot. El sistema ahora puede:

1. ✅ Acceder a múltiples índices de OpenSearch simultáneamente
2. ✅ Filtrar resultados por año específico
3. ✅ Mostrar el año correspondiente a cada respuesta
4. ✅ Mantener compatibilidad hacia atrás (consultas sin filtro de año)

## Pasos para Configurar

### Paso 1: Crear el Índice de 2026

Primero, debes crear el índice `tariff_fragments_2026` en OpenSearch copiando los datos de 2025:

```bash
cd d:\MAESTRIA\ -\ copia\tariff-rag
python scripts/create_2026_index.py
```

**Qué hace:**
- Crea un nuevo índice llamado `tariff_fragments_2026`
- Copia todos los documentos de `tariff_fragments_2025`
- Añade el campo `year: 2026` a cada documento
- Verifica que la copia se completó correctamente

**Salida esperada:**
```
===== Copiando índice con metadata de año =====

Origen: tariff_fragments_2025
Destino: tariff_fragments_2026
Año: 2026

[1/4] Verificando índice fuente: tariff_fragments_2025...
✓ Índice fuente encontrado
[2/4] Obteniendo configuración...
[3/4] Creando índice destino: tariff_fragments_2026...
✓ Índice tariff_fragments_2026 creado
[4/4] Copiando documentos...
  Copiados: 500...
  Copiados: 1000...

=== COPIA COMPLETADA ===
✓ Documentos copiados: XXXX
✗ Errores: 0
Índice origen: tariff_fragments_2025
Índice destino: tariff_fragments_2026
Año asignado: 2026

Verificación:
  Documentos en tariff_fragments_2025: XXXX
  Documentos en tariff_fragments_2026: XXXX
✓ Copia verificada exitosamente
```

### Paso 2: Ingestar Datos Reales de 2026 (Opcional)

Si tienes un archivo JSON con datos reales de 2026:

```bash
python scripts/ingest_2026_data.py data/afr_done/Arancel_2026.json
```

**Nota:** Primero debes preparar el archivo JSON en la estructura correcta.

### Paso 3: Reiniciar el Backend

```bash
docker-compose restart api
```

## Uso en el Chatbot

### Opción A: Consultar Todos los Años (Defecto)

**Request:**
```json
{
  "user_query": "Laptop Dell XPS 13",
  "conversation_id": "conv_123"
}
```

**Resultado:** Busca en `tariff_fragments_2025,tariff_fragments_2026`

### Opción B: Consultar Solo 2025

**Request:**
```json
{
  "user_query": "Laptop Dell XPS 13",
  "conversation_id": "conv_123",
  "years": [2025]
}
```

**Resultado:** Busca solo en `tariff_fragments_2025`

### Opción C: Consultar Solo 2026

**Request:**
```json
{
  "user_query": "Laptop Dell XPS 13",
  "conversation_id": "conv_123",
  "years": [2026]
}
```

**Resultado:** Busca solo en `tariff_fragments_2026`

### Opción D: Consultar Años Específicos

**Request:**
```json
{
  "user_query": "Laptop Dell XPS 13",
  "conversation_id": "conv_123",
  "years": [2025, 2026]
}
```

**Resultado:** Busca en ambos índices (esto es lo mismo que Opción A)

## Respuesta con Metadatos de Año

La respuesta del API ahora incluye el año en los fragmentos de evidencia:

```json
{
  "top_candidates": [
    {
      "code": "8471.30",
      "description": "Máquinas portátiles de procesamiento de datos",
      "confidence": 0.95,
      "level": "HS6"
    }
  ],
  "evidence": [
    {
      "fragment_id": "afr_2025_1234",
      "text": "Las máquinas portátiles...",
      "year": 2025,
      "score": 0.92
    },
    {
      "fragment_id": "afr_2026_5678",
      "text": "Máquinas portátiles de computadora...",
      "year": 2026,
      "score": 0.88
    }
  ]
}
```

## Estructura de Índices

Después de ejecutar los scripts, tendrás:

```
OpenSearch
├── tariff_fragments_2025 (original)
│   └── ~XXXX documentos con year: 2025
└── tariff_fragments_2026 (nuevo)
    └── ~XXXX documentos con year: 2026
```

## Verificación

Para verificar que todo está configurado correctamente:

```bash
# Verificar que ambos índices existen
curl -s http://localhost:9200/_cat/indices | grep tariff_fragments

# Contar documentos por índice
curl -s -X GET http://localhost:9200/tariff_fragments_2025/_count
curl -s -X GET http://localhost:9200/tariff_fragments_2026/_count

# Verificar que los documentos tienen el campo 'year'
curl -s -X GET "http://localhost:9200/tariff_fragments_2026/_search?size=1" | jq '.hits.hits[0]._source.year'
```

## Variables de Entorno

Las siguientes variables están configuradas en `app/schemas.py`:

```python
opensearch_index: str = "tariff_fragments"  # Índice por defecto (legado)
opensearch_indices: str = "tariff_fragments_2025,tariff_fragments_2026"  # Índices multi-año
```

Puedes cambiar esto en `.env` o en la configuración de Docker si necesitas añadir más años.

## Troubleshooting

### "Index not found"
- Ejecuta: `python scripts/create_2026_index.py`
- Verifica: `curl http://localhost:9200/_cat/indices`

### "Field 'year' not found"
- Algunos documentos antiguos pueden no tener el campo
- Solución: Re-ingestar con `python scripts/ingest_2026_data.py`

### Resultados sin año
- Verifica que el índice tiene documentos con campo `year`
- Ejecuta el script de verificación arriba

## Cambios de Código

### Archivos Modificados:
1. **app/schemas.py**
   - Añadido `year` a `Fragment`
   - Añadido `year` a `EvidenceFragment`
   - Añadido `years` a `ClassifyRequest`
   - Añadido `opensearch_indices` a `Settings`

2. **app/os_retrieval.py**
   - Actualizado `retrieve_fragments()` con parámetro `years`
   - Actualizado `hybrid_search_with_fallback()` con parámetro `years`

3. **app/api.py**
   - Añadido soporte para parámetro `years` en `/classify`

### Archivos Nuevos:
1. **scripts/create_2026_index.py** - Copia índice 2025 → 2026 con año
2. **scripts/ingest_2026_data.py** - Ingesta datos JSON 2026 reales
3. **PLAN_MULTI_YEAR.md** - Plan técnico
4. **GUIDE_MULTI_YEAR.md** - Esta guía

## Próximos Pasos (Opcional)

1. **UI de Gradio:** Añadir selector de años en `ui/gradio_app.py`
2. **Alias:** Crear alias de OpenSearch para simplificar `tariff_fragments_*`
3. **Más años:** Repetir los pasos para 2027, 2028, etc.
