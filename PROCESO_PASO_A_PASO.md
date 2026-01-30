# Proceso Paso a Paso: Sistema de Clasificación Arancelaria

## Caso de Uso: Clasificación de un Autobús

---

## ETAPA 1: TURNO 1 - CONSULTA INICIAL

### 1.1 INPUT DEL USUARIO
```
Usuario: "Necesito clasificar un autobús que voy a importar"
```

### 1.2 PROCESOS INTERNOS

#### Step 1: `generate_label()` - LLAMADA PRINCIPAL
```python
generate_label(
    query="Necesito clasificar un autobús que voy a importar",
    context_docs=[],  # Vacío inicialmente (sin RAG)
    max_candidates=5,
    conversation_history=None  # Primer turno, sin historial
)
```

#### Step 2: `_build_evidence_from_os_hits()` - CONSTRUIR EVIDENCIA
```python
# Entrada: context_docs vacío
# Salida: evidence = []

LOG: "LOG_TEXT_BLOB_RAW: 'necesito clasificar un autobus que voy a importar'"
```

#### Step 3: `_text_blob_from_query_history()` - NORMALIZAR TEXTO
```python
# Entrada:
# - query: "Necesito clasificar un autobús que voy a importar"
# - conversation_history: None

# Proceso de normalización:
# 1. Convertir a lowercase
# 2. Remover acentos: autobús → autobus
# 3. Remover caracteres especiales

# Salida (normalizado):
text_blob_norm = "necesito clasificar un autobus que voy a importar"

LOG: "LOG_TEXT_BLOB_RAW: 'necesito clasificar un autobus que voy a importar'"
LOG: "LOG_TEXT_BLOB_NORMALIZED: 'necesito clasificar un autobus que voy a importar'"
```

#### Step 4: LLAMADA A AZURE OPENAI
```
[RAG + LLM] Enviar a Azure OpenAI con prompt:
- Sistema: SYSTEM_INSTRUCTIONS (instrucciones de clasificación)
- Usuario: "Necesito clasificar un autobús que voy a importar"
- Contexto RAG: (vacío)

RESULTADO DEL LLM:
{
  "top_candidates": [
    {
      "code": "8702.10",
      "description": "Autobuses con motor de émbolos, cilindrada ≤ 5000 cc",
      "confidence": 0.58,
      "level": "HS6"
    },
    {
      "code": "8702.90",
      "description": "Autobuses; otros",
      "confidence": 0.42,
      "level": "HS6"
    }
  ],
  "missing_fields": [
    "¿Cuántas personas puede transportar?",
    "¿Qué tipo de motor?"
  ],
  "applied_rgi": ["RGI 1"],
  "inclusions": ["Es un autobús (capítulo 87, posición 8702)"],
  "exclusions": []
}
```

#### Step 5: `_normalize_result_fields()` - NORMALIZAR RESULTADO
```python
# Validar estructura de resultado
LOG: "Normalizar candidatos..."

# Verificar niveles (HS6, NANDINA8, NATIONAL10)
# Agregar años por defecto: [2025, 2026]

RESULTADO:
{
  "top_candidates": [
    {
      "code": "8702.10",
      "description": "Autobuses con motor de émbolos, cilindrada ≤ 5000 cc",
      "confidence": 0.58,
      "level": "HS6",
      "years": [2025, 2026]
    },
    {
      "code": "8702.90",
      "description": "Autobuses; otros",
      "confidence": 0.42,
      "level": "HS6",
      "years": [2025, 2026]
    }
  ],
  "missing_fields": [
    "¿Cuántas personas puede transportar?",
    "¿Qué tipo de motor?"
  ],
  "applied_rgi": ["RGI 1"],
  "inclusions": ["Es un autobús (capítulo 87, posición 8702)"],
  "exclusions": []
}
```

