from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from typing import Optional, Any, Dict
import os
from time import perf_counter
import logging
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from opensearchpy import OpenSearch

from app.config import get_settings
from app.schemas import ClassifyResponse, HealthResponse
from app.metrics import REQUESTS, LATENCY
from app.generator_gemini import generate_label, generate_followup_answer
from app.os_retrieval import retrieve_support_for_code  # si implementaste esta función
from app.os_retrieval import hybrid_search_with_fallback

# Configuración del logger
logger = logging.getLogger("tariff_rag.api")
if not logger.handlers:
    # No toques el nivel si ya tienes configuración global; si no la tienes, lo dejamos INFO.
    logging.basicConfig(level=logging.INFO)

# Lifespan para inicializar/liberar recursos
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"[Startup] API iniciada. OpenSearch host: {settings.opensearch_host}")

    # Inicializar OpenSearch y guardarlo en app.state
    try:
        client = OpenSearch(
            hosts=[settings.opensearch_host],
            http_auth=None,           # agrega auth si la defines en Settings
            verify_certs=False,
            timeout=10,
        )
        # Chequeo liviano
        try:
            health = client.cluster.health()
            logger.info(f"OpenSearch OK: {health.get('status')} (nodes={health.get('number_of_nodes')})")
        except Exception as e:
            logger.exception("OpenSearch health check failed: %s", e)
        app.state.os_client = client
        app.state.index_name = settings.opensearch_index
    except Exception as e:
        logger.exception("Error inicializando OpenSearch: %s", e)
        app.state.os_client = None
        app.state.index_name = None

    # Lifespan activo
    try:
        yield
    finally:
        # Liberar recursos si aplica
        try:
            if getattr(app.state, "os_client", None):
                app.state.os_client.close()
        except Exception:
            pass
        logger.info("[Shutdown] Liberando recursos...")

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

class ChatRequest(BaseModel):
    question: str
    previous_result: Dict[str, Any]

class ChatResponse(BaseModel):
    answer: str

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

@app.post("/classify", response_model=ClassifyResponse)
def classify_endpoint(req: ClassifyRequest, fastapi_request: Request):
    try:
        os_client = getattr(fastapi_request.app.state, "os_client", None)
        index_name = getattr(fastapi_request.app.state, "index_name", None)
        if os_client is None or index_name is None:
            raise HTTPException(status_code=503, detail="Search backend not ready")

        # 1) retrieval con fallback
        hits = hybrid_search_with_fallback(os_client, index_name, req.query, k=req.top_k or 5) or []

        # 2) generación (asegúrate dict)
        result_dict = generate_label(query=req.query, context_docs=hits, max_candidates=req.top_k or 3)
        if not isinstance(result_dict, dict):
            result_dict = result_dict.dict() if hasattr(result_dict, "dict") else {}

        # 3) normalizar evidencia de la consulta
        def _norm(h):
            src = h.get("_source", {}) if isinstance(h, dict) else {}
            return {
                "fragment_id": (src or {}).get("fragment_id") or h.get("fragment_id"),
                "score": h.get("_score") or h.get("score"),
                "text": (src or {}).get("text") or h.get("text", ""),
                "bucket": (src or {}).get("bucket"),
                "unit": (src or {}).get("unit"),
                "doc_id": (src or {}).get("doc_id"),
                "reason": h.get("reason") or "retrieved_by_search",
            }
        try:
            result_dict["evidence"] = [_norm(h) for h in hits]
        except Exception:
            logger.exception("evidence normalization failed")
            result_dict["evidence"] = []

        # 4) evidencia anclada al código (opcional)
        main_code = None
        cands = result_dict.get("top_candidates") or result_dict.get("candidates") or []
        if isinstance(cands, list) and cands:
            main_code = cands[0].get("code") or cands[0].get("hs_code")

        result_dict["support_evidence"] = []
        if main_code:
            try:
                result_dict["support_evidence"] = retrieve_support_for_code(os_client, index_name, main_code, k=3) or []
            except Exception:
                logger.exception("support_evidence retrieval failed")
                result_dict["support_evidence"] = []

        return ClassifyResponse(**result_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in /classify")
        raise HTTPException(status_code=500, detail=f"Internal error: {e.__class__.__name__}: {e}")

@app.post("/chat", response_model=ChatResponse)
def chat_followup(req: ChatRequest):
    answer = generate_followup_answer(req.question, req.previous_result)
    return ChatResponse(answer=answer)

@app.get("/metrics", include_in_schema=False)
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)