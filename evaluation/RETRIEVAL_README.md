# 🔍 Evaluación de Retrieval - Quick Start

## ✅ Estado Actual

- ✅ Dataset generado: 500 registros (100 queries × 5 docs)
- ✅ Herramientas de anotación creadas
- ✅ Calculador de métricas listo
- ⏳ Anotación pendiente: 0/500 (0%)

---

## 🚀 Inicio Rápido

### Opción 1: Anotación Interactiva (Recomendada)

```bash
python evaluation/tools/annotate_retrieval.py --csv evaluation/templates/eval_retrieval_asgard.csv
```

**Controles:**
- `1` = Relevante | `0` = No relevante | `s` = Skip | `q` = Quit

**Para continuar después:**
```bash
python evaluation/tools/annotate_retrieval.py --csv evaluation/templates/eval_retrieval_asgard.csv --start-from 250
```

### Opción 2: Anotación en Excel

```bash
# 1. Generar versión simple
python evaluation/tools/simplify_retrieval_csv.py \
  --input evaluation/templates/eval_retrieval_asgard.csv \
  --output evaluation/templates/eval_retrieval_asgard_simple.csv

# 2. Abrir eval_retrieval_asgard_simple.csv en Excel
# 3. Llenar columna 'relevance' con 0 o 1
# 4. Guardar archivo
```

---

## 📊 Verificar Progreso

```bash
python evaluation/eval_retrieval_annotated.py --csv evaluation/templates/eval_retrieval_asgard.csv --verbose
```

**Salida:**
```
================================================================================
ESTADO DE ANOTACIÓN
================================================================================
Total de registros:     500
Anotados:               125 (25.0%)
  - Relevantes:         45
  - No relevantes:      80
Pendientes:             375
================================================================================
```

---

## 🎯 Calcular Métricas (Después de Anotar)

```bash
python evaluation/eval_retrieval_annotated.py --csv evaluation/templates/eval_retrieval_asgard.csv --verbose
```

**Métricas calculadas:**
```json
{
  "recall@1": 0.45,
  "recall@3": 0.68,
  "recall@5": 0.82,
  "precision@1": 0.45,
  "precision@3": 0.31,
  "precision@5": 0.24,
  "ndcg@1": 0.45,
  "ndcg@3": 0.58,
  "ndcg@5": 0.63,
  "map": 0.52,
  "num_queries": 100,
  "num_annotated": 500
}
```

---

## 📝 Criterio de Relevancia

**Pregunta clave:** ¿Este snippet ayudaría a un agente de aduana a clasificar correctamente el producto?

### ✅ RELEVANTE (1):
- Menciona el capítulo HS correcto
- Describe materiales/características similares
- Proporciona contexto útil para clasificación

### ❌ NO RELEVANTE (0):
- Habla de productos diferentes
- Texto genérico sin valor
- Capítulos HS no relacionados

---

## 📚 Documentación Completa

Ver: [`GUIA_ANOTACION_RETRIEVAL.md`](./GUIA_ANOTACION_RETRIEVAL.md)

---

## 🎯 Ejemplo de Anotación

**Query 1:** `YARA PERLADA FERTILIZANTE SACOS UREA PARA USO AGRICOLA`  
**Ground Truth:** `3102.10` (Capítulo 31: Fertilizantes)

| Rank | Snippet | Relevancia |
|------|---------|------------|
| 1 | "UREA. Las demás, incluidas las mezclas..." | ✅ 1 |
| 2 | "Uso y aplicación: Para uso agrícola..." | ✅ 1 |
| 3 | "Papel y cartón, ondulados..." | ❌ 0 |
| 4 | "Fertilizantes minerales o químicos..." | ✅ 1 |
| 5 | "Los demás abonos..." | ✅ 1 |

**Resultado:** 4/5 relevantes → Retrieval exitoso para esta query

---

## ⏱️ Tiempo Estimado

- **Total:** 3-4 horas para 500 registros
- **Por registro:** ~25-30 segundos
- **Recomendación:** Sesiones de 1 hora con descansos

---

## 📂 Archivos

```
evaluation/
├── templates/
│   ├── eval_retrieval_asgard.csv           # ← ANOTAR AQUÍ
│   └── eval_retrieval_asgard_simple.csv    # Versión para Excel
├── tools/
│   ├── annotate_retrieval.py               # Herramienta interactiva
│   ├── simplify_retrieval_csv.py           # Generador versión simple
│   └── generate_eval_retrieval.py          # (ya usado)
├── eval_retrieval_annotated.py             # Calculador de métricas
├── GUIA_ANOTACION_RETRIEVAL.md            # Guía completa
└── RETRIEVAL_README.md                     # Este archivo
```

---

## 🆘 Troubleshooting

### Problema: "No veo bien los snippets"
**Solución:** Usa la versión Excel:
```bash
python evaluation/tools/simplify_retrieval_csv.py --input ... --output ...
```

### Problema: "Interrumpí la anotación"
**Solución:** El progreso se guarda automáticamente. Continúa con `--start-from <índice>`

### Problema: "Algunos snippets son muy cortos"
**Solución:** Esos son artefactos del OCR. Márcalos como NO relevantes (0) si no aportan información útil.

---

## ✅ Checklist

- [ ] Leer guía de anotación completa
- [ ] Probar herramienta con primeras 5 queries
- [ ] Anotar al menos 50 queries (250 docs) para métricas preliminares
- [ ] Completar 100 queries (500 docs) para evaluación final
- [ ] Calcular métricas finales
- [ ] Guardar resultados en `evaluation/results/retrieval_asgard_metrics.json`

---

**¿Listo para empezar?** 🚀

```bash
python evaluation/tools/annotate_retrieval.py --csv evaluation/templates/eval_retrieval_asgard.csv
```
