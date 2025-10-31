#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opensearch_ingest_afr.py

Ingesta directa a OpenSearch (BM25 + kNN) de:
  (A) Resultados JSON de Azure Form Recognizer (Layout), o
  (B) Un JSONL de chunks ya generado (corpus_chunks.jsonl).

Esta versión usa el entorno del proyecto (config/env) y las
embeddings de Gemini a través de app.os_ingest.bulk_ingest_fragments.
"""
import argparse
import json
import os
import sys
import time
import logging
from typing import Any, Dict, Iterable, List, Optional, Generator
import hashlib
from pathlib import Path
from datetime import datetime
import pickle

# Hacer import del paquete app/*
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import get_settings
from app.os_index import get_os_client
from app.os_ingest import bulk_ingest_fragments

# --------------- Lógica de AFR -> chunks --------------
def sha16(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def page_from_regions(regions: Optional[List[Dict[str, Any]]]) -> Optional[int]:
    if not regions:
        return None
    for r in regions:
        if isinstance(r, dict) and "pageNumber" in r:
            return r["pageNumber"]
    return None

def build_metadata(doc_id: str, source: str, api_version: Optional[str], model_id: Optional[str], **kwargs) -> Dict[str, Any]:
    m = {
        "doc_id": doc_id,
        "source": source,
        "apiVersion": api_version,
        "modelId": model_id,
    }
    for k, v in kwargs.items():
        if v is not None:
            m[k] = v
    return m

def transform_analyze_result(ar: Dict[str, Any], source_name: str) -> List[Dict[str, Any]]:
    doc_id = sha16(source_name)
    api_version = ar.get("apiVersion")
    model_id   = ar.get("modelId")
    chunks: List[Dict[str, Any]] = []

    for i, para in enumerate(ar.get("paragraphs", []) or []):
        text = para.get("content") or ""
        if not text:
            continue
        page_num = page_from_regions(para.get("boundingRegions"))
        role = para.get("role")
        span = (para.get("spans") or [{}])[0] if para.get("spans") else {}
        chunk_id = f"{doc_id}_p{i}"
        chunks.append({
            "id": chunk_id,
            "type": "text",
            "text": text,
            "metadata": build_metadata(doc_id, source_name, api_version, model_id,
                                       page_num=page_num, index=i, role=role, span=span, kind="paragraph"),
        })

    for ti, tbl in enumerate(ar.get("tables", []) or []):
        page_num = page_from_regions(tbl.get("boundingRegions"))
        nrows = int(tbl.get("rowCount") or 0)
        ncols = int(tbl.get("columnCount") or 0)
        grid = [["" for _ in range(ncols)] for _ in range(nrows)]
        for c in tbl.get("cells", []) or []:
            r = int(c.get("rowIndex") or 0)
            cidx = int(c.get("columnIndex") or 0)
            txt = c.get("content") or ""
            if 0 <= r < nrows and 0 <= cidx < ncols:
                grid[r][cidx] = txt

        lines: List[str] = []
        if nrows > 0 and ncols > 0:
            header = grid[0]
            lines.append("| " + " | ".join(h if h is not None else "" for h in header) + " |")
            lines.append("| " + " | ".join(["---"] * ncols) + " |")
            for rr in grid[1:]:
                lines.append("| " + " | ".join(rr) + " |")
        table_text = "\n".join(lines)

        chunk_id = f"{doc_id}_t{ti}"
        chunks.append({
            "id": chunk_id,
            "type": "table",
            "text": table_text,
            "metadata": build_metadata(doc_id, source_name, api_version, model_id,
                                       page_num=page_num, index=ti, kind="table",
                                       shape={"rows": nrows, "cols": ncols}),
        })

    for fi, fig in enumerate(ar.get("figures", []) or []):
        caption = fig.get("caption") or ""
        page_num = page_from_regions(fig.get("boundingRegions"))
        chunk_id = f"{doc_id}_f{fi}"
        chunks.append({
            "id": chunk_id,
            "type": "figure",
            "text": caption,
            "metadata": build_metadata(doc_id, source_name, api_version, model_id,
                                       page_num=page_num, index=fi, kind="figure"),
        })
    return chunks

def detect_analyze_result(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if "analyzeResult" in payload and isinstance(payload["analyzeResult"], dict):
        return payload["analyzeResult"]
    return None

# --------------- OpenSearch utils ----------------------
def ensure_index(client, index_name: str, dim: int, knn_space: str = "cosinesimil",
                 shards: int = 1, replicas: int = 0, analyzer: str = "spanish") -> None:
    """
    Crea el índice si no existe con el mapping esperado por la app:
    - text (text)
    - embedding (knn_vector, dim=dim, space=knn_space)
    - metadata (object enabled)
    - fragment_id/doc_id/source/page/type/role/kind/bucket (campos auxiliares)
    """
    if client.indices.exists(index=index_name):
        return

    settings = {
        "index": {
            "number_of_shards": shards,
            "number_of_replicas": replicas,
            "knn": True
        },
        "analysis": {
            "analyzer": {
                "default": {"type": analyzer}
            }
        }
    }
    mappings = {
        "properties": {
            "text": {"type": "text"},
            "embedding": {
                "type": "knn_vector",
                "dimension": dim,
                "method": {
                    "name": "hnsw",
                    "space_type": knn_space,
                    "engine": "nmslib"
                }
            },
            "metadata": {"type": "object", "enabled": True},
            "fragment_id": {"type": "keyword"},
            "doc_id": {"type": "keyword"},
            "source": {"type": "keyword"},
            "bucket": {"type": "keyword"},
            "page": {"type": "integer"},
            "type": {"type": "keyword"},
            "role": {"type": "keyword"},
            "kind": {"type": "keyword"},
            "indexed_at": {"type": "date"}
        }
    }
    body = {"settings": settings, "mappings": mappings}
    client.indices.create(index=index_name, body=body)

# --------------- Lectores de entrada -------------------
def _iter_json_objects_from_file(path: str) -> Generator[Dict[str, Any], None, None]:
    """
    Lee un archivo que puede ser:
    - JSON único (AFR)
    - Múltiples JSON concatenados
    - JSONL (un objeto por línea)
    """
    import json
    from json.decoder import JSONDecodeError

    # 1) Intento JSON único
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            obj = json.load(f)
        yield obj
        return
    except JSONDecodeError:
        pass
    except Exception as e:
        logging.warning("No se pudo cargar como JSON único %s: %s", path, e)

    # 2) Intento múltiples JSON concatenados (raw_decode)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        decoder = json.JSONDecoder()
        idx = 0
        n = len(content)
        any_obj = False
        while idx < n:
            # saltar espacios
            while idx < n and content[idx].isspace():
                idx += 1
            if idx >= n:
                break
            obj, next_idx = decoder.raw_decode(content, idx)
            yield obj
            any_obj = True
            idx = next_idx
        if any_obj:
            return
    except Exception:
        # continuar con JSONL
        pass

    # 3) Intento JSONL (un objeto por línea)
    with open(path, "r", encoding="utf-8-sig") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception as e:
                logging.warning("Línea %d inválida en %s: %s", ln, path, e)

def iter_chunks_from_jsonl(path: str) -> Generator[Dict[str, Any], None, None]:
    for obj in _iter_json_objects_from_file(path):
        # Permite tanto chunks directos como payloads AFR por línea
        ar = detect_analyze_result(obj)
        if ar:
            # Devolver los chunks transformados desde AFR payloads que vengan en JSONL
            for ch in transform_analyze_result(ar, os.path.splitext(os.path.basename(path))[0]):
                yield ch
        else:
            yield obj

def iter_chunks_from_afr_dir(dir_path: str, tracking: dict = None, force: bool = False) -> Generator[Dict[str, Any], None, None]:
    """
    Itera sobre chunks de AFR JSONs, saltando archivos ya procesados.
    
    Args:
        dir_path: Directorio con JSONs de AFR
        tracking: Dict de archivos procesados (opcional)
        force: Si True, reprocesa todos los archivos
    """
    tracking = tracking or {}
    files = [f for f in os.listdir(dir_path) if f.lower().endswith(".json")]
    
    for fname in sorted(files):
        fpath = os.path.join(dir_path, fname)
        
        # Saltar si ya fue procesado y no hubo cambios
        if not _should_process_file(fpath, tracking, force):
            continue
        
        try:
            for obj in _iter_json_objects_from_file(fpath):
                ar = detect_analyze_result(obj)
                if ar:
                    source_name = os.path.splitext(fname)[0]
                    for ch in transform_analyze_result(ar, source_name):
                        yield ch
                else:
                    if isinstance(obj, dict) and "text" in obj:
                        yield obj
                    else:
                        logging.debug("Objeto no reconocido en %s, se omite.", fname)
            
            # Registrar como procesado exitosamente
            tracking[fname] = {
                "hash": _get_file_hash(fpath),
                "processed_at": datetime.utcnow().isoformat(),
                "status": "success"
            }
        except Exception as e:
            logging.warning("Error procesando %s: %s", fname, e)
            tracking[fname] = {
                "hash": _get_file_hash(fpath),
                "processed_at": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }

# --------------- Helpers de fragmentos -----------------
def chunk_to_fragment(ch: Dict[str, Any], bucket: str) -> Dict[str, Any]:
    """
    Convierte un chunk {id,type,text,metadata{...}} a un fragmento
    aceptado por bulk_ingest_fragments (usa Gemini internamente).
    """
    md = ch.get("metadata", {}) or {}
    frag = {
        "fragment_id": ch.get("id"),
        "text": ch.get("text", "") or "",
        # Levantar algunos campos al nivel superior para el mapping de la app
        "page": md.get("page_num") or md.get("page"),
        "doc_id": md.get("doc_id"),
        # metadata completa (se agregan banderas de procedencia)
        "metadata": {
            **md,
            "bucket": bucket,
            "source_type": ch.get("type"),
        }
    }
    return frag

def batched(iterable: Iterable[Any], n: int) -> Iterable[List[Any]]:
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch

# --------------- Tracking de archivos procesados ---------------
TRACKING_FILE = Path(__file__).parent.parent / "storage" / "afr_processed.pkl"

def _get_file_hash(file_path: str) -> str:
    """Calcula hash SHA256 del archivo para detectar cambios."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def _load_tracking() -> dict:
    """Carga registro de archivos procesados."""
    if TRACKING_FILE.exists():
        try:
            with open(TRACKING_FILE, "rb") as f:
                return pickle.load(f)
        except Exception:
            logging.warning("No se pudo cargar tracking file, iniciando nuevo")
    return {}

