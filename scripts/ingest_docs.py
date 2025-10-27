import os, sys, glob, logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ocr_formrec import extract_fragments_from_pdf
from app.os_ingest import bulk_ingest_fragments
from app.config import get_settings

# Mapeo de carpeta → metadatos (ajusta a tu estructura)
FOLDER_META = {
    "00_WCO":        {"source": "WCO",        "jurisdiction":"INT",   "edition":"HS_2022"},
    "10_CAN":        {"source": "CAN",        "jurisdiction":"REG_CAN","edition":"HS_2022"},
    "20_BO":         {"source": "BO_ARANCEL", "jurisdiction":"BO",    "edition":"HS_2022"},
    "90_Comparados": {"source": "COMPARADOS", "jurisdiction":"EXT",   "edition":"HS_2022"},
}
CORPUS_ROOT = "data/corpus"
BULK_BATCH = int(os.environ.get("BULK_BATCH", "800"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

def iter_pdfs():
    # Busca recursivo en subcarpetas
    for bucket in FOLDER_META.keys():
        folder = os.path.join(CORPUS_ROOT, bucket)
        for path in glob.glob(os.path.join(folder, "*.pdf")):
            yield bucket, path

def main():
    s = get_settings()
    total_frags = 0
    batch = []

    for bucket, path in iter_pdfs():
        meta_defaults = FOLDER_META[bucket]
        doc_id = os.path.splitext(os.path.basename(path))[0]
        fname = os.path.basename(path)
        base_meta = {
            "doc_id": doc_id,
            "bucket": bucket,
            "filename": fname,
            "validity_from": "2022-01-01",
            "unit": "SECTION"
        }
        try:
            frs = extract_fragments_from_pdf(path, base_meta)  # Azure DI + chunking
            cur = frs  # Ya son diccionarios, no necesitan model_dump()
            batch.extend(cur)
            total_frags += len(cur)
            logging.info(f"[{bucket}] {doc_id}: {len(cur)} fragmentos")

            if len(batch) >= BULK_BATCH:
                logging.info(f"Indexando batch de {len(batch)} → {s.opensearch_index}")
                bulk_ingest_fragments(batch, s.opensearch_index)
                batch = []
        except Exception as e:
            logging.exception(f"ERROR procesando {path}: {e}")

    # Último batch
    if batch:
        logging.info(f"Indexando batch final de {len(batch)} → {s.opensearch_index}")
        bulk_ingest_fragments(batch, s.opensearch_index)

    if total_frags == 0:
        logging.warning("ℹ️ No se hallaron PDFs en data/corpus/**.pdf")
    else:
        logging.info(f"✅ Ingestados {total_frags} fragmentos → {s.opensearch_index}")

if __name__ == "__main__":
    main()
