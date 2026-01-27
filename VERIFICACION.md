# Guía de Verificación - Filtrado de Evidencia Irrelevante

## Cambios Implementados

### 1. Backend (`app/chain_rag.py`)
- ✅ Filtrado de evidencia con `min_score_for_display = 0.5`
- ✅ No muestra evidencia si score < umbral
- ✅ Missing fields descriptivos

### 2. Configuración (`app/config.py`)
- ✅ Nuevo parámetro `min_score_for_display: float = 0.5`

### 3. Prompts (`app/prompts.py`)
- ✅ Instrucciones para validar relevancia de evidencia
- ✅ LLM instruido para NO usar evidencia irrelevante

### 4. UI (`ui/gradio_app.py`)
- ✅ Importación de `re` agregada
- ✅ UI simplificada (solo renderiza, no decide)

---

## Opción 1: Pruebas Automatizadas

### Paso 1: Iniciar servicios
```powershell
cd "d:\MAESTRIA - copia\tariff-rag"
docker-compose up -d
```

Espera 30-60 segundos para que los servicios inicien completamente.

### Paso 2: Ejecutar test automatizado
```powershell
python test_evidence_filtering.py
```

**Comportamiento esperado:**
```
✅ TEST PASADO
  ✓ No propuso códigos (correcto sin información específica)
  ✓ Pregunta específica sobre tipo de electrodoméstico
  ✓ No hay evidencia irrelevante con score alto
```

---

## Opción 2: Pruebas Manuales en UI

### Paso 1: Iniciar servicios
```powershell
cd "d:\MAESTRIA - copia\tariff-rag"
docker-compose up -d
```

### Paso 2: Abrir UI
Navega a: http://localhost:7860

### Caso de Prueba 1: Electrodomésticos (ANTES tenía neumáticos)

**Query:** `quiero importar electrodomésticos`

**Comportamiento ANTES (❌ malo):**
```
📚 Información disponible (sin clasificación automática)
(Score: 44.11) | 📅 2026
Neumáticos (llantas neumáticas) nuevos de caucho.
```

**Comportamiento AHORA (✅ esperado):**
```
🔍 Necesito más información para clasificar

- ¿Qué tipo de electrodoméstico específico? (lavadora, refrigerador, microondas, etc.)
- Descripción precisa del producto (material, uso, presentación)
- Características técnicas clave

Por favor, proporciona los datos solicitados para una clasificación precisa.
```

**O si hay evidencia relevante:**
```
📚 Información encontrada

1. (Score: 0.XX) | 📅 2025
   [Texto relevante sobre electrodomésticos]

🔍 Información adicional que ayudaría a clasificar
- Tipo de electrodoméstico
...
```

### Caso de Prueba 2: Bus diesel (verificar contexto)

**Query 1:** `quiero importar un bus a diesel`

**Respuesta esperada:**
- ✅ Debe proponer código 8702.20 (bus diesel)
- ✅ NO debe preguntar "tipo de vehículo" (ya dijo bus)
- ✅ NO debe preguntar "tipo de motor" (ya dijo diesel)
- ✅ Debe preguntar: cilindrada, número de pasajeros, nuevo/usado

**Query 2:** `tiene 6000 cc`

**Respuesta esperada:**
- ✅ Debe actualizar a 8702.20.90 (> 3500cc)
- ✅ NO debe volver a preguntar cilindrada
- ✅ Debe preguntar: plazas, nuevo/usado

---

## Opción 3: Pruebas con curl (sin UI)

### Test 1: Electrodomésticos
```powershell
$body = @{
    user_query = "quiero importar electrodomésticos"
    top_k = 5
    conversation_history = @()
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/classify" -Method POST -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 10
```

**Verificar:**
- `evidence`: debe estar vacía o con pocos items con score < 0.5
- `missing_fields`: debe incluir pregunta específica sobre tipo de electrodoméstico
- `top_candidates`: debe estar vacía
- NO debe haber menciones a neumáticos en la evidencia

### Test 2: Health check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

---

## Validación de Resultados

### ✅ Señales de éxito:
1. Query sobre electrodomésticos NO muestra neumáticos
2. Sistema pide información específica del producto
3. Evidencia mostrada tiene score >= 0.5
4. No hay códigos propuestos sin información suficiente
5. Missing fields son específicos y útiles

### ❌ Señales de problema:
1. Muestra evidencia con score < 0.5
2. Propone códigos basándose en evidencia irrelevante
3. Missing fields genéricos ("tipo de producto")
4. Evidencia de neumáticos cuando preguntan por electrodomésticos

---

## Ajustar Umbrales (si necesario)

Si los resultados no son óptimos, ajusta en `app/config.py`:

```python
# Umbral para filtrar documentos en retrieval
min_score: float = 0.35  # Aumentar a 0.4 si trae mucho ruido

# Umbral para mostrar evidencia en UI
min_score_for_display: float = 0.5  # Aumentar a 0.6 para ser más estricto
```

Después de cambiar:
```powershell
docker-compose restart api
```

---

## Rollback (si hay problemas)

Para revertir todos los cambios:

```powershell
cd "d:\MAESTRIA - copia\tariff-rag"
git diff  # Ver cambios
git checkout -- app/config.py app/chain_rag.py app/prompts.py ui/gradio_app.py  # Revertir
docker-compose restart
```

---

## Logs para Debug

Ver logs del API:
```powershell
docker-compose logs -f api
```

Buscar líneas clave:
- `Evidencia insuficiente: X < Y` → Filtrado activado
- `Retrieved X hits` → Documentos recuperados
- `Validación de salida` → Respuesta final construida
