import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.etl_mysql import extract_mysql_fragments, extract_asgard_fragments
from app.os_ingest import bulk_ingest_fragments
from app.config import get_settings

def main():
    s = get_settings()
    target_index = os.environ.get("TARGET_INDEX") or os.environ.get("OPENSEARCH_INDEX") or s.opensearch_index
    limit = os.environ.get("MYSQL_LIMIT")
    no_embed = os.environ.get("NO_EMBED")
    offset = os.environ.get("MYSQL_OFFSET")
    
    # Detectar si queremos ingestar tabla asgard o genérica
    table = os.environ.get("MYSQL_TABLE", "asgard")
    
    if table.lower() == "asgard":
        print("📊 Ingesta desde tabla ASGARD...")
        print(f"   → índice destino: {target_index}")
        if limit:
            print(f"   → límite de filas (MYSQL_LIMIT): {limit}")
        if offset:
            print(f"   → desplazamiento (MYSQL_OFFSET): {offset}")
        if no_embed in ("1","true","True"):
            print("   → embeddings: DESACTIVADOS (NO_EMBED=1)")
        fr_db = extract_asgard_fragments()
    else:
        # Modo genérico para otras tablas
        text_col = os.environ.get("MYSQL_TEXT_COL", "description")
        id_col = os.environ.get("MYSQL_ID_COL", "id")
        print(f"📊 Ingesta genérica desde tabla {table}...")
        fr_db = extract_mysql_fragments(table, text_col, id_col)
    
    if fr_db:
        bulk_ingest_fragments([f.model_dump() for f in fr_db], target_index)
        print(f"✅ Ingestados {len(fr_db)} fragmentos desde MySQL en índice '{target_index}'")
        
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