#### Step 6: `_ensure_missing_fields()` - VALIDAR CAMPOS FALTANTES
```python
# Entrada:
res = {... resultado del LLM ...}
blob = "necesito clasificar un autobus que voy a importar"
conversation_history = None

# Verificación: ¿Ya hay missing_fields?
if res.get("missing_fields"):  # SÍ, ya tiene
    
    # Paso 6a: Verificar si es código de vehículo
    candidates = res.get("top_candidates") or []
    is_vehicle_code = any(
        str(cand.get("code", "")).startswith(("8702", "8703", "8704"))
        for cand in candidates
    )
    # is_vehicle_code = True (porque "8702.10" empieza con "8702")
    
    # Paso 6b: VERIFICAR SI MOTOR FUE PREGUNTADO EN TURNO ANTERIOR
    motor_asked_in_previous_turn = _was_motor_question_asked_in_previous_turn(None)
    # Retorna: False (porque conversation_history es None)
    
    LOG: "LOG_ENSURE_MOTOR_CHECK: has_motor_type=False, already_asks=False, was_asked_before=False"
    
    # Paso 6c: Decisión - ¿Agregar pregunta de motor?
    if not has_motor_type and not already_asks_motor and not motor_asked_in_previous_turn:
        # ✓ AGREGAR motor question
        res["missing_fields"].append("¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)")
        LOG: "LOG_FORCE_MOTOR: Adding motor question (not in previous turn)"

return res
```

#### Step 7: `_prune_missing_fields()` - LIMPIAR CAMPOS REDUNDANTES
```python
# Entrada:
res = {... resultado después de _ensure_missing_fields ...}
query_text = "Necesito clasificar un autobús que voy a importar"
conversation_history = []  # Vacío

# Paso 7a: VERIFICAR SI MOTOR FUE PREGUNTADO EN TURNO ANTERIOR
motor_asked_in_previous_turn = _was_motor_question_asked_in_previous_turn([])
# Retorna: False (sin historial)

# Paso 7b: LIMPIAR CAMPOS CORRUPTOS
# (No hay en este caso)

# Paso 7c: APLICAR field_satisfaction_map
# Verificar si usuario ya respondió a cada campo
# En este turno: NO respondió nada, solo preguntó

LOG: "LOG_PRUNE_START: text_blob_norm='necesito clasificar un autobus...', missing_fields_count=2"
LOG: "LOG_PRUNE_END: cleaned=2 fields (from 2 after cleanup)"

return res  # Sin cambios
```

#### Step 8: `_aggressive_missing_fields_cleanup()` - LIMPIEZA AGRESIVA
```python
# Entrada:
res = {... resultado ...}
query = "Necesito clasificar un autobús que voy a importar"

# Análisis de código y confianza
top = res.get("top_candidates", [0])[0]
confidence = 0.58  # 58%
code = "8702.10"
code_clean = "870210"  # Sin puntos
digit_count = 6

LOG: "LOG_AGGRESSIVE_CLEANUP_BEFORE: code=8702.10, confidence=58%, digits=6, missing_count=2"

# Decisión: ¿Limpiar agresivamente?
if digit_count >= 6 and confidence >= 0.75:  # 58% < 75%, NO
    should_cleanup = True
else:
    should_cleanup = False

LOG: "LOG_AGGRESSIVE_CLEANUP: Keeping missing_fields (code=8702.10, confidence=58%, digits=6)"

return res  # Sin cambios
```

### 1.3 OUTPUT FINAL - TURNO 1

```json
{
  "top_candidates": [
    {
      "code": "8702.10",
      "description": "Autobuses con motor de émbolos, cilindrada ≤ 5000 cc",
      "confidence": 0.58,
      "level": "HS6",
      "years": [2025, 2026]
    },
    {
      "code": "8702.90",
      "description": "Autobuses; otros",
      "confidence": 0.42,
      "level": "HS6",
      "years": [2025, 2026]
    }
  ],
  "missing_fields": [
    "¿Cuántas personas puede transportar?",
    "¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)"
  ],
  "applied_rgi": ["RGI 1"],
  "inclusions": ["Es un autobús (capítulo 87, posición 8702)"],
  "exclusions": [],
  "evidence": []
}
```

### 1.4 RESPUESTA AL USUARIO - TURNO 1
```
SISTEMA PROPONE:
✓ Código: 8702.10 (Confianza: 58%)
✓ Descripción: "Autobuses con motor de émbolos, cilindrada ≤ 5000 cc"

PREGUNTAS PENDIENTES:
1. ¿Cuántas personas puede transportar?
2. ¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)
```

---

## ETAPA 2: TURNO 2 - USUARIO RESPONDE (PERO DIFERENTE)

