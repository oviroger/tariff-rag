# 📋 Instrucciones para Anotación de Archivos de Evaluación

## ✅ Archivos Generados

Se generaron automáticamente **80 queries** de prueba distribuidas en:

- **35 queries predefinidas** (productos comunes de diversos capítulos HS)
- **10 queries extraídas** del corpus OpenSearch
- **35 queries sintéticas** (variaciones de las anteriores)

### Archivos CSV de Evaluación:

1. **`eval_clasificador_hs6.csv`**: 80 registros (1 por query)
2. **`eval_retrieval.csv`**: 392 registros (80 queries × ~5 docs)

---

## 📝 Paso 1: Anotar `eval_clasificador_hs6.csv`

### Estructura del archivo:
```csv
query_id,query,pred_hs6_1,pred_hs6_2,pred_hs6_3,true_hs6
1,Smartphone con pantalla OLED,8517.12,8517.13,8517.62,
```

### Tarea:
Llenar la columna **`true_hs6`** con el código HS correcto (6 dígitos) para cada query.

### Herramientas de apoyo:
1. **Nomenclatura oficial**: Consultar tablas de la WCO/OMA
2. **Sistema actual**: Comparar con predicciones del modelo (`pred_hs6_1`, `pred_hs6_2`, `pred_hs6_3`)
3. **Corpus local**: Buscar en OpenSearch productos similares

### Ejemplo de anotación:
```csv
query_id,query,pred_hs6_1,pred_hs6_2,pred_hs6_3,true_hs6
60,Smartphone con pantalla OLED,8517.12,8517.13,8517.62,8517.12
54,Laptop HP 15 pulgadas,8471.30,8471.41,8471.49,8471.30
59,Café en grano tostado,0901.21,0901.11,0901.22,0901.21
72,Manzanas rojas importadas,0808.10,0808.30,0810.90,0808.10
```

### Criterios de anotación:
- ✅ **Usar código más específico**: Si existe código de 6 dígitos, usarlo
- ✅ **Ser consistente**: Productos similares deben tener códigos similares
- ⚠️ **Si hay duda**: Dejar vacío o marcar con "REVISAR"
- ⚠️ **Si no existe en HS**: Usar código más cercano y anotar en comentarios

### Tiempo estimado: **2-3 horas** (80 queries)

---

## 📝 Paso 2: Anotar `eval_retrieval.csv`

### Estructura del archivo:
```csv
query_id,query,doc_id,rank,score,relevance,snippet
1,Smartphone OLED,9d7a5ed04bb6afc8_p9709,1,10.77,,- LED - LCD - OLED - QLED
```

### Tarea:
Llenar la columna **`relevance`** con:
- **1** = El documento **ES relevante** para responder la query
- **0** = El documento **NO ES relevante** para la query

### Criterios de relevancia:

#### ✅ Relevante (1):
- Contiene el código HS correcto del producto
- Describe características del producto consultado
- Explica reglas de clasificación aplicables
- Proporciona ejemplos del mismo tipo de producto

#### ❌ No relevante (0):
- Habla de productos completamente diferentes
- Código HS de otra categoría
- Información genérica sin relación
- Fragmentos sin contexto útil

### Ejemplo de anotación:
```csv
query_id,query,doc_id,rank,score,relevance,snippet
60,Smartphone con pantalla OLED,abc123_p100,1,15.2,1,"8517.12 - Teléfonos móviles con pantalla..."
60,Smartphone con pantalla OLED,def456_p200,2,12.8,1,"Características: pantalla OLED, táctil..."
60,Smartphone con pantalla OLED,ghi789_p300,3,8.5,0,"0808.10 - Manzanas frescas..." ← NO relevante
54,Laptop HP 15 pulgadas,jkl012_p400,1,14.1,1,"8471.30 - Máquinas automáticas procesamiento datos..."
```

### Estrategia eficiente:
1. **Revisar snippet**: Leer el texto recuperado
2. **Comparar con query**: ¿Habla del mismo producto/categoría?
3. **Verificar código HS**: Si aparece, ¿corresponde al producto?
4. **Marcar 1 o 0**: Decisión binaria simple

### Tiempo estimado: **3-4 horas** (392 registros)

---

## 🚀 Paso 3: Ejecutar Evaluaciones

Una vez anotados los archivos, ejecutar los scripts de evaluación:

### 3.1 Métricas de Clasificación:
```powershell
python evaluation/eval_clasificador.py `
  --csv evaluation/templates/eval_clasificador_hs6.csv
```

**Salida esperada:**
```
📊 MÉTRICAS DE CLASIFICACIÓN
============================
Accuracy@1: 0.725
Accuracy@3: 0.888
Macro-F1: 0.682
Micro-F1: 0.725
MRR@3: 0.801
ECE (calibración): 0.134
```

### 3.2 Métricas de Recuperación:
```powershell
python evaluation/eval_retrieval.py `
  --csv evaluation/templates/eval_retrieval.csv `
  --k 5
