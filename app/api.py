from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from typing import Optional
import os
from time import perf_counter

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import get_settings
from app.schemas import ClassifyResponse, HealthResponse
from app.chain_rag import classify
from app.metrics import REQUESTS, LATENCY

# Lifespan para inicializar/liberar recursos
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-carga de recursos (clientes, conexiones pool) aquí si es necesario
    settings = get_settings()
    print(f"[Startup] API iniciada. OpenSearch: {settings.opensearch_host}")
    yield
    print("[Shutdown] Liberando recursos...")

app = FastAPI(
    title="Tariff RAG API",
    description="Clasificación arancelaria con RAG híbrido (OpenSearch + Gemini)",
    version="0.1.0",
    lifespan=lifespan
)

# CORS para desarrollo (ajusta origins en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === REQUEST MODEL CON VALIDACIONES ===
class ClassifyRequest(BaseModel):
    text: str = Field(None, description="Query text (legacy)")
    query: str = Field(None, description="Query text (preferred)")
    top_k: int = Field(default=5, ge=1, le=50)
    file_url: str = Field(None, description="Optional file URL for context")
    debug: bool = Field(default=False, description="Enable debug mode")

    def get_query_text(self) -> str:
        """Return query or text, preferring query if both provided."""
        return self.query or self.text or ""

# === ENDPOINTS ===
@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Tariff RAG API",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check completo: verifica OpenSearch, MySQL y configuración de Gemini"""
    settings = get_settings()
    status = {"status": "ok", "services": {}}

    # OpenSearch
    try:
        from opensearchpy import OpenSearch
        client = OpenSearch(
            hosts=[settings.opensearch_host],
            http_auth=None,
            use_ssl=False,
            verify_certs=False,
            timeout=5
        )
        cluster_health = client.cluster.health()
        status["services"]["opensearch"] = {
            "status": "ok",
            "cluster_name": cluster_health.get("cluster_name"),
            "cluster_status": cluster_health.get("status"),
            "nodes": cluster_health.get("number_of_nodes")
        }
    except Exception as e:
        status["services"]["opensearch"] = {"status": "fail", "error": str(e)}
        status["status"] = "degraded"

    # MySQL
    try:
        import pymysql
        conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_db,
            connect_timeout=5
        )
        conn.close()
        status["services"]["mysql"] = {"status": "ok"}
    except Exception as e:
        status["services"]["mysql"] = {"status": "fail", "error": str(e)}
        status["status"] = "degraded"

    # Gemini API Key (sin llamada real para evitar latencia/costo)
    gemini_key_present = bool(settings.gemini_api_key and len(settings.gemini_api_key) > 10)
    status["services"]["gemini"] = {
        "status": "configured" if gemini_key_present else "missing",
        "key_present": gemini_key_present
    }
    if not gemini_key_present:
        status["status"] = "degraded"

    # Azure Document Intelligence
    azure_fr_configured = bool(settings.azure_formrec_endpoint and settings.azure_formrec_key)
    status["services"]["azure_di"] = {
        "status": "configured" if azure_fr_configured else "missing",
        "configured": azure_fr_configured
    }

    return status

@app.post("/classify", response_model=ClassifyResponse, tags=["Classification"])
def classify_endpoint(request: ClassifyRequest):
    t0 = perf_counter()
    status_code = 200
    try:
        query_text = request.get_query_text()
        if not query_text:
            raise HTTPException(400, "Either 'text' or 'query' field required")

        result = classify(
            text=query_text,  # Usar query_text en lugar de request.text
            file_url=request.file_url,
            top_k=request.top_k,
            debug=request.debug
        )
        return result
    except ValueError as ve:
        status_code = 400
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        status_code = 500
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        LATENCY.labels("/classify", "POST").observe(perf_counter() - t0)
        REQUESTS.labels("/classify", "POST", str(status_code)).inc()

@app.get("/metrics", include_in_schema=False)
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)