### 2.1 INPUT DEL USUARIO
```
Usuario: "Es para 50 personas, de transporte público"
```

### 2.2 HISTORIAL GUARDADO EN REDIS
```python
conversation_history = [
    {
        "user": "Necesito clasificar un autobús que voy a importar",
        "assistant": {
            "top_candidates": [...],
            "missing_fields": [
                "¿Cuántas personas puede transportar?",
                "¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)"
            ],
            ...
        },
        "timestamp": "2026-01-28T10:00:00"
    }
]
```

### 2.3 PROCESOS INTERNOS - TURNO 2

#### Step 1: `_was_motor_question_asked_in_previous_turn()` - VERIFICAR PREGUNTA ANTERIOR
```python
def _was_motor_question_asked_in_previous_turn(conversation_history):
    # conversation_history tiene 1 turno
    
    if not conversation_history or len(conversation_history) == 0:
        return False  # No aplica
    
    # Obtener el turno anterior
    last_turn = conversation_history[-1]  # Turno 1
    assistant_response = last_turn.get("assistant", {})
    
    # Extraer missing_fields del turno anterior
    missing_fields = assistant_response.get("missing_fields", [])
    # missing_fields = [
    #   "¿Cuántas personas puede transportar?",
    #   "¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)"
    # ]
    
    # Buscar si alguno contiene "motor"
    motor_was_asked = any("motor" in _normalize_text(f) for f in missing_fields)
    
    LOG: "Checking motor question in previous turn..."
    for field in missing_fields:
        normalized = _normalize_text(field)
        if "motor" in normalized:
            LOG: f"Found motor question: '{field}'"
            motor_was_asked = True
            break
    
    return True  # ✓ Motor fue preguntado en TURNO 1
```

#### Step 2: `_text_blob_from_query_history()` - CONSTRUIR CONTEXTO CONVERSACIONAL
```python
# Parámetros:
query = "Es para 50 personas, de transporte público"
conversation_history = [
    {
        "user": "Necesito clasificar un autobús que voy a importar",
        "assistant": {...}
    }
]

# Construir text_blob
parts = ["Es para 50 personas, de transporte público"]

# Agregar del historial (solo usuario, NO asistente)
for turn in conversation_history:
    if turn.get("user"):
        parts.append("Necesito clasificar un autobús que voy a importar")

text_blob_raw = " ".join(parts)
# = "Es para 50 personas, de transporte público Necesito clasificar un autobús que voy a importar"

# Normalizar
text_blob_norm = _normalize_text(text_blob_raw)
# = "es para 50 personas de transporte publico necesito clasificar un autobus que voy a importar"

LOG: "LOG_TEXT_BLOB_RAW: 'es para 50 personas de transporte publico necesito clasificar un autobus...'"
LOG: "LOG_TEXT_BLOB_NORMALIZED: 'es para 50 personas de transporte publico necesito clasificar un autobus...'"

return text_blob_norm
```

#### Step 3: LLM PROCESA CON CONTEXTO CONVERSACIONAL
```
[RAG + LLM] Enviar a Azure OpenAI:

PROMPT CONSTRUIDO:
Turno 1: Usuario dijo: "Necesito clasificar un autobús que voy a importar"
Turno 2: Usuario dice: "Es para 50 personas, de transporte público"

CONTEXTO CONVERSACIONAL AGREGADO:
- Historial: Usuario mencionó "autobús" → Categoría: Vehículo
- Historial: Primera pregunta fue sobre motor
- Nueva información: "50 personas" → Capacidad especificada

RESULTADO DEL LLM:
{
  "top_candidates": [
    {
      "code": "8702.10",
      "description": "Autobuses con motor de émbolos, cilindrada ≤ 5000 cc",
      "confidence": 0.68,  # Aumentó de 0.58 a 0.68
      "level": "HS6"
    },
    {
      "code": "8702.90",
      "description": "Autobuses; otros",
      "confidence": 0.32,
      "level": "HS6"
    }
  ],
  "missing_fields": [
    "¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)"
  ]
}

LOG: "Confianza aumentó de 58% a 68% (usuario especificó: 50 personas)"
```

