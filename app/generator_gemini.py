"""
app/generator_gemini.py
Generación de clasificación arancelaria con Gemini structured output.
"""
import json
import logging
import google.generativeai as genai
from typing import Dict, Any, List
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configurar Gemini
api_key = getattr(settings, "gemini_api_key", None)

# Línea ~15:
# api_key = getattr(settings, "gemini_api_key", None) or getattr(settings, "google_api_key", None)
if not api_key:
    logger.warning("No se encontró GEMINI_API_KEY ni GOOGLE_API_KEY")
else:
    genai.configure(api_key=api_key)


def generate_label(query: str, context_docs: List[Dict[str, Any]], max_candidates: int = 3) -> Dict[str, Any]:
    """
    Genera clasificación arancelaria usando Gemini con structured output.
    
    Args:
        query: Descripción del producto a clasificar
        context_docs: Lista de hits de OpenSearch (formato: {_id, _score, _source: {text, ...}})
        max_candidates: Número máximo de códigos candidatos
        
    Returns:
        Dict con: top_candidates, applied_rgi, inclusions, exclusions, missing_fields
    """
    
    # Construir evidencia desde hits de OpenSearch
    evidence = []
    for doc in context_docs[:5]:  # Top 5 para no exceder límites
        source = doc.get("_source", {})
        evidence.append({
            "fragment_id": doc.get("_id", "unknown"),
            "score": doc.get("_score", 0.0),
            "text": source.get("text", "")[:600],  # Limitar texto
            "doc_id": source.get("doc_id", ""),
            "unit": source.get("unit", ""),
            "bucket": source.get("bucket", "")
        })
    
    # Contexto textual para el prompt
    context_text = "\n\n".join([
        f"[Fragment {e['fragment_id']} | Score: {e['score']:.3f}]\n{e['text']}"
        for e in evidence
    ])
    
    # Prompt estructurado
    prompt = f"""You are an expert in tariff classification using the Harmonized System (HS).

PRODUCT DESCRIPTION:
{query}

RELEVANT HS DOCUMENTATION (from tariff database):
{context_text}

TASK:
Based on the product description and HS documentation, provide a complete tariff classification analysis.

INSTRUCTIONS:
1. Identify {max_candidates} most likely HS codes with confidence scores
2. Apply relevant General Rules for Interpretation (RGI)
3. List what products are INCLUDED in this classification
4. List what products are EXCLUDED
5. Identify any MISSING information needed for precise classification

Return your analysis as a JSON object with this structure:
{{
  "top_candidates": [
    {{
      "code": "XXXX.XX.XX",
      "description": "Brief product category description",
      "confidence": 0.85,
      "level": "subheading"
    }}
  ],
  "applied_rgi": ["RGI 1", "RGI 3(b)"],
  "inclusions": ["Products or characteristics included"],
  "exclusions": ["Products or characteristics excluded"],
  "missing_fields": ["Specific information needed"]
}}

RULES:
- Use actual HS codes from the documentation when available
- Confidence: 0.8-1.0 (high), 0.5-0.8 (medium), 0.3-0.5 (low)
- Level: chapter (4 digits), heading (6 digits), subheading (8+ digits)
- If info is insufficient, list specific missing fields
- Apply RGI sequentially (1, then 2, then 3, etc.)

Return ONLY valid JSON, no markdown formatting.
"""
    
    try:
        # Usar modelo por default o el configurado
        model_name = "models/gemini-2.0-flash"  # Incluir prefijo models/
        
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json"
            },
            # AÑADIR: Safety settings más permisivos
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
            }
        )
        
        logger.info(f"Llamando a Gemini {model_name} para generación...")
        response = model.generate_content(prompt)
        
        # AÑADIR: Manejo de respuestas bloqueadas
        if not response.parts:
            logger.warning(f"Gemini bloqueó la respuesta. Finish reason: {response.candidates[0].finish_reason}")
            logger.warning(f"Safety ratings: {response.candidates[0].safety_ratings}")
            raise ValueError(f"Gemini bloqueó el contenido (finish_reason={response.candidates[0].finish_reason})")
        
        # Parsear JSON
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback: extraer JSON si viene con markdown
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            result = json.loads(text.strip())
        
        # Validación y defaults
        result.setdefault("top_candidates", [])
        result.setdefault("applied_rgi", ["RGI 1"])
        result.setdefault("inclusions", [])
        result.setdefault("exclusions", [])
        result.setdefault("missing_fields", [])
        
        logger.info(f"Gemini generó {len(result.get('top_candidates', []))} candidatos")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Gemini no devolvió JSON válido: {e}")
        raise ValueError(f"Respuesta de Gemini no es JSON válido: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error en generación con Gemini: {e}")
        raise RuntimeError(f"Error llamando a Gemini API: {str(e)}")


def generate_structured(query: str, docs: list, versions: dict) -> dict:
    """
    Función legacy para compatibilidad con código anterior.
    Redirige a generate_label con conversión de formato.
    """
    # Convertir formato LangChain a formato OpenSearch
    os_docs = []
    for d in docs:
        if hasattr(d, 'metadata') and hasattr(d, 'page_content'):
            # Formato LangChain
            os_docs.append({
                "_id": d.metadata.get("fragment_id", ""),
                "_score": 1.0,
                "_source": {
                    "text": d.page_content,
                    "doc_id": d.metadata.get("source", ""),
                    "unit": d.metadata.get("unit", ""),
                    "edition": d.metadata.get("edition", "")
                }
            })
        else:
            # Ya es formato OpenSearch
            os_docs.append(d)
    
    return generate_label(query, os_docs)
