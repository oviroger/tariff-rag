# Evaluación y métricas (3.5)

Este directorio contiene scripts y plantillas para calcular métricas del clasificador, del componente de recuperación (RAG) y métricas operativas.

## Estructura

- `evaluation/eval_clasificador.py`: acc@1, acc@3, macro/micro-F1 (si scikit-learn está disponible), MRR@3 y ECE opcional.
- `evaluation/eval_retrieval.py`: recall@k y nDCG@k (relevancia binaria) para la fusión RRF.
- `evaluation/eval_operativo.py`: latencias p50/p95/p99, throughput (QPM) y tasa de errores desde logs.
- `evaluation/templates/*.csv`: plantillas vacías con encabezados.

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

## Formatos CSV

Ver archivos en `evaluation/templates/` para los encabezados esperados y ejemplos comentados en la segunda línea.
