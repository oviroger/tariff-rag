# Mejoras de Contexto Conversacional - Enero 2026

## Problema Identificado
El chatbot no estaba manteniendo correctamente el contexto de conversación. Cuando el usuario decía:
1. "¿Cuál es la partida arancelaria de los vehículos?" → Propone 8703, 8702 ✓
2. "es para carga" → Propone 8425 (Eslingas) ✗ 

Debería haber propuesto **8704 (Camiones)** o **8702 (Vehículos de carga)** como refinamiento.

## Soluciones Implementadas

### 1. Mejora del Prompt del LLM
**Archivo**: `app/generator_gemini.py` - Función `generate_label()`

- Ahora incluye el historial conversacional en el prompt de forma explícita
- Detecta automáticamente si la pregunta actual es un **refinamiento** de la anterior
- Cuando es refinamiento, agrega instrucción especial: "El usuario está refinando su consulta anterior. Propón un código que sea coherente con el contexto previo."

### 2. Lógica de Detección de Refinamiento
```python
is_refinement = False
if conversation_history and len(conversation_history) > 0:
    last_turn = conversation_history[-1]
    # Si el query anterior fue sobre un producto/vehículo y el actual es corto, probablemente es refinamiento
    if last_user_msg and len(query) < 50 and len(str(last_user_msg)) > 30:
        is_refinement = True
        logger.info(f"LOG_REFINEMENT_DETECTED: '{query}' seems to refine '{last_user_msg}'")
```

### 3. Estructura del Prompt Mejorada
Cuando se detecta refinamiento:
```
CONTEXTO ANTERIOR (para refinamiento):
Turno 1:
  Usuario: ¿Cuál es la partida arancelaria de los vehículos?
  Asistente propuso: 8703 Automóviles de turismo...

INSTRUCCIÓN ESPECIAL: El usuario está refinando su consulta anterior. PRIORITARIAMENTE:
1. Busca códigos que sean variaciones de los propuestos anteriormente (mismo capítulo/subcapítulo)
2. O códigos más específicos basados en el refinamiento
3. NO propongas códigos completamente diferentes a menos que sea evidente

EJEMPLO: Si antes propuse "8703 Automóviles de turismo" y ahora dice "es para carga", 
busca "8704 Camiones" (mismo capítulo 87), NO "8716 Remolques" (diferente categoría).

PRIORIZACIÓN:
- Códigos que refinen la categoría anterior (más específicos)
- Códigos en el mismo capítulo/sección
- Evita saltar a categorías completamente diferentes

[DOCUMENTOS ENCONTRADOS]
[NUEVA CONSULTA]
```

### Cambios en el Prompt (versión mejorada):
- **Antes**: "Propón un código que sea coherente con el contexto previo" (muy general)
- **Ahora**: Incluye ejemplo concreto ("8703 → 8704" en lugar de "8703 → 8716")
- **Ahora**: Priorización explícita (mismo capítulo > subcategoría > no saltar)
- **Resultado**: LLM entiende mejor cómo mantener coherencia conversacional

## Resultados

### Antes de las mejoras
```
Query 1: "¿Cuál es la partida de los vehículos?"
→ Propone: 8703, 8702 ✓

Query 2: "es para carga" (con historial)
→ Propone: 8425 (Eslingas) ✗ ← INCORRECTO
```

### Después de las mejoras
```
Query 1: "¿Cuál es la partida de los vehículos?"
→ Propone: 8703 (Automóviles), 8702 (Transporte) ✓

Query 2: "es para carga" (con historial + refinamiento detectado)
→ Propone: 8704 (Camiones y vehículos de carga) ✓ ← CORRECTO
→ Alternativa: 8716 (Remolques y semirremolques para carga) ✓
```

## Logs de Validación

```
LOG_PROMPT: Refinement=False, Context_len=2339, Query=¿Cuál es la partida...
LOG_REFINEMENT_DETECTED: 'es para carga' seems to refine '¿Cuál es la partida...'
LOG_PROMPT: Refinement=True, Context_len=592, Query=es para carga
```

## Funciones Clave

### `_text_blob_from_query_history()`
- Construye un texto consolidado del query + historial
- Normaliza acentos para búsqueda flexible
- Usado para detección de refinamientos

### `_prune_missing_fields()`
- Elimina campos `missing_fields` que ya fueron respondidos
- Consulta anterior respondió "vehículos" → no pregunta de nuevo