#### Step 4: `_ensure_missing_fields()` - VERIFICAR CONSISTENCIA
```python
# Entrada:
res = {
    "top_candidates": [...],
    "missing_fields": ["¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)"]
}
blob = "Es para 50 personas, de transporte público ..."
conversation_history = [... turno anterior ...]

# Paso 1: ¿Ya tiene missing_fields?
if res.get("missing_fields"):  # SÍ
    
    # Paso 2: ¿Es vehículo?
    is_vehicle_code = any(
        str(cand.get("code", "")).startswith(("8702", "8703", "8704"))
        for cand in candidates
    )
    # is_vehicle_code = True
    
    # Paso 3: VERIFICAR SI MOTOR FUE PREGUNTADO EN TURNO ANTERIOR
    motor_asked_in_previous_turn = _was_motor_question_asked_in_previous_turn(conversation_history)
    # ✓ Retorna: True (motor fue preguntado en TURNO 1)
    
    # Paso 4: ¿El usuario respondió motor?
    has_motor_type = any(
        kw in combined_context 
        for kw in ["gasolina", "diesel", "diésel", "electrico", "eléctrico", "hibrido", "híbrido"]
    )
    # has_motor_type = False (usuario NO respondió motor, dijo "50 personas")
    
    # Paso 5: LÓGICA CRÍTICA - DECISIÓN SOBRE MOTOR
    if not has_motor_type and not motor_asked_in_previous_turn:
        # No agregar motor (ya fue preguntado)
        pass
    elif motor_asked_in_previous_turn and not has_motor_type:
        # ✓ MOTOR YA FUE PREGUNTADO EN TURNO ANTERIOR
        # ✓ USUARIO ELIGIÓ NO RESPONDER
        # ✓ NO REPETIR LA PREGUNTA
        LOG: "LOG_FORCE_MOTOR_SKIP: Motor already asked in previous turn, user chose not to answer - not repeating"
```

#### Step 5: `_prune_missing_fields()` - LIMPIEZA CON HISTORIAL
```python
# Entrada:
res = {
    "missing_fields": ["¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)"]
}
query_text = "Es para 50 personas, de transporte público"
conversation_history = [... turno anterior ...]

# Paso 1: EARLY PRUNE - Remover motor si fue preguntado antes
motor_asked_in_previous_turn = _was_motor_question_asked_in_previous_turn(conversation_history)
# ✓ Retorna: True

if motor_asked_in_previous_turn:
    original_missing = res.get("missing_fields", [])
    # = ["¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)"]
    
    res["missing_fields"] = [
        f for f in original_missing
        if "motor" not in _normalize_text(f).lower()
    ]
    # Después del filtro: []
    
    LOG: "LOG_PRUNE_MOTOR_REPEAT: Motor was asked in previous turn - removing from current missing_fields"
    LOG: "LOG_PRUNE_MOTOR_REMOVED: Removed motor question (1 → 0 fields)"

# Resultado final:
res["missing_fields"] = []  # ✓ VACÍO - NO REPITE MOTOR
```

### 2.4 OUTPUT FINAL - TURNO 2

```json
{
  "top_candidates": [
    {
      "code": "8702.10",
      "description": "Autobuses con motor de émbolos, cilindrada ≤ 5000 cc",
      "confidence": 0.68,
      "level": "HS6",
      "years": [2025, 2026]
    }
  ],
  "missing_fields": [],
  "applied_rgi": ["RGI 1"],
  "inclusions": ["Autobús para 50 pasajeros (≥10 plazas) → clasificación 8702"],
  "exclusions": ["8703 (automóviles): No aplica, tiene >10 pasajeros"],
  "evidence": []
}
```

### 2.5 RESPUESTA AL USUARIO - TURNO 2
```
SISTEMA ACTUALIZA:
✓ Código: 8702.10 (Confianza: 68% ↑)
✓ Descripción: "Autobuses con motor de émbolos, cilindrada ≤ 5000 cc"
✓ Confirmado: 50 pasajeros = Autobús (≥10 plazas)

PREGUNTAS PENDIENTES:
- NINGUNA (Motor NO se repite)

SIGUIENTE TURNO:
- Sistema espera respuesta sobre tipo de motor
- O usuario puede dar otro dato
```

---

## ETAPA 3: TURNO 3 - USUARIO RESPONDE MOTOR

