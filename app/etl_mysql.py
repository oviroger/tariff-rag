import hashlib
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
    
    query = """
    SELECT 
        codigoproducto,
        Partida,
        Mercancia,
        Param_1, Param_2, Param_3, Param_4, Param_5,
        Param_6, Param_7, Param_8, Param_9, Param_11, Param_12, Param_14
    FROM asgard
    WHERE Mercancia IS NOT NULL
    """
    
    with engine.connect() as conn:
        result = conn.execute(sql_text(query))
        rows = result.fetchall()
        columns = result.keys()
    
    out: List[Fragment] = []
    
    for row in rows:
        # Convertir row a diccionario
        row_dict = dict(zip(columns, row))
        
        codigo = row_dict.get('codigoproducto') or 'SIN_CODIGO'
        partida = row_dict.get('Partida') or ''
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
                "partida": partida,
                "codigo_producto": codigo
            }
        ))
    
    return out