```

**Salida esperada:**
```
📊 MÉTRICAS DE RECUPERACIÓN (IR)
=================================
Recall@1: 0.562
Recall@3: 0.775
Recall@5: 0.850
nDCG@1: 0.562
nDCG@3: 0.689
nDCG@5: 0.734
```

### 3.3 Métricas Operacionales:

#### Primero: Generar tráfico de prueba
```powershell
python evaluation/tools/warmup_requests.py `
  --base-url http://localhost:8000 `
  --num-classify 100 `
  --num-health 50 `
  --workers 5
```

#### Luego: Exportar logs operacionales
```powershell
python evaluation/export_logs_operativos.py `
  --metrics-url http://localhost:8000/metrics `
  --output evaluation/templates/logs_operativos.csv
```

#### Finalmente: Evaluar operaciones
```powershell
python evaluation/eval_operativo.py `
  --csv evaluation/templates/logs_operativos.csv
```

**Salida esperada:**
```
📊 MÉTRICAS OPERACIONALES
=========================
Latencia P50: 0.245 s
Latencia P95: 0.789 s
Latencia P99: 1.234 s
Throughput: 24.5 QPM
Error Rate: 0.02 (2.0%)
```

---

## 📊 Resumen de Tamaños para Prototipo Académico

| Archivo | Queries | Registros | Tiempo Anotación | Estado |
|---------|---------|-----------|------------------|--------|
| **eval_clasificador_hs6.csv** | 80 | 80 | 2-3 horas | ✅ Generado |
| **eval_retrieval.csv** | 80 | 392 | 3-4 horas | ✅ Generado |
| **logs_operativos.csv** | - | ~100-200 | Automático | ⏳ Por generar |

**Total:** ~5-7 horas de anotación manual

---

## 💡 Tips para Anotación Eficiente

### Para `eval_clasificador_hs6.csv`:
1. **Agrupar por categoría**: Anotar primero todas las queries de electrónica, luego alimentos, etc.
2. **Usar las predicciones**: Si `pred_hs6_1` parece correcto, verificar y usarlo
3. **Consultar documentación**: Tener abierta la nomenclatura HS oficial
4. **Anotar en lotes**: 10-15 queries por sesión, descansar

### Para `eval_retrieval.csv`:
1. **Leer solo el snippet**: No necesitas abrir documentos completos
2. **Decisión rápida**: Si el snippet habla del producto → 1, si no → 0
3. **Filtrar por query**: Procesar todas las filas de una query a la vez
4. **Usar búsqueda**: Ctrl+F para encontrar códigos HS en el snippet

### Validación de calidad:
- **Consistencia inter-anotador**: Si es posible, que 2 personas anoten ~10% del dataset
- **Casos ambiguos**: Documentar queries difíciles en archivo aparte
- **Revisión final**: Revisar queries con todas las predicciones incorrectas

---

## 🎯 Próximos Pasos

1. ✅ **Archivos generados** (COMPLETADO)
2. ⏳ **Anotar `eval_clasificador_hs6.csv`** (2-3 horas)
3. ⏳ **Anotar `eval_retrieval.csv`** (3-4 horas)
4. ⏳ **Generar `logs_operativos.csv`** (automático)
5. ⏳ **Ejecutar evaluaciones** (5 minutos)
6. ⏳ **Documentar resultados** en tesis (sección 3.5)

---

## 📁 Archivos de Referencia

- **Queries generadas**: `evaluation/test_queries.txt`
- **Metadata**: `evaluation/test_queries_metadata.json`
- **Scripts generadores**:
  - `evaluation/tools/generate_test_queries.py`
  - `evaluation/tools/generate_eval_clasificador.py`
  - `evaluation/tools/generate_eval_retrieval.py`
- **Scripts evaluadores**:
  - `evaluation/eval_clasificador.py`
  - `evaluation/eval_retrieval.py`
  - `evaluation/eval_operativo.py`

---

## ❓ Preguntas Frecuentes

### ¿Puedo agregar más queries?
Sí, ejecuta de nuevo `generate_test_queries.py` con `--target-total 150` para 150 queries.

### ¿Qué hago si no conozco el código HS correcto?
Consulta:
1. Base de datos WCO/OMA oficial
2. Sistema actual (predicciones del modelo)
3. Experto en comercio internacional

### ¿Puedo modificar queries existentes?
Sí, pero mantén la consistencia en el `query_id` entre ambos archivos CSV.

### ¿Cómo sé si mis anotaciones son correctas?
- Compara con predicciones del modelo (si coinciden, probablemente correcto)
- Valida con documentación oficial HS
- Revisa casos donde todas las predicciones son incorrectas

---

**Última actualización:** 6 de noviembre de 2025
**Autor:** Sistema de Evaluación Automática - Tariff RAG
