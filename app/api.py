from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from contextlib import asynccontextmanager
from typing import Optional, Any, Dict, List
import os
from time import perf_counter
import logging
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from opensearchpy import OpenSearch
import redis, json
from uuid import uuid4
from datetime import datetime

from app.config import get_settings
from app.schemas import ClassifyResponse, HealthResponse
from app.metrics import REQUESTS, LATENCY
from app.generator_gemini import generate_label, generate_followup_answer
from app.os_retrieval import retrieve_support_for_code  # si implementaste esta función
from app.os_retrieval import hybrid_search_with_fallback

# === Redis Helpers ===
HISTORY_TTL = 86400  # 24 horas en segundos

def load_history(r, conv_id):
    """Carga historial desde Redis. Retorna [] si no existe."""
    if not conv_id:
        return []
    raw = r.get(f"chat:{conv_id}")
    return json.loads(raw) if raw else []

def save_history(r, conv_id, history):
    """Guarda historial en Redis con expiración de 24h."""
    if conv_id:
        r.setex(
            f"chat:{conv_id}",
            HISTORY_TTL,
            json.dumps(history)
        )

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

    # Inicializar Redis y guardarlo en app.state
    try:
        redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        app.state.redis = redis_client
    except Exception as e:
        logger.exception("Error inicializando Redis: %s", e)
        app.state.redis = None

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

# === Prometheus instrumentation (middleware) ===
@app.middleware("http")
async def prometheus_instrumentation(request: Request, call_next):
    start = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = getattr(response, "status_code", 500)
        return response
    finally:
        try:
            elapsed = perf_counter() - start
            path = request.url.path
            method = request.method
            LATENCY.labels(endpoint=path, method=method).observe(elapsed)
            REQUESTS.labels(endpoint=path, method=method, status=str(status_code)).inc()
        except Exception:
            # No romper la petición si la instrumentación falla
            pass

# === REQUEST MODEL CON VALIDACIONES ===
class ClassifyRequest(BaseModel):
    user_query: str
    hs_code: Optional[str] = None
    conversation_history: Optional[list] = []
    conversation_id: Optional[str] = None
    top_k: Optional[int] = 5
    years: Optional[List[int]] = None  # Filtrar por años: [2025], [2026], o [2025, 2026]

    @model_validator(mode='after')
    def check_query_provided(self):
        """Ensure user_query is provided and non-empty."""
        if not self.user_query or not self.user_query.strip():
            raise ValueError("user_query must be provided and non-empty")
        return self

    def get_query_text(self) -> str:
        """Return user_query text."""
        return self.user_query.strip() if isinstance(self.user_query, str) else ""

