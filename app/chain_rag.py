from typing import Any, Dict, List, Optional
import logging

from app.config import get_settings
from app.schemas import ClassifyResponse, Candidate, Citation

# OCR best-effort
try:
    from .ocr_formrec import extract_text_best_effort as _extract_text_best_effort
except Exception:
    def _extract_text_best_effort(text: Optional[str], file_url: Optional[str]) -> str:
        return text or ""

# Truncado/guardrails
try:
    from .guardrails import truncate as _truncate
except Exception:
    def _truncate(s: str, max_chars: int = 5000) -> str:
        return (s or "")[:max_chars]

# Reglas rápidas (opcional)
try:
    from .rules import rule_based_label as _rule_based_label
except Exception:
    def _rule_based_label(_: str) -> Optional[str]:
        return None

# Embeddings (opcional)
try:
    from .embedder_gemini import GeminiEmbedder as _GeminiEmbedder
except Exception:
    _GeminiEmbedder = None

# Retriever (opcional)
try:
    from .lc_retriever import retrieve as _retrieve
except Exception:
    def _retrieve(_: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        return []

# Generación LLM (opcional)
try:
    from .generator_gemini import generate_label as _generate_label
except Exception:
    def _generate_label(query: str, context_chunks: List[str]) -> Dict[str, Any]:
        return {"label": "UNKNOWN", "score": 0.0, "reasons": ["Generador no disponible."]}

logger = logging.getLogger(__name__)
settings = get_settings()

# Estado global simple para el embedder
_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is None and _GeminiEmbedder is not None:
        _embedder = _GeminiEmbedder()
    return _embedder

def classify(
    text: str,
    file_url: Optional[str] = None,
    top_k: int = 5,
    debug: bool = False
) -> ClassifyResponse:
    """
    Pipeline RAG con guardrails:
    1. OCR si file_url presente
    2. Recuperación híbrida (BM25 + kNN)
    3. Validación de evidencia (umbrales)
    4. Generación con Gemini (JSON estructurado)
    5. Validación de salida y fallback
    """
    
    debug_info = {} if debug else None
    
    # === 1. OCR (opcional) ===
    if file_url:
        try:
            from app.ocr_formrec import extract_fragments_from_pdf
            # Descarga y procesa PDF (implementa download si no existe)
            # fragments = extract_fragments_from_pdf(local_path, {"source": file_url})
            # text += "\n" + "\n".join([f.text for f in fragments[:3]])
            logger.info(f"OCR solicitado para {file_url}")
        except Exception as e:
            logger.warning(f"OCR falló: {e}")
    
    # === 2. Recuperación ===
    try:
        from app.os_retrieval import retrieve_fragments  # FIXED: was retrieve

        # Recupera documentos (retrieve_fragments handles embedding internally)
        docs = retrieve_fragments(query_text=text, top_k=top_k * 2)

        if debug_info is not None:
            debug_info["retrieved_count"] = len(docs)
            debug_info["top_scores"] = [d.get("_score", 0.0) for d in docs[:5]]

    except Exception as e:
        logger.error(f"Recuperación falló: {e}")
        return ClassifyResponse(
            warnings=[f"Error en recuperación: {str(e)}"],
            missing_fields=["retrieval_failed"],
            debug_info=debug_info
        )
    
    # === 3. Guardrail: Evidencia insuficiente ===
    min_evidence = getattr(settings, "min_evidence", 2)
    min_score = getattr(settings, "min_score", 0.3)
    
    valid_docs = [d for d in docs if d.get("_score", 0.0) >= min_score]
    
    if len(valid_docs) < min_evidence:
        logger.warning(f"Evidencia insuficiente: {len(valid_docs)} < {min_evidence}")
        return ClassifyResponse(
            evidence=[
                Citation(
                    fragment_id=d.get("_id", "unknown"),
                    score=d.get("_score", 0.0),
                    text=d.get("_source", {}).get("text", "")[:200],
                    reason="score_bajo"
                ) for d in docs[:3]
            ],
            warnings=["Evidencia insuficiente para clasificación confiable"],
            missing_fields=["material", "uso", "presentación"],
            applied_rgi=["RGI 1"],
            debug_info=debug_info
        )
    
    # === 4. Generación con Gemini ===
    try:
        from app.generator_gemini import generate_label
        
        # Llamada REAL a Gemini con structured output
        result = generate_label(text, valid_docs[:top_k], max_candidates=3)
        
        # Si Gemini no devuelve missing_fields, usar detector local
        if not result.get("missing_fields"):
            try:
                from app.missing_fields_detector import detect_missing_fields
                result["missing_fields"] = detect_missing_fields(text, valid_docs)
            except:
                result["missing_fields"] = []
        
    except Exception as e:
        logger.error(f"Generación con Gemini falló: {e}")
        
        # FALLBACK a detector local + stub
        try:
            from app.missing_fields_detector import detect_missing_fields
            detected_missing = detect_missing_fields(text, valid_docs)
        except:
            detected_missing = ["información del producto incompleta"]
        
        result = {
            "top_candidates": [
                {"code": "0000.00.00", "description": "Clasificación no disponible (generador offline)", "confidence": 0.0, "level": "chapter"}
            ],
            "applied_rgi": ["RGI 1"],
            "inclusions": [],
            "exclusions": [],
            "missing_fields": detected_missing
        }
    
    # === 5. Validación de salida ===
    try:
        candidates = [Candidate(**c) for c in result.get("top_candidates", [])]
        evidence = [
            Citation(
                fragment_id=d.get("_id", ""),
                score=d.get("_score", 0.0),
                text=d.get("_source", {}).get("text", "")[:300],
                reason="retrieved_by_hybrid_search"
            ) for d in valid_docs[:top_k]
        ]
        
        response = ClassifyResponse(
            top_candidates=candidates,
            evidence=evidence,
            applied_rgi=result.get("applied_rgi", ["RGI 1"]),
            inclusions=result.get("inclusions", []),
            exclusions=result.get("exclusions", []),
            missing_fields=result.get("missing_fields", []),
            warnings=result.get("warnings", []),
            versions={"hs_edition": "HS_2022"},
            debug_info=debug_info
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Validación de salida falló: {e}")
        return ClassifyResponse(
            warnings=[f"Estructura JSON inválida: {str(e)}"],
            missing_fields=["validation_failed"],
            debug_info=debug_info
        )
