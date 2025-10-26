# Checklist de Validación - Tariff-RAG

## Pre-deploy
- [ ] `.env` configurado con claves válidas
- [ ] `.env` NO está en git (`git status` lo ignora)
- [ ] `requirements.txt` no tiene Gradio (solo en `requirements.ui.txt`)
- [ ] No hay conflictos de versiones OTel/httpx/websockets

## Stack
- [ ] `docker compose up -d` arranca sin errores
- [ ] `docker compose ps` muestra 4 servicios healthy (opensearch, mysql, api, ui)
- [ ] http://localhost:8000/docs carga Swagger UI
- [ ] http://localhost:8000/health retorna status "ok"
- [ ] http://localhost:8000/metrics muestra métricas Prometheus
- [ ] http://localhost:7860 carga interfaz Gradio
- [ ] http://localhost:5601 carga OpenSearch Dashboards

## Índice y datos
- [ ] `docker compose exec api python scripts/init_index.py` crea índice
- [ ] OpenSearch Dashboards muestra índice con mapping knn_vector
- [ ] (Opcional) `ingest_docs.py` procesa PDFs con OCR
- [ ] (Opcional) `ingest_mysql.py` ingesta filas desde MySQL

## Funcionalidad
- [ ] UI Gradio acepta descripción y devuelve candidatos
- [ ] `/classify` endpoint retorna JSON válido con top_candidates
- [ ] Métricas incrementan tras llamar a `/classify`
- [ ] Health check reporta estado de OpenSearch y MySQL

## Tests y CI
- [ ] `pytest tests/ -v` pasa 9 tests localmente
- [ ] GitHub Actions CI en verde (si está configurado)
- [ ] Coverage >80% (opcional)

## Observabilidad
- [ ] `/metrics` expone contadores y histogramas
- [ ] (Opcional) OpenTelemetry enviando trazas a colector
- [ ] (Opcional) `eval_ir.py` calcula nDCG/Recall/MRR

## Documentación
- [ ] README.md completo con instrucciones
- [ ] Makefile con targets útiles
- [ ] .env.example sin secretos
- [ ] Comentarios en código para partes complejas

## Seguridad
- [ ] Secretos no commitados
- [ ] .gitignore protege .env y storage/
- [ ] (Producción) Usar Docker secrets o Key Vault