class ChatRequest(BaseModel):
    question: str
    previous_result: Optional[Dict[str, Any]] = None
    conversation_history: Optional[list] = []
    conversation_id: Optional[str] = None

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
        redis_client = getattr(fastapi_request.app.state, "redis", None)
        if os_client is None or index_name is None:
            raise HTTPException(status_code=503, detail="Search backend not ready")
        
        # Asegurar conversation_id
        conv_id = req.conversation_id or uuid4().hex
        
        # Cargar historial desde Redis
        history = []
        if redis_client:
            try:
                history = load_history(redis_client, conv_id)
                # Solo sobrescribir con historial del request si NO está vacío (UI tiene datos)
                if req.conversation_history and len(req.conversation_history) > 0:
                    history = req.conversation_history
            except Exception as e:
                logger.warning(f"Redis load_history failed: {e}")
                history = req.conversation_history or []

        # 0) Validación de query vaga/corta
        query_text = req.get_query_text().strip()
        if len(query_text) < 3:
            # Query demasiado corta - retornar respuesta vacía con warnings
            return ClassifyResponse(
                top_candidates=[],
                evidence=[],
                support_evidence=[],
                applied_rgi=[],
                inclusions=[],
                exclusions=[],
                missing_fields=["La consulta es demasiado corta. Por favor proporciona más detalles sobre el producto."],
                warnings=["Query too short: se requiere al menos 3 caracteres"],
                versions={"hs_edition": "HS_2022"}
            )
        
        # 0.5) Construir texto contextual para el sanitizer (incluye últimas 2-3 interacciones)
        contextual_query = query_text
        logger.info(f"[SANITIZER DEBUG] query_text: {query_text}")
        logger.info(f"[SANITIZER DEBUG] history length: {len(history)}")
        if history and len(history) > 0:
            # Tomar las últimas 2-3 preguntas del usuario para dar contexto
            recent_user_queries = []
            for msg in reversed(history[-6:]):  # Últimos 6 mensajes (3 turnos)
                if isinstance(msg, dict):
                    # El historial puede tener formato {"role": "user", "content": "..."} o {"user": "...", "assistant": "..."}
                    user_content = msg.get("content") if msg.get("role") == "user" else msg.get("user")
                    if user_content:
                        recent_user_queries.insert(0, user_content)
                if len(recent_user_queries) >= 3:
                    break
            # Combinar: queries anteriores + query actual
            logger.info(f"[SANITIZER DEBUG] recent_user_queries: {recent_user_queries}")
            all_queries = recent_user_queries + [query_text]
            contextual_query = " ".join(all_queries)
            logger.info(f"[SANITIZER DEBUG] Contextual query built: {contextual_query[:200]}")
        else:
            contextual_query = query_text
            logger.info(f"[SANITIZER DEBUG] No history, using query_text only")

        # 1) retrieval con fallback
        try:
            # Pasar None para index para que siempre use la lógica de configuración (opensearch_indices o años)
            # Si se especifican años, retrieve_fragments() hará la selección de índices específicos
            index_for_search = None
            hits = hybrid_search_with_fallback(
                os_client, 
                index_for_search, 
                query_text, 
                k=req.top_k or 5,
                years=req.years
            ) or []
        except Exception as e:
            logger.warning(f"Retrieval failed: {e}. Using empty hits.")
            hits = []

        # 1.1) Si el mejor score es muy bajo, tratar como sin contexto para evitar ruido
        settings = get_settings()
        min_score_for_display = getattr(settings, "min_score_for_display", 0.02)
        if hits:
            best_score = max((h.get("_score") or h.get("score") or 0) for h in hits)
            if best_score < min_score_for_display:
                logger.info(
                    f"[RETRIEVAL FILTER] best_score={best_score:.4f} < threshold={min_score_for_display}; dropping context hits"
                )
                hits = []

        # 2) generación (asegúrate dict)
        result_dict = generate_label(
            query=query_text, 
            context_docs=hits, 
            max_candidates=req.top_k or 3,
            conversation_history=history
        )
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
                "year": (src or {}).get("year"),  # Incluir año
            }
        try:
            result_dict["evidence"] = [_norm(h) for h in hits]
        except Exception:
            logger.exception("evidence normalization failed")
            result_dict["evidence"] = []

        # 3.1) FILTRAR evidencia irrelevante por score
        # Si no hay candidatos y la evidencia tiene score bajo, NO mostrarla
        # min_score_for_display ya cargado arriba
        candidates = result_dict.get("top_candidates", [])
        evidence = result_dict.get("evidence", [])
        
        if not candidates and evidence:
            # Filtrar evidencia con score < umbral
            relevant_evidence = [ev for ev in evidence if (ev.get("score") or 0) >= min_score_for_display]
            result_dict["evidence"] = relevant_evidence
            logger.info(f"Filtered evidence: {len(evidence)} -> {len(relevant_evidence)} (threshold={min_score_for_display})")

        # 3.5) Normalización/Corrección de missing_fields genéricos según contexto
        def _has_generic_missing(missing_list):
            """Detecta si el LLM devolvió campos genéricos prohibidos."""
            banned = [
                "tipo de producto",  # Demasiado genérico
                "tipo de dispositivo",  # Demasiado genérico
                "material o composición",  # Demasiado genérico
                "características técnicas relevantes",  # Con "relevantes" es genérico
                "características técnicas adicionales",  # Con "adicionales" es genérico
                "característica adicional",  # Específico para laptop
                "dimensiones relevantes",  # Con "relevantes" es genérico
                "proceso de fabricación",  # Demasiado genérico
                "norma aplicable",
                "cualquier característica",
                "descripción del artículo",
                "estado del artículo",
                "detalles del procesador",
                "como procesador, ram, almacenamiento",
                "uso principal",  # Nuevo: detectar "¿Cuál es su uso principal?"
            ]
            ml = [str(m).lower() for m in (missing_list or [])]
            # IMPORTANTE: Solo marcar como genérico si coincide exactamente o contiene la frase completa
            # NO eliminar campos útiles como "¿Es nuevo o usado?" que son específicos
            return any(any(b in m and len(m) < len(b) + 30 for b in banned) for m in ml)

        try:
            mf = result_dict.get("missing_fields") or []
            has_gen = _has_generic_missing(mf)
            
            logger.info(f"[SANITIZER] contextual_query: {contextual_query[:150]}")
            logger.info(f"[SANITIZER] has_generic_fields={has_gen}")
            logger.info(f"[SANITIZER] missing_fields from LLM: {mf}")
            
            # ÚNICA REGLA: Si el LLM devolvió campos genéricos prohibidos, limpiarlos
            if has_gen:
                logger.warning(f"[SANITIZER] Detected generic fields. Filtering them out.")
                # Filtrar SOLO campos genéricos, mantener campos específicos útiles
                filtered_mf = [
                    field for field in mf 
                    if not any(banned in str(field).lower() and len(str(field)) < len(banned) + 30 
                              for banned in [
                        "tipo de producto",
                        "tipo de dispositivo",
                        "material o composición",
                        "características técnicas relevantes",
                        "características técnicas adicionales",
                        "característica adicional",
                        "dimensiones relevantes",
                        "proceso de fabricación",
                        "norma aplicable",
                        "cualquier característica",
                        "descripción del artículo",
                        "estado del artículo",
                        "detalles del procesador",
                        "como procesador, ram, almacenamiento",
                        "uso principal",
                        "es portátil o de escritorio",  # Específico para laptops donde ya se estableció el tipo
                    ])
                ]
                result_dict["missing_fields"] = filtered_mf
                logger.info(f"[SANITIZER] Filtered missing_fields: {filtered_mf}")
                
        except Exception as e:
            # No interrumpir si el saneamiento falla
            logger.exception(f"Sanitizer failed: {e}")
            pass

        # 3.6) Si NO hay candidatos y missing_fields está vacío o genérico, usar defaults contextuales
        candidates = result_dict.get("top_candidates", [])
        current_mf = result_dict.get("missing_fields", [])
        
        if not candidates and len(current_mf) <= 3:
            # Intentar generar campos específicos basados en la query
            from app.generator_gemini import _default_missing_fields
            contextual_mf = _default_missing_fields(query_text)
            
            # Si los defaults son más específicos que los actuales, usarlos
            if contextual_mf and contextual_mf != current_mf:
                logger.info(f"[OVERRIDE] Using contextual missing_fields: {contextual_mf}")
                result_dict["missing_fields"] = contextual_mf

        # 3.6.1) Si el usuario ya especificó un electrodoméstico concreto, no repetir la pregunta genérica
        appliance_kws = [
            "lavadora", "refrigerador", "microondas", "horno", "lavavajillas", "secadora",
            "licuadora", "batidora", "plancha", "aspiradora", "lavaseca", "lava seca"
        ]
        q_norm = query_text.lower()
        if any(kw in q_norm for kw in appliance_kws):
            mf_list = result_dict.get("missing_fields") or []
            pruned_mf = [f for f in mf_list if "electrodom" not in str(f).lower()]
            if len(pruned_mf) != len(mf_list):
                logger.info("[PRUNE] Removing generic 'tipo de electrodoméstico' because user specified appliance")
                result_dict["missing_fields"] = pruned_mf

        # 3.7) FALLBACK: Si LLM no propuso candidatos pero HAY documentos, proponer automáticamente
        cands_before_fallback = result_dict.get("top_candidates") or []
        if not cands_before_fallback and hits:
            logger.info("[FALLBACK] LLM no propuso candidatos pero hay documentos. Generando código automático.")
            # Generar un candidato automático basado en palabras clave
            query_lower = query_text.lower()
            
            # Mapeo de palabras clave a códigos HS probables
            keyword_to_code = {
                "cable": "8544.30",  # Cables de cobre aislados
                "conductor": "8544.30",
                "alambre": "7408.11",  # Alambre de cobre
                "cobre": "7408.11",
                "bus": "8702.10",  # Transporte de pasajeros
                "camión": "8704.21",
                "vehículo": "8703.21",
                "acero": "7208.37",  # Láminas de acero
                "hierro": "7208.37",
                "lámina": "7208.37",
            }
            
            # Buscar palabras clave en el query
            code = None
            for keyword, candidate_code in keyword_to_code.items():
                if keyword in query_lower:
                    code = candidate_code
                    break
            
            # Si se encontró un código, proponer
            if code:
                result_dict["top_candidates"] = [{
                    "code": code,
                    "description": f"Basado en documentos recuperados: {hits[0].get('_source', {}).get('text', '')[:80]}...",
                    "confidence": 0.72,
                    "level": "HS6"
                }]
                result_dict["missing_fields"] = [
                    "Confirma el producto o proporciona más detalles",
                    "Características adicionales que puedan refinar la clasificación"
                ]
                result_dict["warnings"] = ["Clasificación generada por fallback automático"]
                logger.info(f"[FALLBACK] Generado candidato automático: {code}")
            else:
                logger.info(f"[FALLBACK] No se encontró mapeo de palabras clave para generar código")

        # 4) evidencia anclada al código (opcional)
        main_code = None
        cands = result_dict.get("top_candidates") or result_dict.get("candidates") or []
        if isinstance(cands, list) and cands:
            main_code = cands[0].get("code") or cands[0].get("hs_code")

        result_dict["support_evidence"] = []
        if main_code:
            try:
                result_dict["support_evidence"] = retrieve_support_for_code(
                    os_client,
                    index_name,
                    main_code,
                    k=3,
                    query_text=query_text,
                ) or []
            except Exception:
                logger.exception("support_evidence retrieval failed")
                result_dict["support_evidence"] = []
        
        # Actualizar y guardar historial en Redis
        if redis_client:
            try:
                # Añadir nuevo turno al historial
                history.append({
                    "user": query_text,
                    "assistant": result_dict.get("top_candidates", [{}])[0].get("code", "N/A") if result_dict.get("top_candidates") else "N/A",
                    "timestamp": datetime.now().isoformat()
                })
                save_history(redis_client, conv_id, history)
            except Exception as e:
                logger.warning(f"Redis save_history failed: {e}")
        
        # Añadir conversation_id a la respuesta
        result_dict["conversation_id"] = conv_id
        
        # Extraer años de los hits y incluirlos en la respuesta
        years_set = set()
        for hit in hits:
            year = (hit.get("_source") or {}).get("year")
            if year:
                years_set.add(year)
        result_dict["years"] = sorted(list(years_set)) if years_set else None
        
        # Agregar años a cada candidato propuesto
        if result_dict.get("top_candidates"):
            for cand in result_dict["top_candidates"]:
                if not cand.get("years"):
                    cand["years"] = sorted(list(years_set)) if years_set else None
        
        # Rastrear progreso hacia HS10: cuáles son los detalles faltantes
        cands = result_dict.get("top_candidates") or []
        if cands:
            top_code = cands[0].get("code", "")
            top_level = cands[0].get("level", "HS6")
            missing = result_dict.get("missing_fields") or []
            
            # Determinar qué falta para llegar a HS10
            hs10_requirements = {
                "8450": ["¿Es nueva o usada?"],  # Lavadora
                "8703": ["Cilindrada en cc", "¿Es nueva o usada?"],  # Automóvil
                "8702": ["Cilindrada en cc", "¿Es nueva o usada?"],  # Autobús
                "8704": ["Cilindrada en cc", "¿Es nueva o usada?"],  # Camión
            }
            
            # Buscar el capítulo (primeros 4 dígitos)
            code_clean = top_code.replace(".", "").replace(" ", "")
            chapter = code_clean[:4] if len(code_clean) >= 4 else ""
            
            # Si el código está en la lista de refinables y aún es HS6, informar qué falta
            if chapter in hs10_requirements and top_level == "HS6":
                required = hs10_requirements[chapter]
                missing_for_hs10 = [r for r in required if r not in str(missing).lower()]
                if missing_for_hs10:
                    note = f"Para refinar a HS10 ({chapter}xx.xx.xx), se necesita: {', '.join(missing_for_hs10)}"
                    result_dict.setdefault("warnings", []).append(note)
                    logger.info(f"[HS10_TRACKING] {note}")

        return ClassifyResponse(**result_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in /classify")
        raise HTTPException(status_code=500, detail=f"Internal error: {e.__class__.__name__}: {e}")

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Endpoint para preguntas de seguimiento sobre clasificaciones.
    Ahora soporta historial completo de la conversación.
    """
    if not req.previous_result:
        raise HTTPException(status_code=400, detail="No hay clasificación previa en el contexto.")
    
    try:
        # OPCIONAL: Enriquecer previous_result con historial si el LLM lo necesita
        # Puedes agregar el historial dentro de previous_result["conversation_history"]
        enriched_result = req.previous_result.copy()
        if req.conversation_history:
            enriched_result["conversation_history"] = req.conversation_history
        
        # Llamar al LLM con firma correcta: (question, previous_result)
        answer = generate_followup_answer(
            question=req.question,
            previous_result=enriched_result
        )
        
        return {"answer": answer}
    
    except Exception as e:
        logger.error(f"Error en /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics", include_in_schema=False)
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
