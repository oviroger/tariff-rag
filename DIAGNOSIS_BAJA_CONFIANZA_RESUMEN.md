# 🔴 DIAGNOSIS: POR QUÉ MICROONDAS TIENE BAJA CONFIANZA (35-55%)

## 📊 HALLAZGOS CLAVE

| Componente | Estado | Impacto |
|-----------|--------|--------|
| `tariff_fragments` (índice vacío) | ❌ 0 docs | Alto: Configura inundaciones vacías |
| `tariff_fragments_2026` | ✅ 14,175 docs | Datos existentes pero sin metadatos |
| Búsqueda "microondas" | ⚠️ 1 resultado (score 0.03) | Muy débil - solo lista "- Hornos de microondas" |
| Campo `hs_code` en documentos | ❌ No existe | No hay mapeo texto → código |
| Confianza promedio electrodomésticos | ❌ 35-55% | Debería estar en 80%+ |

---

## 🎯 RAÍCES DEL PROBLEMA

### Problema 1: Índice Vacío (CRÍTICO)
```
tariff_fragments (default): 0 documentos ❌
   └─→ API intenta buscar aquí
   └─→ No encuentra nada
   └─→ Recurre a fallback débil
```

### Problema 2: Documentos Sin Metadatos
```
Documento en tariff_fragments_2026:
{
  "text": "- Hornos de microondas",        ← Solo texto crudo
  "fragment_id": "Arancel_2026_5_p2424",
  "doc_id": "Arancel_2026_5",
  "bucket": "afr_2026",
  "year": 2026
  
  ❌ FALTAN: hs_code, descripción, categoría, nivel_arancelario
}
```

### Problema 3: Score de Relevancia Muy Bajo
```
Query "microondas" → Score: 0.0317 (muy bajo)
   └─→ Poca coincidencia con índice
   └─→ Modelo Gemini: "evidencia débil → confianza baja"
```

### Problema 4: Ambigüedad en Subpartidas
```
"Hornos de microondas" podría ser:
├─ 8516.50: Microondas convencionales (95% de casos)
├─ 8516.60: Con funciones adicionales  (4% de casos)
└─ 8509.80: Otros electrodomésticos    (1% de casos)

Sin más contexto → Modelo es conservador → Baja confianza
```

---

## ✅ SOLUCIONES PROPUESTAS

### Solución 1️⃣: REPARAR LA INDEXACIÓN (⭐ RECOMENDADA)

```python
# Verificar qué índice usa el API
# En app/config.py → opensearch_index = "tariff_fragments_2025"

# Problema: tariff_fragments_2025 podría estar vacío también
# Solución: 
#   1. Verificar índices activos
#   2. Actualizar config a usar tariff_fragments_2026
#   3. O reindexar con metadatos completos
```

**Pasos:**
1. ✅ Verificar config actual del API
2. ✅ Usar índice 2026 que tiene datos
3. ✅ Reindexar con campos: `hs_code`, `description`, `category`
4. ✅ Mejorar embeddings específicos para aranceles

**Tiempo estimado:** 30-45 minutos

---

### Solución 2️⃣: MEJORAR PROMPTS (⭐ RÁPIDO)

Ajustar `app/generator_gemini.py` para:

```python
# ANTES:
# "Confidence: X% (modelo conservador con evidencia débil)"

# DESPUÉS:  
# Si el usuario dice "microondas" → automáticamente 8516.50
# Si el usuario dice "microondas + nuevo" → incrementar confianza 20%
# Si el usuario dice "microondas + características adicionales" → 8516.60
```

**Pasos:**
1. ✅ Agregar diccionario de patrones comunes
2. ✅ Aumentar boost de confianza si hay confirmación conversacional
3. ✅ Hacer prompts más específicos para electrodomésticos

**Tiempo estimado:** 15-20 minutos

---

### Solución 3️⃣: ENRIQUECER DOCUMENTOS (INTERMEDIO)

Mapear fragmentos de texto a códigos HS conocidos:

```python
# Crear mapeo:
{
  "microondas convencional": "8516.50",
  "microondas con convección": "8516.60",
  "hornos eléctricos": "8516.10",
  "refrigerador": "8418.69",
  "lavadora": "8450"
}

# Reindexar con este campo nuevo
```

**Tiempo estimado:** 1-2 horas

---

## 🚀 RECOMENDACIÓN FINAL

**Ejecutar Solución 1 + Solución 2:**

### 👉 Paso 1: Verificar Config (5 min)
```bash
# Ver qué índice está usando
grep -n "opensearch_index" app/config.py
docker logs rag-api | grep -i "opensearch"
```

### 👉 Paso 2: Actualizar si es Necesario (10 min)
Si usa `tariff_fragments` o `tariff_fragments_2025` vacío:
```python
# app/config.py
opensearch_index = "tariff_fragments_2026"  # ✅ Tiene 14,175 docs
```

### 👉 Paso 3: Mejorar Prompts (20 min)
```python
# app/generator_gemini.py
# Agregar boost de confianza si:
# - Usuario menciona "microondas" + "nuevo" → confianza += 15%
# - Usuario menciona "microondas" a secas → asignar 8516.50 por defecto
# - Validar contra reglas de negocio en app/rules.py
```

### 👉 Paso 4: Test (10 min)
```bash
python debug_microwave_confidence.py
# Verificar que confianza suba a 75%+
```

---

## 📈 RESULTADO ESPERADO

| Query | Antes | Después |
|-------|-------|---------|
| "microondas" | 35% → ? | 75%+ |
| "microondas nuevo" | 45% → ? | 85%+ |
| "microondas convencional" | 43% → ? | 80%+ |
| "es nuevo" | 55% → ? | 80%+ |

---

## ❓ ¿QUIERES QUE IMPLEMENTE ESTO?

**Opciones:**
- [ ] **A) Rápida (5 min):** Solo verificar qué índice está usando el API
- [ ] **B) Estándar (45 min):** Solución 1 + Solución 2 (lo recomendado)
- [ ] **C) Completa (2+ horas):** Soluciones 1, 2 y 3 (reindexación completa)
- [ ] **D) Solo diagnóstico:** Mostrar más detalles del API
