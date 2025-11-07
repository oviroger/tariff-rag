import hashlib
import re
import os
from typing import List, Dict, Any
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
            fragment_id=fid,
            text=str(txt),
            metadata={
                "source": "DB",
                "doc_id": f"{table}:{rid}",
                "unit": "DB_ROW",
                "edition": "DB_SNAPSHOT"
            }
        ))
    return out

def extract_asgard_fragments() -> List[Fragment]:
    """
    Extrae fragmentos de la tabla 'asgard' concatenando todos los campos relevantes
    en un texto descriptivo para clasificación arancelaria.
    """
    engine = create_engine(mysql_url(), pool_pre_ping=True)

    # Permitir limitar filas para pruebas/control de costos de embeddings
    limit = os.getenv("MYSQL_LIMIT")
    offset = os.getenv("MYSQL_OFFSET")
    order_col = os.getenv("MYSQL_ORDER", "codigoproducto")
    order_dir = os.getenv("MYSQL_ORDER_DIR", "ASC").upper()
    if order_dir not in ("ASC", "DESC"):
        order_dir = "ASC"
    try:
        limit_val = int(limit) if limit else None
    except ValueError:
        limit_val = None
    try:
        offset_val = int(offset) if offset else None
    except ValueError:
        offset_val = None

    base_query = (
        "SELECT "
        " codigoproducto,"
        " Partida,"
        " Mercancia,"
        " Param_1, Param_2, Param_3, Param_4, Param_5,"
        " Param_6, Param_7, Param_8, Param_9, Param_11, Param_12, Param_14"
        " FROM asgard"
        " WHERE Partida IS NOT NULL"
    )
    # Orden estable para paginación determinística
    order_clause = f" ORDER BY {order_col} {order_dir}"
    limit_clause = f" LIMIT {limit_val}" if limit_val and limit_val > 0 else ""
    offset_clause = f" OFFSET {offset_val}" if offset_val and offset_val >= 0 and limit_clause else ""
    query = base_query + order_clause + limit_clause + offset_clause
    
    with engine.connect() as conn:
        result = conn.execute(sql_text(query))
        rows = result.fetchall()
        columns = result.keys()
    
    out: List[Fragment] = []
    
    for row in rows:
        # Convertir row a diccionario
        row_dict = dict(zip(columns, row))

        codigo = row_dict.get('codigoproducto') or 'SIN_CODIGO'
        partida_raw = row_dict.get('Partida') or ''
        # Normalizar partida para extraer solo dígitos (ej. "PARTIDA ARANCELARIA: 48193010000" → 48193010000)
        m = re.search(r"(\d{6,12})", str(partida_raw))
        partida_digits = m.group(1) if m else ""
        hs6 = partida_digits[:6] if partida_digits else ""
        partida = partida_raw
        mercancia = row_dict.get('Mercancia') or ''

        # Construir texto descriptivo concatenando todos los parámetros no vacíos
        text_parts = []

        # Agregar mercancía principal
        if mercancia:
            text_parts.append(f"MERCANCÍA: {mercancia}")

        # Agregar partida si existe
        if partida:
            text_parts.append(f"PARTIDA: {partida}")

        # Agregar todos los parámetros que tengan valor
        param_fields = ['Param_1', 'Param_2', 'Param_3', 'Param_4', 'Param_5',
                        'Param_6', 'Param_7', 'Param_8', 'Param_9', 'Param_11',
                        'Param_12', 'Param_14']

        for param in param_fields:
            value = row_dict.get(param)
            if value and str(value).strip() and str(value).upper() not in ['NULL', 'SIN REFERENCIA']:
                text_parts.append(str(value))

        # Concatenar todo el texto
        full_text = " | ".join(text_parts)

        if not full_text.strip():
            continue

        # Generar fragment_id único
        fid = hashlib.md5(f"ASGARD::{codigo}".encode()).hexdigest()[:12]

        out.append(Fragment(
            fragment_id=fid,
            text=full_text,
            metadata={
                "source": "ASGARD_DB",
                "doc_id": f"asgard:{codigo}",
                "unit": "PRODUCT",
                "edition": "ASGARD_IMPORT",
                "bucket": "asgard_products",
                "partida": partida_digits or partida,
                "hs6": hs6,
                "codigo_producto": codigo
            }
        ))
    
    return out