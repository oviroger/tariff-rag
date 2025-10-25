import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.etl_mysql import extract_mysql_fragments
from app.os_ingest import bulk_ingest_fragments
from app.config import get_settings

def main():
    s = get_settings()
    table = os.environ.get("MYSQL_TABLE","product_cases")
    text_col = os.environ.get("MYSQL_TEXT_COL","description")
    id_col = os.environ.get("MYSQL_ID_COL","id")

    fr_db = extract_mysql_fragments(table, text_col, id_col)
    if fr_db:
        bulk_ingest_fragments([f.model_dump() for f in fr_db], s.opensearch_index)
        print(f"✅ Ingestados {len(fr_db)} fragmentos desde MySQL")
    else:
        print("ℹ️ No se encontraron registros con texto.")

if __name__ == "__main__":
    main()