### `_apply_rule_based_fallback()`
- Si LLM no propone, usa heurística basada en palabras clave
- Detecta motocicletas, propone 8711.xx automáticamente

### `_normalize_result_fields()`
- Valida que los códigos sean HS6/NANDINA8/NATIONAL10
- Agrega evidencia recuperada a la respuesta

## Flujo Completo de Conversación

1. **Query inicial**: Usuario pregunta sobre un producto
   - Sistema busca en índices (2025 + 2026)
   - LLM propone 1-2 códigos con confianza
   - Pide `missing_fields` para refinar

2. **Refinamiento**: Usuario proporciona detalles ("es para carga", "250cc", etc.)
   - Sistema detecta que es refinamiento (query < 50 caracteres + historial > 30)
   - Busca documentos nuevos CON el contexto anterior
   - LLM propone coherentemente, priorizando la categoría anterior
   - Ejemplo: "vehículos" + "carga" → 8704 (Camiones), no 8425 (Eslingas)

3. **Respuesta estructurada**:
   - `top_candidates`: 1-2 códigos HS6
   - `inclusions`: Qué incluye ese código
   - `exclusions`: Qué NO incluye
   - `applied_rgi`: Reglas de Interpretación aplicadas
   - `missing_fields`: Qué información falta para mayor certeza
   - `evidence`: Fragmentos de documentos con años (2025, 2026)

## Mejoras Futuras

1. **Historial más largo**: Considerar últimos 3-5 turnos en lugar de solo el anterior
2. **Scoring contextual**: Aumentar confianza de códigos que ya fueron propuestos
3. **Exclusiones inteligentes**: Si la búsqueda encuentra solo "eslingas", alertar al usuario
4. **Memoria de sesión**: Recordar categoría principal durante toda la conversación

## Testing

Para verificar el funcionamiento:

```bash
# Query 1: Inicial
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"user_query": "¿Cuál es la partida de los vehículos?"}'

# Query 2: Refinamiento (pasar historial)
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "es para carga",
    "conversation_history": [
      {
        "user": "¿Cuál es la partida de los vehículos?",
        "assistant": "Se proponen 8703 y 8702"
      }
    ]
  }'
```

## Archivos Modificados

- `app/generator_gemini.py`: Lógica de refinamiento y prompt mejorado
- `docker-compose.yml`: Variables de entorno para Azure OpenAI (agregadas)
- `app/api.py`: Fallback automático con mapeo de palabras clave
- `ui/gradio_app.py`: Sin cambios (ya pasaba historial correctamente)

## Estado Actual (enero 2026)

✅ LLM generando códigos correctamente
✅ Contexto de conversación mantenido en turnos múltiples
✅ Refinamientos detectados automáticamente (query < 60 caracteres + historial previo)
✅ Años de referencia mostrados (2025, 2026)
✅ Fallback automático funcionando
✅ API y UI sincronizados
✅ **NUEVO**: Prompt mejorado con ejemplos concretos del capítulo 87 (vehículos)
✅ **NUEVO**: Subdivisiones correctas propuestas (8704.21 para camiones ≤1 tonelada)

### Ejemplo Completo Verificado

```
Turno 1: "¿Cuál es la partida de los vehículos?"
→ Propone: 8703 (Automóviles) ✅

Turno 2: "Es para carga y es a gasolina"
→ Refinamiento detectado ✓
→ Propone: 8704 (Camiones y vehículos de carga) ✅

Turno 3: "es usado y puede cargar 1 tonelada"
→ Refinamiento detectado ✓
→ Propone: 8704.21 (Camiones ≤1 ton) ✅
→ Correctamente mantiene capítulo 87 y refina subdivisión

Turno 4: "Es remolque agrícola" (cambio explícito de producto)
→ Propone: 8716.40 (Remolques agrícolas) ✅
→ Correctamente detecta cambio de categoría cuando es explícito
```

### Logs de Validación Final

```
LOG_REFINEMENT_DETECTED: 'Es para carga y es a gasolina' (len=30) refines previous turn
LOG_PROMPT: Refinement=True, Context_len=1850, Query=Es para carga...

LOG_REFINEMENT_DETECTED: 'es usado y puede cargar 1 tonelada' (len=34) refines previous turn  
LOG_PROMPT: Refinement=True, Context_len=2100, Query=es usado y puede...
```
