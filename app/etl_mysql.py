import hashlib
from typing import List
from sqlalchemy import create_engine, text as sql_text
from .schemas import Fragment
from .config import get_settings

def mysql_url():
    s = get_settings()
    # Usamos PyMySQL (ya instalado)
    return f"mysql+pymysql://{s.mysql_user}:{s.mysql_password}@{s.mysql_host}:{s.mysql_port}/{s.mysql_db}"

def extract_mysql_fragments(table: str, text_col: str, id_col: str) -> List[Fragment]:
    engine = create_engine(mysql_url(), pool_pre_ping=True)
    with engine.connect() as conn:
        rows = conn.execute(sql_text(f"SELECT {id_col}, {text_col} FROM {table} WHERE {text_col} IS NOT NULL")).fetchall()

    out: List[Fragment] = []
    for rid, txt in rows:
        if not txt or not str(txt).strip():
            continue
        fid = hashlib.md5(f"DB::{table}::{rid}".encode()).hexdigest()[:12]
        out.append(Fragment(
            fragment_id=fid, source="DB",
            doc_id=f"{table}:{rid}", unit="DB_ROW",
            text=str(txt), edition="DB_SNAPSHOT"
        ))
    return out