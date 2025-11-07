# 📋 Guía de Anotación de Retrieval

## 🎯 Objetivo

Evaluar la calidad del sistema de recuperación (retrieval) marcando si cada documento recuperado es **relevante** o **no relevante** para clasificar el producto descrito en la query.

---

## 📊 Estado Actual

- **Total de registros:** 500 (100 queries × 5 docs cada una)
- **Anotados:** 0 (0%)
- **Pendientes:** 500 (100%)

---

## ⚙️ Métodos de Anotación

### Opción 1: Herramienta Interactiva (Recomendada)

```powershell
python evaluation/tools/annotate_retrieval.py --csv evaluation/templates/eval_retrieval_asgard.csv
```

**Ventajas:**
- ✅ Interfaz interactiva con progreso en tiempo real
- ✅ Muestra query + snippet juntos
- ✅ Guarda progreso automáticamente
- ✅ Permite volver atrás (back), saltar (skip), y retomar después
- ✅ Estadísticas en vivo

**Controles:**
- `1` = Relevante
- `0` = No relevante
- `s` = Skip (dejar para después)
- `b` = Volver al anterior
- `q` = Guardar y salir
- `?` = Ver ayuda

**Continuar anotación:**
```powershell
# Si interrumpes, puedes retomar desde donde dejaste:
python evaluation/tools/annotate_retrieval.py --csv evaluation/templates/eval_retrieval_asgard.csv --start-from 150
```

---

### Opción 2: Excel/LibreOffice (Manual)

```powershell
# Generar versión simplificada
python evaluation/tools/simplify_retrieval_csv.py `
  --input evaluation/templates/eval_retrieval_asgard.csv `
  --output evaluation/templates/eval_retrieval_asgard_simple.csv
```

Luego:
1. Abre `eval_retrieval_asgard_simple.csv` en Excel
2. Llena la columna **relevance** con `0` o `1`
3. Guarda el archivo
4. Copia los valores de vuelta a `eval_retrieval_asgard.csv`

**Ventajas:**
- ✅ Puedes filtrar, buscar, usar formulas
- ✅ Anotar en bloques
- ✅ Copiar/pegar valores

**Desventajas:**
- ❌ No hay validación automática
- ❌ Más propenso a errores de formato

---

## 🧭 Criterios de Relevancia

### ✅ Un documento es RELEVANTE (1) si:

- Contiene información que **ayudaría a clasificar correctamente** el producto
- Menciona el **capítulo HS correcto** o productos similares
- Describe **características, materiales o usos** relacionados con la query
- Proporciona **contexto útil** para la clasificación arancelaria
- Es del mismo **grupo/familia de productos**

### ❌ Un documento es NO RELEVANTE (0) si:

- Habla de **productos completamente diferentes**
- Menciona **capítulos HS no relacionados**
- Es **texto genérico** sin valor para la clasificación
- Contiene información **contradictoria o confusa**
- Es **ruido del OCR** o texto sin sentido

---

## 💡 Criterio Práctico

> **Pregunta clave:** Si fueras un agente de aduana clasificando el producto de la query,  
> ¿este fragmento te ayudaría a asignar el código HS correcto?
> 
> - **SÍ** → Marca como `1` (relevante)
> - **NO** → Marca como `0` (no relevante)

---

## 📝 Ejemplos de Anotación

### Ejemplo 1: RELEVANTE ✅

**Query:**  
`YARA PERLADA FERTILIZANTE SACOS UREA PARA USO AGRICOLA`

**Ground Truth HS:** `3102.10` (Capítulo 31: Fertilizantes)

**Snippet Recuperado:**  
`UREA. Las demás, incluidas las mezclas no comprendidas en las subpartidas precedentes.`

**Relevancia:** `1` (Relevante)  
**Razón:** Menciona directamente "UREA" y pertenece al capítulo correcto.

---

### Ejemplo 2: NO RELEVANTE ❌

**Query:**  
`YARA PERLADA FERTILIZANTE SACOS UREA PARA USO AGRICOLA`

**Ground Truth HS:** `3102.10` (Capítulo 31: Fertilizantes)

