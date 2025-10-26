import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import glob
from app.ocr_formrec import extract_fragments_from_pdf
from app.os_ingest import bulk_ingest_fragments
from app.config import get_settings

def main():
    s = get_settings()
    pdfs = glob.glob("data/corpus/*.pdf")
    all_docs = []
    for path in pdfs:
        doc_id = os.path.splitext(os.path.basename(path))[0]
        meta = {
            "doc_id": doc_id, "source": "DOC",
            "edition": "HS_2022", "validity_from": "2022-01-01",
            "unit": "SECTION"
        }
        frs = extract_fragments_from_pdf(path, meta)
        all_docs.extend([f.model_dump() for f in frs])

    if not all_docs:
        print("ℹ️ No se hallaron PDFs en data/corpus")
        return

    bulk_ingest_fragments(all_docs, s.opensearch_index)
    print(f"✅ Ingestados {len(all_docs)} fragmentos → {s.opensearch_index}")

if __name__ == "__main__":
    main()