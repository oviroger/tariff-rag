@'
# Tariff RAG - Sistema de Clasificación Arancelaria

Sistema RAG (Retrieval-Augmented Generation) para clasificación arancelaria usando:
- **OpenSearch** con búsqueda híbrida (BM25 + k-NN HNSW)
- **Google Gemini** para embeddings y generación
- **Azure Document Intelligence** para OCR de PDFs
- **FastAPI** (backend) + **Gradio** (UI)
- **Prometheus** (métricas) + **OpenTelemetry** (trazas opcionales)

## 🚀 Inicio Rápido

### Prerrequisitos
- Docker Desktop (8GB RAM recomendados)
- Claves API: `GOOGLE_API_KEY`, `AZURE_FR_ENDPOINT`, `AZURE_FR_KEY`
- Puertos libres: 8000 (API), 7860 (UI), 9200/5601 (OpenSearch/Dashboards), 3306 (MySQL)

### Levantar el stack

```powershell
# 1. Configurar variables de entorno
cp .env.example .env
# Edita .env con tus claves

# 2. Levantar servicios
docker compose up -d

# 3. Inicializar índice OpenSearch
docker compose exec api python scripts/init_index.py

# 4. (Opcional) Ingestar datos
docker compose exec api python scripts/ingest_docs.py
docker compose exec api python scripts/ingest_mysql.py