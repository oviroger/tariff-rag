# Resultados de Evaluación - Sistema RAG de Clasificación Arancelaria

**Fecha:** 6 de noviembre de 2025  
**Dataset:** ASGARD (100 queries con ground truth real)  
**Modelo:** Gemini con búsqueda híbrida OpenSearch

---

## 📊 Métricas del Clasificador

| Métrica | Valor | Descripción |
|---------|-------|-------------|
| **Accuracy@1** | **25.0%** | Porcentaje de consultas donde la predicción top-1 es correcta |
| **Accuracy@3** | **26.0%** | Porcentaje de consultas donde el código correcto está en el top-3 |
| **MRR@3** | **0.255** | Mean Reciprocal Rank - posición promedio del código correcto |
| **Macro-F1** | **0.175** | F1 promedio entre todas las clases (capítulos HS) |
| **Micro-F1** | **0.250** | F1 global considerando todos los casos |
| **ECE@10** | **N/A** | Expected Calibration Error (requiere scores de probabilidad) |

---

## 🔎 Métricas de Retrieval (100 queries × 5 docs)

Anotación completada: 500/500 documentos (92 relevantes, 408 no relevantes)

| Métrica | @1 | @3 | @5 |
|--------:|:--:|:--:|:--:|
| Recall  | 0.24 | 0.41 | 0.48 |
| Precision | 0.24 | 0.207 | 0.184 |
| nDCG    | 0.24 | 0.338 | 0.366 |

Otras:
- MAP: 0.321
- Número de queries: 100

Archivo: `evaluation/results/retrieval_asgard_metrics.json`

---

## 🎯 Interpretación de Resultados

### Precisión del Clasificador
- **1 de cada 4 consultas** recibe el código HS correcto como primera predicción
- El sistema muestra **baja mejora** entre top-1 y top-3 (solo +1%), indicando que cuando falla, raramente el código correcto está en posiciones 2-3
- El **MRR de 0.255** confirma que la mayoría de aciertos están en la primera posición

### F1 Scores
- **Micro-F1 = 0.25** coincide con Accuracy@1 (esperado en clasificación multiclase)
- **Macro-F1 = 0.175** indica desbalance en el desempeño entre diferentes capítulos HS
- La diferencia (0.25 vs 0.175) sugiere que el sistema funciona mejor en algunos capítulos que en otros

---

## 🔍 Análisis del Dataset

- **Total de consultas:** 100
- **Capítulos HS cubiertos:** 85 (del 04 al 98)
- **Distribución:** ~1 consulta por capítulo
- **Fuente:** Archivo ASGARD.csv con declaraciones reales de importación/exportación
- **Ventaja:** Ground truth verificado (códigos HS oficiales de aduana)

---

## ⚠️ Observaciones

### Advertencias de scikit-learn
Durante el cálculo se generaron warnings indicando que el número de clases únicas (códigos HS diferentes) es mayor al 50% de las muestras. Esto es **normal** para este tipo de evaluación donde:
- Hay 100 queries
- Hay ~85 códigos HS únicos (uno por capítulo)
- Es un problema de clasificación multiclase con muchas clases y pocas muestras por clase

### Limitaciones
1. **Dataset pequeño:** 100 queries es adecuado para una tesis de maestría pero insuficiente para conclusiones estadísticamente robustas
2. **Cobertura dispersa:** 1 query por capítulo no permite evaluar consistencia intra-capítulo
3. **Falta ECE:** No se calculó calibración porque el endpoint `/classify` no devuelve probabilidades, solo rankings

---

## 📝 Próximos Pasos

### Para mejorar la evaluación:
1. ✅ **Clasificador evaluado** con ground truth automático
2. ✅ **Retrieval evaluado** con anotación completa y métricas guardadas
3. ⏳ **Operacional:** Generar logs con warmup y exportar métricas de latencia/throughput

### Para mejorar el modelo:
- Analizar fallos por capítulo para identificar patrones
- Incrementar dataset de entrenamiento con más queries ASGARD
- Implementar reranking o fine-tuning específico para códigos HS problemáticos
- Agregar explicabilidad para entender predicciones incorrectas

---

## 📂 Archivos Generados

```
evaluation/
├── queries_asgard.txt                          # 100 queries (texto plano)
├── queries_asgard_metadata.json                # Metadata completo
├── queries_asgard_groundtruth.csv              # Ground truth con códigos HS
├── templates/
│   ├── eval_clasificador_hs6_asgard.csv        # Predicciones + ground truth
│   ├── eval_clasificador_hs6_asgard_metrics.csv # Formato normalizado
│   └── eval_retrieval_asgard.csv               # 500 docs para anotar
├── results/
│   └── classifier_asgard_metrics.json          # Métricas finales
└── tools/
    ├── generate_from_asgard.py                 # Extractor de queries
    ├── merge_groundtruth.py                    # Fusión con ground truth
    └── reshape_eval_for_metrics.py             # Normalización de formato
```

---

**Nota:** Los warnings de scikit-learn son informativos y no afectan la validez de las métricas. Reflejan la naturaleza del problema: clasificación multiclase con alta cardinalidad y pocas muestras por clase.