**Snippet Recuperado:**  
`Papel y cartón, ondulados, incluso perforados.`

**Relevancia:** `0` (No relevante)  
**Razón:** Habla de papel y cartón, completamente diferente a fertilizantes.

---

### Ejemplo 3: PARCIALMENTE RELEVANTE → RELEVANTE ✅

**Query:**  
`TUBO DE ACERO REDONDO NEGRO VELAN TUBO DE ACERO REDONDO 22 MM`

**Ground Truth HS:** `7306.30` (Capítulo 73: Tubos de acero)

**Snippet Recuperado:**  
`Los demás tubos (por ejemplo: soldados o remachados) de sección circular...`

**Relevancia:** `1` (Relevante)  
**Razón:** Aunque no menciona "redondo negro" específicamente, describe tubos de sección circular, que es relevante para la clasificación.

---

## 🔍 Verificar Progreso

```powershell
python evaluation/eval_retrieval_annotated.py --csv evaluation/templates/eval_retrieval_asgard.csv --verbose
```

Esto mostrará:
- Total de registros
- Anotados / Pendientes
- Porcentaje de completitud
- Distribución (relevantes vs no relevantes)

---

## 🎯 Calcular Métricas (Después de Anotar)

Una vez completada la anotación (o con anotación parcial):

```powershell
python evaluation/eval_retrieval_annotated.py --csv evaluation/templates/eval_retrieval_asgard.csv --verbose
```

**Métricas calculadas:**
- `recall@1, @3, @5`: ¿Hay al menos 1 doc relevante en top-k?
- `precision@1, @3, @5`: Proporción de docs relevantes en top-k
- `ndcg@1, @3, @5`: Ranking quality (penaliza docs relevantes en posiciones bajas)
- `map`: Mean Average Precision (métrica agregada)

---

## ⏱️ Estimación de Tiempo

- **Con herramienta interactiva:** ~3-4 horas (500 registros ≈ 30 seg/registro)
- **Con Excel (manual):** ~4-5 horas (más lento por context switching)

**Recomendación:** Hazlo en sesiones de 1 hora, guarda progreso frecuentemente.

---

## 📂 Archivos Generados

```
evaluation/
├── templates/
│   ├── eval_retrieval_asgard.csv           # CSV principal (anotar aquí)
│   └── eval_retrieval_asgard_simple.csv    # Versión simplificada para Excel
├── tools/
│   ├── annotate_retrieval.py               # Herramienta interactiva
│   └── simplify_retrieval_csv.py           # Generador de versión simple
└── eval_retrieval_annotated.py             # Calculador de métricas
```

---

## 🆘 Problemas Comunes

### "No puedo ver bien los snippets largos"
```powershell
# Usar Excel para ver snippets completos
python evaluation/tools/simplify_retrieval_csv.py --input ... --output ...
```

### "Interrumpí la anotación, ¿perdí mi progreso?"
```powershell
# NO, el progreso se guarda automáticamente. Continúa con:
python evaluation/tools/annotate_retrieval.py --csv ... --start-from <índice>
```

### "¿Puedo anotar solo algunas queries?"
Sí, las métricas se calcularán solo con las queries que tengan anotaciones completas (todos sus 5 docs anotados).

### "¿Qué pasa si marco todo como 0?"
Las métricas serán 0, pero es un resultado válido si realmente ningún documento es relevante (indicaría problema con el retrieval).

---

## ✅ Checklist de Completitud

- [ ] Revisar primeras 10 queries para familiarizarse con el corpus
- [ ] Anotar al menos 50 queries (250 docs) para métricas preliminares
- [ ] Completar las 100 queries (500 docs) para evaluación final
- [ ] Verificar coherencia: revisar queries con 0% relevantes y 100% relevantes
- [ ] Calcular métricas finales
- [ ] Generar reporte de retrieval

---

**¿Listo para empezar?**

```powershell
python evaluation/tools/annotate_retrieval.py --csv evaluation/templates/eval_retrieval_asgard.csv
```

🚀 ¡Buena suerte con la anotación!
