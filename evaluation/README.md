# Evaluación y métricas (3.5)

Este directorio contiene scripts y plantillas para calcular métricas del clasificador, del componente de recuperación (RAG) y métricas operativas.

## 🎯 Dataset de Evaluación Generado

Se han generado **42 queries de prueba** de alta calidad distribuidas en:
- **35 queries predefinidas** (productos comunes de diversos capítulos HS)
- **7 queries extraídas de MySQL** (tabla asgard con productos reales)

### Archivos CSV de Evaluación:
- ✅ **`eval_clasificador_hs6.csv`**: 42 queries con predicciones top-3
- ✅ **`eval_retrieval.csv`**: 220 registros (42 queries × ~5 docs recuperados)

> 📋 **IMPORTANTE**: Ver `INSTRUCCIONES_ANOTACION.md` para completar las columnas `true_hs6` y `relevance` antes de ejecutar evaluaciones.
> 
> ⏱️ **Tiempo de anotación estimado**: 3-4 horas (vs 5-7 horas del dataset anterior)
> 
> 📊 **Validez**: Dataset optimizado con todas las queries siendo productos reales válidos

## Estructura

- `evaluation/eval_clasificador.py`: acc@1, acc@3, macro/micro-F1 (si scikit-learn está disponible), MRR@3 y ECE opcional.
- `evaluation/eval_retrieval.py`: recall@k y nDCG@k (relevancia binaria) para la fusión RRF.
- `evaluation/eval_operativo.py`: latencias p50/p95/p99, throughput (QPM) y tasa de errores desde logs.
- `evaluation/templates/*.csv`: plantillas con datos generados automáticamente.
- `evaluation/tools/`: scripts para generar queries y CSVs de evaluación automáticamente.

> Nota de dependencias: los scripts requieren `pandas` y `numpy`. Para macro/micro-F1 se intentará usar `scikit-learn`; si no está instalado, se omite F1 y se imprime `null`.

## Uso rápido

1) Clasificador (HS6):

```bash
python evaluation/eval_clasificador.py --csv evaluation/templates/eval_clasificador_hs6.csv
```

2) Recuperación (RAG):

```bash
python evaluation/eval_retrieval.py --csv evaluation/templates/eval_retrieval.csv --k 5
```

3) Operativas:

```bash
python evaluation/eval_operativo.py --csv evaluation/templates/logs_operativos.csv
```


## Exportar logs operativos desde /metrics

Para exportar logs operativos desde el endpoint de métricas, usa:

```sh
python evaluation/export_logs_operativos.py --url http://localhost:8000/metrics --output evaluation/templates/logs_operativos.csv
```

Puedes cambiar el puerto y la URL según tu configuración:

```sh
python evaluation/export_logs_operativos.py --url http://localhost:<PUERTO>/metrics --output evaluation/templates/logs_operativos.csv
```

## Generar tráfico de prueba (warmup)

Para obtener valores distintos de cero, genera tráfico contra la API antes de exportar:

```bash
python evaluation/tools/warmup_requests.py --base-url http://localhost:8000 \
	--health 20 --classify 20 --workers 5 --query "Necesito importar plátanos"
```

Luego exporta filtrando si lo deseas por endpoint/método:

```bash
python evaluation/export_logs_operativos.py --url http://localhost:8000/metrics \
	--endpoint /classify --method POST --output evaluation/templates/logs_operativos.csv
```

Atajo (Windows PowerShell): warmup + export en un solo paso

```powershell
pwsh -File evaluation/tools/warmup_and_export.ps1 -BaseUrl "http://localhost:8000" `
	-Endpoint "/classify" -Method "POST" -Health 20 -Classify 20 -Workers 5 `
	-Query "Necesito importar plátanos" -Output "evaluation/templates/logs_operativos.csv"
```

## Generar CSVs de evaluación automáticamente

### 1. Generar queries de prueba

Primero genera un conjunto de queries desde el corpus:

```bash
python evaluation/tools/generate_test_queries.py \
  --os-host http://localhost:9200 \
  --os-index tariff_fragments \
  --os-samples 200 \
  --synthetic 70 \
  --target-total 100 \
  --output evaluation/test_queries.txt
```

Esto genera:
- `evaluation/test_queries.txt`: lista de queries (una por línea)
- `evaluation/test_queries_metadata.json`: metadata con códigos HS y fuente

**Dataset actual generado:** 80 queries (10 corpus + 35 predefinidas + 35 sintéticas)

### 2. Clasificador (eval_clasificador_hs6.csv)

Consulta `/classify` con queries de prueba y registra predicciones:

```bash
python evaluation/tools/generate_eval_clasificador.py \
  --base-url http://localhost:8000 \
  --queries-file evaluation/test_queries.txt \
  --top-n 3 \
  --output evaluation/templates/eval_clasificador_hs6.csv
```

**Archivo generado:** ✅ 80 queries con predicciones top-3

**⚠️ Importante**: Debes llenar manualmente la columna `true_hs6` con los códigos correctos antes de calcular métricas.

### 3. Retrieval (eval_retrieval.csv)

Ejecuta búsquedas híbridas en OpenSearch y registra documentos recuperados:

	```bash
	python evaluation/tools/generate_eval_retrieval.py \
		--os-host https://localhost:9200 \
		--index tariff_docs \
		--queries "Smartphone OLED" "Plátanos" \
		--top-k 5 \
		--output evaluation/templates/eval_retrieval.csv
	```

	**Importante**: Debes llenar manualmente la columna `relevance` (0 o 1) para cada documento antes de calcular recall@k y nDCG@k.


## Formatos CSV

Ver archivos en `evaluation/templates/` para los encabezados esperados y ejemplos comentados en la segunda línea.
