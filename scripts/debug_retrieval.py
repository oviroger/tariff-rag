#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de debugging: Muestra exactamente qué documentos se recuperan
para las consultas problemáticas.
"""
import requests
import json
import sys
import os

# Configurar UTF-8
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

API_URL = "http://localhost:8000"

def debug_retrieval(query: str, years: list = None):
    """Debug: Muestra documentos recuperados para una query."""
    if years is None:
        years = [2025, 2026]
    
    print(f"\n{'='*80}")
    print(f"DEBUGGING QUERY: {query}")
    print(f"YEARS: {years}")
    print(f"{'='*80}\n")
    
    payload = {
        "user_query": query,
        "top_k": 10,  # Más documentos para ver
        "conversation_history": [],
        "years": years
    }
    
    try:
        resp = requests.post(f"{API_URL}/classify", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        # Mostrar candidatos
        print("TOP CANDIDATES:")
        for cand in data.get("top_candidates", [])[:5]:
            print(f"  {cand.get('code')} | {cand.get('confidence')*100:.1f}% | {cand.get('description', '')[:60]}")
        
        # Mostrar evidencia recuperada
        print("\n\nEVIDENCIA RECUPERADA (TOP 10):")
        evidence = data.get("evidence", [])
        for i, ev in enumerate(evidence[:10], 1):
            year = ev.get("year", "N/A")
            chapter = ev.get("chapter", "N/A")
            text = ev.get("text", "")[:70]
            source = ev.get("source", "N/A")
            print(f"\n{i}. Año: {year} | Cap: {chapter} | Source: {source}")
            print(f"   Text: {text}...")
        
        # Resumen por año
        print(f"\n\nRESUMEN BY YEAR:")
        years_count = {}
        for ev in evidence:
            year = ev.get("year", "N/A")
            years_count[year] = years_count.get(year, 0) + 1
        for year, count in sorted(years_count.items()):
            print(f"  {year}: {count} documentos")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

# Pruebas problemáticas
print("\n" + "="*80)
print("PROBLEMATIC QUERIES - DEBUGGING")
print("="*80)

# Caso 1: Neumáticos (devuelve 8517.13 en lugar de 4011)
debug_retrieval("neumaticos radiales para automovil 205/55R16", [2025, 2026])

# Caso 2: Laptops con especificaciones (falta 2025)
debug_retrieval("14 pulgadas, 16GB RAM, 512GB SSD, nuevo", [2025, 2026])

# Caso 3: Neumáticos seguimiento (devuelve 8703)
debug_retrieval("para vehículos de pasajeros, nuevos", [2025, 2026])

# Caso 4: Compare directamente búsquedas
debug_retrieval("neumaticos para automovil", [2025, 2026])
debug_retrieval("neumáticos", [2025, 2026])
debug_retrieval("4011", [2025, 2026])
