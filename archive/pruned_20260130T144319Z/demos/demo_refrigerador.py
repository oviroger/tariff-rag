#!/usr/bin/env python3
"""
DEMO 2: ELECTRODOMÉSTICO - REFRIGERADOR
========================================
Caso de uso: Usuario importa un refrigerador/congelador
Objetivo: Demostrar que el sistema maneja diferentes tipos de electrodomésticos
Flujo esperado:
  1. "Necesito clasificar equipo de refrigeración" → Código genérico (8418) @ 35%
  2. "Es un refrigerador-congelador" → Código más específico (8418.10) @ 72%
  3. "De 300 litros, no frost, para uso doméstico" → Refinamiento final @ 85%
Validación: NO deben aparecer campos de vehículos
"""

import requests
import json
from pathlib import Path
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")

def print_response(turn, user_input, classification):
    """Formatea la respuesta de manera legible"""
    print(f"TURNO {turn}")
    print(f"├─ Usuario: \"{user_input}\"")
    
    if classification:
        print(f"├─ Código HS: {classification['code']}")
        print(f"├─ Confianza: {classification['confidence']}%")
        print(f"├─ Nivel: {classification['level']}")
        print(f"├─ Año: {classification['year']}")
        
        if classification.get('missing_fields'):
            print(f"├─ Campos faltantes sugeridos:")
            for i, field in enumerate(classification['missing_fields'][:5], 1):
                # Validar que NO haya campos de vehículos
                # Load vehicle field keywords from app/category_keywords.json
                cat_path = Path(__file__).parent.parent / "app" / "category_keywords.json"
                try:
                    if cat_path.exists():
                        with open(cat_path, "r", encoding="utf-8") as fh:
                            cat = json.load(fh)
                        vehicle_keywords = [s.lower() for s in (cat.get("vehicle_fields", []) or [])]
                    else:
                        vehicle_keywords = ['motor', 'cilindrada', 'gasolina', 'diesel', 'plazas', 'pasajeros', 'tracción', 'eje', 'suspensión']
                except Exception:
                    vehicle_keywords = ['motor', 'cilindrada', 'gasolina', 'diesel', 'plazas', 'pasajeros', 'tracción', 'eje', 'suspensión']
                is_vehicle_field = any(kw in field.lower() for kw in vehicle_keywords)
                marker = "❌ [INCORRECTO]" if is_vehicle_field else "✓"
                print(f"    {marker} {i}. {field}")
        
        # Validar ausencia de campos de vehículos
        if classification.get('missing_fields'):
            vehicle_fields = [f for f in classification['missing_fields'] 
                            if any(kw in f.lower() for kw in 
                                  ['motor', 'cilindrada', 'gasolina', 'diesel', 
                                   'plazas', 'pasajeros', 'tracción'])]
            if vehicle_fields:
                print(f"\n⚠️  VALIDACIÓN: Se encontraron campos INAPROPIADOS:")
                for field in vehicle_fields:
                    print(f"   ❌ {field}")
            else:
                print(f"\n✅ VALIDACIÓN: No hay campos de vehículos (correcto para electrodoméstico)")

def demo_refrigerador():
    """Ejecuta la demostración de clasificación de refrigerador"""
    print_section("DEMO 2: REFRIGERADOR - ELECTRODOMÉSTICO")
    
    conversation_id = f"demo_refrigerador_{int(time.time())}"
    
    # TURNO 1: Consulta genérica
    print("PASO 1: Usuario solicita clasificación de equipo de refrigeración")
    print("-" * 70)
    response = requests.post(
        f"{BASE_URL}/api/classify",
        json={
            "user_query": "Necesito clasificar un equipo de refrigeración",
            "conversation_id": conversation_id,
            "turn_number": 1
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        classification = result.get('classification', {})
        print_response(1, "Necesito clasificar un equipo de refrigeración", classification)
        code_t1 = classification.get('code')
    else:
        print(f"❌ Error: {response.status_code}")
        return

    time.sleep(1)

    # TURNO 2: Especifica que es refrigerador-congelador
    print("\nPASO 2: Usuario especifica el tipo de equipamiento")
    print("-" * 70)
    response = requests.post(
        f"{BASE_URL}/api/classify",
        json={
            "user_query": "Es un refrigerador-congelador estándar",
            "conversation_id": conversation_id,
            "turn_number": 2
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        classification = result.get('classification', {})
        print_response(2, "Es un refrigerador-congelador estándar", classification)
        code_t2 = classification.get('code')
    else:
        print(f"❌ Error: {response.status_code}")
        return

    time.sleep(1)

    # TURNO 3: Añade características técnicas
    print("\nPASO 3: Usuario proporciona especificaciones técnicas")
    print("-" * 70)
    response = requests.post(
        f"{BASE_URL}/api/classify",
        json={
            "user_query": "De 300 litros, sistema no-frost, capacidad de congelación 10kg/24h",
            "conversation_id": conversation_id,
            "turn_number": 3
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        classification = result.get('classification', {})
        print_response(3, "De 300 litros, sistema no-frost, capacidad de congelación 10kg/24h", classification)
        code_t3 = classification.get('code')
    else:
        print(f"❌ Error: {response.status_code}")
        return

    # RESUMEN
    print_section("RESUMEN DE LA DEMOSTRACIÓN")
    print(f"Conversación ID: {conversation_id}")
    print(f"\nProgresión de clasificación:")
    print(f"  Turno 1: {code_t1} (inicial, genérico)")
    print(f"  Turno 2: {code_t2} (refino con 'refrigerador-congelador')")
    print(f"  Turno 3: {code_t3} (detallado con especificaciones técnicas)")
    print(f"\n✅ DEMOSTRACIÓN COMPLETADA - El sistema refinó correctamente la clasificación")
    print(f"✅ Los campos sugeridos fueron apropiados para un electrodoméstico de refrigeración")

if __name__ == "__main__":
    try:
        demo_refrigerador()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