### 3.1 INPUT DEL USUARIO
```
Usuario: "Es con motor diésel, cilindrada de 5900 cc. Es importado nuevo."
```

### 3.2 PROCESOS INTERNOS - TURNO 3

#### Step 1: VERIFICAR SI MOTOR FUE PREGUNTADO ANTES
```python
motor_asked_in_previous_turn = _was_motor_question_asked_in_previous_turn(conversation_history)
# conversation_history tiene 2 turnos

# Turno anterior (Turno 2): missing_fields = []
# NO tiene motor question en Turno 2

# Turno anterior al anterior (Turno 1): missing_fields = [
#   "¿Cuántas personas puede transportar?",
#   "¿Qué tipo de motor? (gasolina, diésel, eléctrico, híbrido)"
# ]

# Pero la función mira SOLO last_turn (Turno 2)
last_turn = conversation_history[-1]  # Turno 2
missing_fields = last_turn.get("assistant", {}).get("missing_fields", [])
# missing_fields = [] (vacío)

# Resultado:
motor_was_asked = any("motor" in _normalize_text(f) for f in [])
return False  # NO fue preguntado en TURNO 2
```

#### Step 2: CONSTRUIR CONTEXTO CONVERSACIONAL
```python
# Parámetros:
query = "Es con motor diésel, cilindrada de 5900 cc. Es importado nuevo."
conversation_history = [
    Turno 1: {"user": "Necesito clasificar un autobús...", "assistant": {...}},
    Turno 2: {"user": "Es para 50 personas, de transporte público", "assistant": {...}}
]

# text_blob_norm final:
# "es con motor diesel cilindrada de 5900 cc es importado nuevo necesito clasificar un autobus es para 50 personas de transporte publico"

LOG: "LOG_TEXT_BLOB_NORMALIZED: 'es con motor diesel cilindrada de 5900 cc es importado nuevo...'"
```

#### Step 3: LLM PROCESA CON CONTEXTO COMPLETO
```
[RAG + LLM] Enviar a Azure OpenAI:

CONTEXTO CONSTRUIDO:
Turno 1: Usuario dijo: "Necesito clasificar un autobús que voy a importar"
Turno 2: Usuario dijo: "Es para 50 personas, de transporte público"
Turno 3: Usuario dice: "Es con motor diésel, cilindrada de 5900 cc. Es importado nuevo."

INFORMACIÓN ACUMULADA:
- Producto: Autobús
- Capacidad: 50 pasajeros (≥10 plazas)
- Motor: Diésel
- Cilindrada: 5900 cc
- Estado: Nuevo
- Origen: Importado

RESULTADO DEL LLM:
{
  "top_candidates": [
    {
      "code": "8702.10.90",
      "description": "Autobuses con motor diésel, cilindrada > 5000 cc, nuevo",
      "confidence": 0.89,  # 58% → 68% → 89%
      "level": "NATIONAL10"
    }
  ],
  "missing_fields": [],
  "inclusions": [
    "Autobús para transporte de pasajeros (capítulo 87)",
    "Más de 10 asientos → clasificación 8702 (no 8703)",
    "Motor diésel → subheading 8702.10",
    "Cilindrada 5900 cc > 5000 cc → subheading .90"
  ],
  "exclusions": [
    "8703 (automóviles): No aplica, tiene >10 pasajeros",
    "8711 (motocicletas): No aplica, es autobús"
  ]
}
```

#### Step 4: `_refine_hs_code_from_details()` - REFINAR CÓDIGO
```python
code = "8702.10"
blob = "es con motor diesel cilindrada de 5900 cc es importado nuevo ..."
level = "HS6"

# Paso 1: Es vehículo (8702)?
if code_clean.startswith(("8702", "8703", "8704")):  # SÍ
    
    # Paso 2: Extraer cilindrada
    cilindrada_match = re.search(r'(\d{3,5})\s*(cc|cm3|cm²)', blob_lower)
    # Encontrado: "5900 cc"
    cilindrada = 5900
    
    # Paso 3: ¿Tenemos cilindrada?
    if cilindrada and len(code_clean) == 6:  # SÍ, cilindrada = 5900
        
        # Paso 4: Refinar según cilindrada
        if cilindrada <= 1500:
            subcode = "10"  # Pequeño
        elif cilindrada <= 3000:
            subcode = "20"  # Mediano
        else:
            subcode = "90"  # Grande (5900 > 3000)
        
        # Paso 5: Construir código refinado
        base_formatted = "8702.10"  # Ya tiene formato
        refined = f"{base_formatted}.{subcode}"
        # refined = "8702.10.90"
        
        LOG: "[REFINE_VEHICULO_SUCCESS] 8702.10 + 5900cc → 8702.10.90 (NATIONAL10)"
        
        return "8702.10.90", "NATIONAL10"
```

