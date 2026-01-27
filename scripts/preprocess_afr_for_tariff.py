#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preprocess_afr_for_tariff.py

Preprocesa JSONs de AFR extrayendo solo texto relevante para clasificación arancelaria.
Filtra encabezados, pie de página, números de página, información técnica irrelevante.
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

def is_relevant_paragraph(text: str, role: str = None) -> bool:
    """Detecta si un párrafo es relevante para aranceles."""
    t = text.strip().lower()
    
    # Excluir: muy cortos
    if len(t) < 10:
        return False
    
    # Excluir: números de página
    if re.match(r"^(página|page|pag\.?|pp?\.?)\s*\d+", t):
        return False
    
    # Excluir: solo fechas
    if re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", t):
        return False
    
    # Excluir: headers/footers comunes
    if role and role.lower() in ["pageheader", "pagefooter", "pagenumber"]:
        return False
    
    # Excluir: líneas con solo código HS sin descripción (ej: "8703.10")
    if re.match(r"^\d{4}\.\d{2}$", t) and len(t) < 15:
        return False
    
    # Incluir: contenido arancelario
    tariff_keywords = [
        "partida", "subpartida", "descripcion", "descripción", "arancel",
        "aduanero", "importacion", "importación", "exportacion", "exportación",
        "material", "composicion", "composición", "uso", "presentacion", "presentación",
        "clasificacion", "clasificación", "mercancia", "mercancía",
        "producto", "articulo", "artículo", "codigo", "código",
        "incluye", "excluye", "comprende", "abarca"
    ]
    
    # Si tiene palabras clave arancelarias, es relevante
    if any(kw in t for kw in tariff_keywords):
        return True
    
    # Si parece código HS con descripción (ej: "8703.10 - Vehículos...")
    if re.search(r"\d{4}\.\d{2}", t) and len(t) > 20:
        return True
    
    return False

def preprocess_afr_json(input_path: str, output_path: str):
    """Lee AFR JSON y extrae solo párrafos relevantes."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    ar = data.get("analyzeResult", {})
    paragraphs = ar.get("paragraphs", [])
    tables = ar.get("tables", [])
    
    # Filtrar párrafos relevantes y extraer solo campos necesarios
    relevant_paras = []
    for p in paragraphs:
        content = p.get("content", "")
        role = p.get("role")
        if is_relevant_paragraph(content, role):
            # Solo mantener campos útiles para el chatbot
            page_num = None
            if p.get("boundingRegions"):
                page_num = p["boundingRegions"][0].get("pageNumber")
            
            relevant_paras.append({
                "content": content,
                "role": role,
                "page": page_num
            })
    
    print(f"📄 {Path(input_path).name}")
    print(f"   Original: {len(paragraphs)} párrafos, {len(tables)} tablas")
    print(f"   Filtrado: {len(relevant_paras)} párrafos relevantes")
    
    # Simplificar tablas: solo mantener contenido de celdas sin coordenadas
    simplified_tables = []
    for tbl in tables:
        cells = tbl.get("cells", [])
        simplified_tables.append({
            "rowCount": tbl.get("rowCount"),
            "columnCount": tbl.get("columnCount"),
            "cells": [
                {
                    "rowIndex": c.get("rowIndex"),
                    "columnIndex": c.get("columnIndex"),
                    "content": c.get("content", "")
                }
                for c in cells
            ]
        })
    
    # Crear salida minimalista
    output_data = {
        "source": str(Path(input_path).name),
        "stats": {
            "original_paragraphs": len(paragraphs),
            "filtered_paragraphs": len(relevant_paras),
            "tables": len(tables),
            "reduction_percent": round((1 - len(relevant_paras)/len(paragraphs)) * 100, 1) if paragraphs else 0
        },
        "analyzeResult": {
            "apiVersion": ar.get("apiVersion"),
            "modelId": ar.get("modelId"),
            "paragraphs": relevant_paras,
            "tables": simplified_tables
        }
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✓ Guardado en {output_path}")
    print(f"   📉 Reducción: {output_data['stats']['reduction_percent']}%\n")
    
    # Mostrar primeros 3 párrafos relevantes como muestra
    print("   Muestra de párrafos relevantes:")
    for i, p in enumerate(relevant_paras[:3], 1):
        snippet = p.get("content", "")[:100]
        print(f"   {i}. {snippet}{'...' if len(p.get('content', '')) > 100 else ''}")
    print()

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Preprocesa JSONs de AFR para clasificación arancelaria")
    ap.add_argument("input", nargs="?", default="data/afr_done/Arancel_Boliviano_2025_Parte_1.json",
                    help="Archivo JSON o carpeta con JSONs a procesar")
    ap.add_argument("--output", "-o", help="Archivo o carpeta de salida (default: {input}_filtered)")
    args = ap.parse_args()
    
    input_path = Path(args.input)
    
    # Procesar carpeta completa
    if input_path.is_dir():
        output_dir = Path(args.output) if args.output else Path(str(input_path) + "_filtered")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_files = list(input_path.glob("*.json"))
        print(f"\n🗂️  Procesando {len(json_files)} archivos de {input_path}\n")
        
        for json_file in sorted(json_files):
            output_file = output_dir / json_file.name
            try:
                preprocess_afr_json(str(json_file), str(output_file))
            except Exception as e:
                print(f"❌ Error procesando {json_file.name}: {e}\n")
        
        print(f"\n✅ Completado. Archivos guardados en {output_dir}")
    
    # Procesar archivo individual
    else:
        output_file = args.output if args.output else str(input_path).replace(".json", "_filtered.json")
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        preprocess_afr_json(str(input_path), output_file)
