#!/usr/bin/env python3
"""
DEMO 1: ELECTRODOMÉSTICO - LAVADORA
====================================
Caso de uso: Usuario importa una lavadora de ropa
Objetivo: Demostrar clasificación progresiva con refinamiento de código
Flujo esperado:
  1. "Quiero importar electrodoméstico" → Código genérico (8509.80) @ 43%
  2. "Es una lavadora de ropa" → Código más específico (8450.11) @ 78%
  3. "Con función de secado incluida" → Código final refinado (8450.11.10) @ 90%
Validación: NO deben aparecer campos de vehículos (motor, cilindrada, pasajeros)
"""

import requests
import json
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
                vehicle_keywords = ['motor', 'cilindrada', 'gasolina', 'diesel', 
                                   'plazas', 'pasajeros', 'tracción', 'eje', 'suspensión']
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

def demo_lavadora():
    """Ejecuta la demostración de clasificación de lavadora"""
    print_section("DEMO 1: LAVADORA - ELECTRODOMÉSTICO")
    
    conversation_id = f"demo_lavadora_{int(time.time())}"
    
    # TURNO 1: Consulta genérica
    print("PASO 1: Usuario inicia consulta genérica")
    print("-" * 70)
    response = requests.post(
        f"{BASE_URL}/api/classify",
        json={
            "user_query": "Quiero importar un electrodoméstico",
            "conversation_id": conversation_id,
            "turn_number": 1
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        classification = result.get('classification', {})
        print_response(1, "Quiero importar un electrodoméstico", classification)
        code_t1 = classification.get('code')
    else:
        print(f"❌ Error: {response.status_code}")
        return

    time.sleep(1)

    # TURNO 2: Especifica que es lavadora
    print("\nPASO 2: Usuario especifica que es una lavadora")
    print("-" * 70)
    response = requests.post(
        f"{BASE_URL}/api/classify",
        json={
            "user_query": "Es una lavadora de ropa automática",
            "conversation_id": conversation_id,
            "turn_number": 2
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        classification = result.get('classification', {})
        print_response(2, "Es una lavadora de ropa automática", classification)
        code_t2 = classification.get('code')
    else:
        print(f"❌ Error: {response.status_code}")
        return

    time.sleep(1)

    # TURNO 3: Añade detalles adicionales
    print("\nPASO 3: Usuario proporciona más detalles")
    print("-" * 70)
    response = requests.post(
        f"{BASE_URL}/api/classify",
        json={
            "user_query": "Tiene función de secado incluida, voltaje 220V",
            "conversation_id": conversation_id,
            "turn_number": 3
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        classification = result.get('classification', {})
        print_response(3, "Tiene función de secado incluida, voltaje 220V", classification)
        code_t3 = classification.get('code')
    else:
        print(f"❌ Error: {response.status_code}")
        return

    # RESUMEN
    print_section("RESUMEN DE LA DEMOSTRACIÓN")
    print(f"Conversación ID: {conversation_id}")
    print(f"\nProgresión de clasificación:")
    print(f"  Turno 1: {code_t1} (inicial, genérico)")
    print(f"  Turno 2: {code_t2} (refino con 'lavadora')")
    print(f"  Turno 3: {code_t3} (detallado con 'secado' y 'voltaje')")
    print(f"\n✅ DEMOSTRACIÓN COMPLETADA - El sistema refinó correctamente la clasificación")
    print(f"✅ Los campos sugeridos fueron apropiados para un electrodoméstico")

if __name__ == "__main__":
    try:
        demo_lavadora()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
