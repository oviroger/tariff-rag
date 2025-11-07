"""
app/ocr_formrec.py
Extracción de texto mediante Azure Document Intelligence (antes Form Recognizer).
"""

import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from .chunking import juridical_chunks
import json
import re
import io

def _get_chunk_params() -> tuple[int, int]:
    """Lee parámetros de chunking desde variables de entorno.
    CHUNK_MAX_CHARS (por defecto 1800), CHUNK_OVERLAP (por defecto 0)."""
    try:
        max_chars = int(os.environ.get("CHUNK_MAX_CHARS", "1800"))
    except Exception:
        max_chars = 1800
    try:
        overlap = int(os.environ.get("CHUNK_OVERLAP", "0"))
    except Exception:
        overlap = 300
    overlap = max(0, min(overlap, max_chars - 1)) if max_chars > 0 else 0
    return max_chars, overlap


def extract_fragments_from_pdf(pdf_path: str, base_metadata: dict) -> list:
    """
    Usa Azure DI para extraer layout (prebuilt-layout) y devuelve chunks jurídicos.
    Respeta parámetros de chunking definidos por entorno (CHUNK_MAX_CHARS/CHUNK_OVERLAP).
    """
    endpoint = os.environ.get("AZURE_FR_ENDPOINT")
    key = os.environ.get("AZURE_FR_KEY")
    if not endpoint or not key:
        raise ValueError("Missing AZURE_FR_ENDPOINT or AZURE_FR_KEY")

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    with open(pdf_path, "rb") as f:
        file_content = f.read()
    
    # For azure-ai-documentintelligence 1.0.2, pass the bytes directly as the body parameter
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=io.BytesIO(file_content)  # file-like para tipado estricto
    )
    result = poller.result()

    text_blocks = []
    if result.paragraphs:
        for para in result.paragraphs:
            if para.content:
                text_blocks.append(para.content)
    else:
        # Fallback: concatenate page content
        if result.pages:
            for pg in result.pages:
                if pg.lines:
                    for line in pg.lines:
                        text_blocks.append(line.content)

    full_text = "\n".join(text_blocks)

    max_chars, overlap = _get_chunk_params()
    # Pasamos base_metadata como meta, con solapamiento opcional
    chunks_list = juridical_chunks(full_text, base_metadata, max_chars=max_chars, overlap=overlap)

    fragments = []
    for idx, chunk_obj in enumerate(chunks_list):
        frag_id = f"{base_metadata.get('doc_id', 'unknown')}_{idx:04d}"
        
        # Extract text from Fragment object if it's a Pydantic model
        if hasattr(chunk_obj, 'text'):
            chunk_text = chunk_obj.text
        elif isinstance(chunk_obj, str):
            chunk_text = chunk_obj
        else:
            chunk_text = str(chunk_obj)
        
        # Fusiona metadatos base con los del chunk (si existen)
        chunk_meta = getattr(chunk_obj, 'metadata', {}) if hasattr(chunk_obj, 'metadata') else {}
        merged_meta = {**base_metadata, **(chunk_meta or {})}

        frag = {
            "fragment_id": frag_id,
            "chunk_id": frag_id,
            "text": chunk_text,
            **merged_meta,
        }
        fragments.append(frag)

    return fragments


def extract_fragments_from_afr_json(json_path: str, base_metadata: dict) -> list:
    """
    Procesa un archivo JSON exportado de Azure Document Intelligence (prebuilt-layout)
    y genera fragmentos aplicando el mismo chunking jurídico.

    Estrategia robusta: recorrer recursivamente y recolectar todos los campos "content"
    en orden de aparición, concatenándolos para formar un texto continuo.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    text_blocks: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            # Priorizar 'content' si es str
            if "content" in node and isinstance(node["content"], str):
                # Filtrar contenidos vacíos o puramente de puntuación suelta
                c = node["content"].strip()
                if c:
                    text_blocks.append(c)
            # Recorrer hijos
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)
        # otros tipos: ignorar

    # Comenzar desde analyzeResult si existe, si no desde raíz
    root = data.get("analyzeResult", data)
    walk(root)

    # Unir en texto continuo, compactando espacios múltiples
    full_text = re.sub(r"\s+", " ", "\n".join(text_blocks)).strip()

    max_chars, overlap = _get_chunk_params()
    chunks_list = juridical_chunks(full_text, base_metadata, max_chars=max_chars, overlap=overlap)

    fragments = []
    for idx, chunk_obj in enumerate(chunks_list):
        frag_id = f"{base_metadata.get('doc_id', 'unknown')}_{idx:04d}"
        if hasattr(chunk_obj, 'text'):
            chunk_text = chunk_obj.text
        elif isinstance(chunk_obj, str):
            chunk_text = chunk_obj
        else:
            chunk_text = str(chunk_obj)

        chunk_meta = getattr(chunk_obj, 'metadata', {}) if hasattr(chunk_obj, 'metadata') else {}
        merged_meta = {**base_metadata, **(chunk_meta or {})}

        frag = {
            "fragment_id": frag_id,
            "chunk_id": frag_id,
            "text": chunk_text,
            **merged_meta,
        }
        fragments.append(frag)

    return fragments