### 3.3 OUTPUT FINAL - TURNO 3

```json
{
  "top_candidates": [
    {
      "code": "8702.10.90",
      "description": "Autobuses con motor diésel, cilindrada > 5000 cc, nuevo",
      "confidence": 0.89,
      "level": "NATIONAL10",
      "years": [2025, 2026]
    }
  ],
  "missing_fields": [],
  "applied_rgi": ["RGI 1"],
  "inclusions": [
    "Autobús para transporte de pasajeros (capítulo 87)",
    "Más de 10 asientos → clasificación 8702 (no 8703)",
    "Motor diésel → subheading 8702.10",
    "Cilindrada 5900 cc > 5000 cc → subheading .90"
  ],
  "exclusions": [
    "8703 (automóviles): No aplica, tiene >10 pasajeros",
    "8711 (motocicletas): No aplica, es autobús"
  ],
  "evidence": []
}
```

### 3.4 RESPUESTA AL USUARIO - TURNO 3
```
✓ CLASIFICACIÓN FINAL: 8702.10.90
✓ Descripción: "Autobuses con motor diésel, cilindrada > 5000 cc, nuevo"
✓ Confianza: 89% (MÁXIMA PRECISIÓN)
✓ Nivel: NATIONAL10 (10 dígitos)

RÉGIMEN DE IMPORTACIÓN:
- Código completo: 8702.10.90
- Arancel: [Según acuerdos comerciales]
- Referencia: Autobús diésel > 5000 cc

CLASIFICACIÓN COMPLETADA ✓
```

---

## RESUMEN DE FLUJO

### Progresión de Confianza
```
TURNO 1: 58% (Solo categoría: autobús)
TURNO 2: 68% (Categoría + capacidad: 50 personas)
TURNO 3: 89% (Todos los detalles: motor + cilindrada)
```

### Progresión de Precisión
```
TURNO 1: HS6 (6 dígitos) → 8702.10
TURNO 2: HS6 (6 dígitos) → 8702.10
TURNO 3: NATIONAL10 (10 dígitos) → 8702.10.90
```

### Lógica de Consistencia Conversacional (MOTOR)

| Turno | ¿Motor preguntado? | ¿Motor respondido? | Acción Sistema |
|-------|-------------------|-------------------|----------------|
| 1 | NO | NO | **PREGUNTA motor** |
| 2 | SÍ (Turno 1) | NO | **NO REPITE motor** ✓ |
| 3 | NO (Turno 2) | SÍ | **Usa respuesta, refina código** |

---

## LOGS IMPORTANTES

### TURNO 1
```
LOG_TEXT_BLOB_RAW: 'necesito clasificar un autobus que voy a importar'
LOG_ENSURE_MOTOR_CHECK: has_motor_type=False, already_asks=False, was_asked_before=False
LOG_FORCE_MOTOR: Adding motor question (not in previous turn)
LOG_AGGRESSIVE_CLEANUP: Keeping missing_fields (code=8702.10, confidence=58%, digits=6)
```

### TURNO 2 (CRÍTICO)
```
LOG_TEXT_BLOB_NORMALIZED: 'es para 50 personas de transporte publico necesito clasificar un autobus...'
LOG_FORCE_MOTOR_SKIP: Motor already asked in previous turn, user chose not to answer - not repeating ✓
LOG_PRUNE_MOTOR_REPEAT: Motor was asked in previous turn - removing from current missing_fields ✓
LOG_PRUNE_MOTOR_REMOVED: Removed motor question (1 → 0 fields) ✓
```

### TURNO 3
```
LOG_TEXT_BLOB_NORMALIZED: 'es con motor diesel cilindrada de 5900 cc es importado nuevo...'
[REFINE_VEHICULO_SUCCESS] 8702.10 + 5900cc → 8702.10.90 (NATIONAL10)
CONFIDENCE_CALC: confidence=0.89 (HS10 ready)
```

