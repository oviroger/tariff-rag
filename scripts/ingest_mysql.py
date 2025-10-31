import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.etl_mysql import extract_mysql_fragments, extract_asgard_fragments
from app.os_ingest import bulk_ingest_fragments
from app.config import get_settings

def main():
    s = get_settings()
    
    # Detectar si queremos ingestar tabla asgard o genérica
    table = os.environ.get("MYSQL_TABLE", "asgard")
    
    if table.lower() == "asgard":
        print("📊 Ingesta desde tabla ASGARD...")
        fr_db = extract_asgard_fragments()
    else:
        # Modo genérico para otras tablas
        text_col = os.environ.get("MYSQL_TEXT_COL", "description")
        id_col = os.environ.get("MYSQL_ID_COL", "id")
        print(f"📊 Ingesta genérica desde tabla {table}...")
        fr_db = extract_mysql_fragments(table, text_col, id_col)
    
    if fr_db:
        bulk_ingest_fragments([f.model_dump() for f in fr_db], s.opensearch_index)
        print(f"✅ Ingestados {len(fr_db)} fragmentos desde MySQL")
        
        # Mostrar ejemplo del primer fragmento
        if fr_db:
            print("\n📝 Ejemplo del primer fragmento:")
            print(f"   ID: {fr_db[0].fragment_id}")
            print(f"   Texto: {fr_db[0].text[:200]}...")
            print(f"   Metadata: {fr_db[0].metadata}")
    else:
        print("ℹ️ No se encontraron registros con texto.")

if __name__ == "__main__":
    main()