def _save_tracking(tracking: dict):
    """Guarda registro de archivos procesados."""
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, "wb") as f:
        pickle.dump(tracking, f)

def _should_process_file(file_path: str, tracking: dict, force: bool = False) -> bool:
    """
    Determina si un archivo debe procesarse.
    
    Returns:
        True si debe procesarse (nuevo o modificado)
    """
    if force:
        return True
    
    file_hash = _get_file_hash(file_path)
    fname = os.path.basename(file_path)
    
    if fname not in tracking:
        logging.info(f"Nuevo archivo: {fname}")
        return True
    
    if tracking[fname]["hash"] != file_hash:
        logging.info(f"Archivo modificado: {fname}")
        return True
    
    logging.debug(f"Archivo ya procesado (sin cambios): {fname}")
    return False

# --------------- CLI principal -------------------------
def main():
    ap = argparse.ArgumentParser(description="Ingesta AFR/JSONL a OpenSearch usando Gemini (entorno del proyecto).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--afr-input", help="Carpeta con JSONs de AFR (Layout).")
    src.add_argument("--chunks-jsonl", help="Ruta a corpus_chunks.jsonl (o JSONL con {id,type,text,metadata}).")

    ap.add_argument("--index", help="Nombre del índice (default: OPENSEARCH_INDEX de .env).")
    ap.add_argument("--bucket", default=None, help="Etiqueta de fuente/bucket (default: afr|jsonl_import).")
    ap.add_argument("--batch-size", type=int, default=128, help="Tamaño de batch para la ingesta.")
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--replicas", type=int, default=0)
    ap.add_argument("--analyzer", default="spanish", help="Analyzer por defecto para 'text'.")
    # NUEVO: flags de verificación
    ap.add_argument("--refresh", action="store_true", help="Forzar refresh del índice tras cada batch.")
    ap.add_argument("--verify", action="store_true", help="Mostrar conteo de documentos tras cada batch.")
    # NUEVO flag para forzar reprocesamiento
    ap.add_argument("--force", action="store_true", help="Reprocesar todos los archivos, incluso si no cambiaron.")

    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    settings = get_settings()
    index_name = args.index or settings.opensearch_index
    # bucket por defecto según la fuente
    bucket = args.bucket or ("afr" if args.afr_input else "jsonl_import")

    # NUEVO: Cargar tracking
    tracking = _load_tracking()
    force_reprocess = getattr(args, 'force', False)  # Si agregaste flag --force
    
    # Cliente de OpenSearch del proyecto
    client = get_os_client()
    # Dimensión/espacio desde settings (coherente con toda la app)
    emb_dim = int(getattr(settings, "opensearch_emb_dim", 768))
    knn_space = getattr(settings, "opensearch_knn_space", "cosinesimil")

    # Asegurar índice kNN compatible
    ensure_index(client, index_name, dim=emb_dim, knn_space=knn_space,
                 shards=args.shards, replicas=args.replicas, analyzer=args.analyzer)
    logging.info("Índice listo: %s (dim=%d, space=%s)", index_name, emb_dim, knn_space)

    # Fuente de datos con tracking
    if args.afr_input:
        iterator = iter_chunks_from_afr_dir(args.afr_input, tracking=tracking, force=force_reprocess)
    else:
        # JSONL no usa tracking (asumimos que son archivos únicos)
        iterator = iter_chunks_from_jsonl(args.chunks_jsonl)

    # Ingesta en batches con embeddings Gemini vía bulk_ingest_fragments
    total = 0
    for chunk_batch in batched(iterator, args.batch_size):
        # CORREGIDO: fuerza a string antes de strip
        fragments = [
            chunk_to_fragment(ch, bucket=bucket)
            for ch in chunk_batch
            if isinstance(ch.get("text", ""), str) and ch.get("text", "").strip()
        ]
        if not fragments:
            continue
        try:
            bulk_ingest_fragments(fragments, index_name)
            total += len(fragments)
            logging.info("Batch upsert: %d docs (acumulado=%d)", len(fragments), total)
            if args.refresh:
                client.indices.refresh(index=index_name)
            if args.verify:
                cnt = client.count(index=index_name).get("count", 0)
                logging.info("Docs actuales en %s: %d", index_name, cnt)
        except Exception as e:
            logging.warning("Error en batch (%d docs): %s", len(fragments), str(e)[:300])

    # NUEVO: Guardar tracking actualizado
    if args.afr_input:
        _save_tracking(tracking)
        logging.info("Tracking guardado en %s", TRACKING_FILE)
    
    if args.refresh:
        client.indices.refresh(index=index_name)
    if args.verify:
        cnt = client.count(index=index_name).get("count", 0)
        logging.info("Total final de documentos en %s: %d", index_name, cnt)

    logging.info("Ingesta finalizada. Total documentos upsert: %d", total)

if __name__ == "__main__":
    main()