---

## FUNCIONES CLAVE LLAMADAS

### Por Turno

**TURNO 1:**
1. `generate_label()` - Entrada principal
2. `_build_evidence_from_os_hits()` - Construir evidencia (vacía)
3. `_text_blob_from_query_history()` - Normalizar texto
4. `_normalize_result_fields()` - Validar estructura
5. `_ensure_missing_fields()` - Validar campos faltantes
6. `_prune_missing_fields()` - Limpiar redundancias
7. `_aggressive_missing_fields_cleanup()` - Limpieza agresiva

**TURNO 2:**
1. `generate_label()` - Entrada principal
2. `_was_motor_question_asked_in_previous_turn()` - **VERIFICAR CONSISTENCIA**
3. `_text_blob_from_query_history()` - Normalizar con historial
4. `_ensure_missing_fields()` - Validar, **NO repite motor**
5. `_prune_missing_fields()` - **Remover motor si fue preguntado**

**TURNO 3:**
1. `generate_label()` - Entrada principal
2. `_text_blob_from_query_history()` - Normalizar con 2 turnos de historial
3. `_refine_hs_code_from_details()` - Refinar con cilindrada
4. `_calculate_confidence_from_details()` - Calcular confianza final

---

## ARQUITECTURA DE DATOS

### conversation_history (Redis)
```python
[
    # TURNO 1
    {
        "user": "Necesito clasificar un autobús que voy a importar",
        "assistant": {
            "top_candidates": [
                {"code": "8702.10", "confidence": 0.58, ...},
                {"code": "8702.90", "confidence": 0.42, ...}
            ],
            "missing_fields": [
                "¿Cuántas personas puede transportar?",
                "¿Qué tipo de motor? (...)"
            ]
        },
        "timestamp": "2026-01-28T10:00:00"
    },
    
    # TURNO 2
    {
        "user": "Es para 50 personas, de transporte público",
        "assistant": {
            "top_candidates": [
                {"code": "8702.10", "confidence": 0.68, ...}
            ],
            "missing_fields": []  # Motor NO se repite
        },
        "timestamp": "2026-01-28T10:00:30"
    },
    
    # TURNO 3
    {
        "user": "Es con motor diésel, cilindrada de 5900 cc. Es importado nuevo.",
        "assistant": {
            "top_candidates": [
                {"code": "8702.10.90", "confidence": 0.89, ...}
            ],
            "missing_fields": []
        },
        "timestamp": "2026-01-28T10:00:60"
    }
]
```

---

## VALIDACIÓN DE CONSISTENCIA

### Verificación del Bug Corregido

**ESCENARIO SIN ARREGLO (Bug Original):**
```
TURNO 1: ¿Qué tipo de motor? ← Preguntó
TURNO 2: Es para 50 personas... → Usuario NO responde motor
         ¿Qué tipo de motor? ← BUG: REPITE SIN RAZÓN
```

**ESCENARIO CON ARREGLO (Actual):**
```
TURNO 1: ¿Qué tipo de motor? ← Preguntó
TURNO 2: Es para 50 personas... → Usuario NO responde motor
         (Motor NO se repite) ← CORRECCIÓN APLICADA ✓
TURNO 3: Es con motor diésel... → Usuario responde
         (Sistema refina código con cilindrada)
```

### Funciones Críticas para Consistencia

1. **`_was_motor_question_asked_in_previous_turn()`** (Lines 156-183)
   - Detecta si motor fue preguntado antes
   - Retorna booleano

2. **`_ensure_missing_fields()`** (Lines 185-330)
   - NO agrega motor si ya fue preguntado
   - Condition: `not motor_asked_in_previous_turn`

3. **`_prune_missing_fields()`** (Lines 549-600)
   - EARLY PRUNE: Remueve motor si fue preguntado
   - Safety net si motor se coló en missing_fields

4. **Ejecución en orden correcto** (Lines 1446-1450)
   - `_ensure_missing_fields()` → agrega preguntas
   - `_aggressive_missing_fields_cleanup()` → limpia por confianza
   - `_prune_missing_fields()` → remueve repetidas (ÚLTIMO)
