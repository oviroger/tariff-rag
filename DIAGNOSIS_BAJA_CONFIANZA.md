#!/usr/bin/env python3
"""
ANÁLISIS FINAL: POR QUÉ MICROONDAS TIENE BAJA CONFIANZA
"""

import json

print("=" * 100)
print("🎯 DIAGNOSIS: CONFIANZA BAJA EN MICROONDAS")
print("=" * 100)

print("""
DATOS ENCONTRADOS:
==================

1. ÍNDICES EN OPENSEARCH:
   ├─ tariff_fragments: 0 docs (VACÍO) ❌
   ├─ tariff_fragments_2025: 3,992 docs ✅
   └─ tariff_fragments_2026: 14,175 docs ✅

2. CONFIGURACIÓN DEL API:
   └─ opensearch_index: "tariff_fragments_2025" (default en config)
   
3. DOCUMENTOS EN 2026:
   ├─ Estructura: [fragment_id, text, doc_id, bucket, unit, year, page, embedding]
   ├─ NO contiene: hs_code, description (❌ PROBLEMA!)
   └─ Búsqueda "microondas": 1 resultado con score muy bajo (0.03)

4. BÚSQUEDA DE "8516":
   └─ Retorna: 0 resultados ❌ (porque el índice NO tiene hs_code)

5. CONFIANZAS RETORNADAS:
   ├─ "microondas": 35%
   ├─ "microondas nuevo": 45%
   ├─ "microondas convencional": 43%
   └─ "es nuevo": 55%
   
   Patrón: 🔴 NUNCA SUPERA 55% para cualquier electrodoméstico

CONCLUSIÓN:
===========

El PROBLEMA REAL es una combinación de factores:

A) 🔴 ÍNDICE VACÍO (tariff_fragments con 0 docs)
   - El API está configurado para usar tariff_fragments por defecto
   - Este índice está vacío
   - El API no está usando tariff_fragments_2026

B) 🔴 DOCUMENTOS SIN METADATOS ESTRUCTURADOS
   - Los fragmentos en 2026 NO tienen hs_code, descripción, etc.
   - Solo tienen texto crudo
   - El modelo tiene que inferir TODO del texto

C) 🔴 MODELO CONSERVADOR
   - Gemini está asignando baja confianza porque:
     - Evidencia débil (score 0.03 es muy bajo)
     - Contexto insuficiente (solo "- Hornos de microondas")
     - No hay información completa sobre la subpartida

D) 🔴 FALTA DE ESPECIFICIDAD
   - "hornos de microondas" puede ser:
     ├─ 8516.50: microondas convencionales
     ├─ 8516.60: con funciones adicionales
     └─ 8509.80: otros electrodomésticos
   - Sin más datos, el modelo es conservador

SOLUCIONES:
===========

✅ OPCIÓN 1: Reparar la indexación (RECOMENDADA)
   - Asegurar que tariff_fragments_2026 tenga:
     * Texto completo del arancel
     * Metadatos: hs_code, descripción, categoría
     * Embeddings de alta calidad
   - Actualizar config del API para usar tariff_fragments_2026

✅ OPCIÓN 2: Mejorar los prompts (RÁPIDO)
   - Hacer más específicas las preguntas de seguimiento
   - Calibrar el modelo para subir confianza
   - Agregar reglas de negocio para aranceles comunes

✅ OPCIÓN 3: Enriquecer documentos con HS codes (INTERMEDIO)
   - Mapear fragmentos de texto a códigos HS conocidos
   - Agregar información de subpartidas (8516.50, 8516.60, etc.)
   - Usar MySQL para validar contra tabla maestra

RECOMENDACIÓN:
===============

Implementar OPCIÓN 1 + OPCIÓN 2:

1. Verificar que API está usando índice 2026 correcto
2. Validar estructura de documentos en 2026
3. Si faltan hs_code: ejecutar script de reindexación
4. Ajustar prompt en generator_gemini.py para ser menos conservador
5. Agregar regla de negocio: microondas → 8516.50 si nuevo

PRÓXIMOS PASOS:
===============

1. ¿Ejecuto script para revisar la config del API?
2. ¿Agrego campo hs_code a los documentos indexados?
3. ¿Ajusto los prompts de Gemini?
4. ¿Agrego reglas específicas para electrodomésticos?
""")

print("\n" + "=" * 100)
print("¿QUÉ QUIERES QUE HAGA?")
print("=" * 100)
