#!/usr/bin/env python3
"""
Test completo: Simulación de interacción usuario-sistema hasta código arancelario completo.
Ejemplo: Vehículo automóvil → clasificación de HS6 hasta HS10
"""

import requests
import json
import time

API_URL = "http://localhost:8000/classify"
SESSION_ID = f"test_complete_flow_{int(time.time())}"

def print_separator(title=""):
    print("\n" + "=" * 80)
    if title:
        print(f"📌 {title}")
    print("=" * 80)

def make_request(user_query, conversation_history, turn_number):
    """Realiza petición al API y muestra resultados."""
    print(f"\n{'🔹' * 40}")
    print(f"TURNO {turn_number}: Usuario dice...")
    print(f"{'🔹' * 40}")
    print(f"👤 Usuario: {user_query}")
    
    payload = {
        "user_query": user_query,
        "conversation_history": conversation_history,
        "conversation_id": SESSION_ID,
        "top_k": 5,
        "years": [2025, 2026]
    }
    
    response = requests.post(API_URL, json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    
    print_separator("RESPUESTA DEL SISTEMA")
    
    # Mostrar candidato principal
    if result.get("top_candidates"):
        top = result["top_candidates"][0]
        print(f"\n🎯 CÓDIGO PROPUESTO: {top['code']} ({top['level']})")
        print(f"📊 CONFIANZA: {top['confidence']:.0%}")
        print(f"📝 DESCRIPCIÓN: {top['description']}")
        if top.get('years'):
            print(f"📅 VIGENTE EN: {', '.join(map(str, top['years']))}")
    
    # Mostrar preguntas pendientes
    missing = result.get("missing_fields", [])
    if missing:
        print(f"\n❓ PREGUNTAS PENDIENTES ({len(missing)}):")
        for i, field in enumerate(missing[:5], 1):
            print(f"   {i}. {field}")
    else:
        print(f"\n✅ CLASIFICACIÓN COMPLETA - No se requiere más información")
    
    # Mostrar inclusiones/exclusiones si hay
    if result.get("inclusions"):
        print(f"\n✓ INCLUYE: {', '.join(result['inclusions'][:3])}")
    if result.get("exclusions"):
        print(f"\n✗ EXCLUYE: {', '.join(result['exclusions'][:3])}")
    
    return result

def main():
    print_separator("🚗 SIMULACIÓN COMPLETA: CLASIFICACIÓN DE VEHÍCULO AUTOMÓVIL")
    print("\nObjetivo: Clasificar un vehículo desde consulta inicial hasta código HS10 completo")
    print(f"Session ID: {SESSION_ID}")
    
    conversation_history = []
    
    # ============================================================
    # TURNO 1: Consulta inicial muy genérica
    # ============================================================
    query1 = "Necesito clasificar un vehículo"
    result1 = make_request(query1, conversation_history, 1)
    
    # Actualizar historial
    if result1.get("top_candidates"):
        top_code = result1["top_candidates"][0]["code"]
        top_desc = result1["top_candidates"][0]["description"]
        assistant_msg = f"Código: {top_code} ({top_desc})"
        missing = result1.get("missing_fields", [])
        if missing:
            assistant_msg += f" | Preguntó: {', '.join(missing[:2])}"
        conversation_history.append({
            "user": query1,
            "assistant": assistant_msg
        })
    
    time.sleep(2)
    
    # ============================================================
    # TURNO 2: Responder tipo de vehículo y combustible
    # ============================================================
    query2 = "Es un automóvil de turismo con motor de gasolina"
    result2 = make_request(query2, conversation_history, 2)
    
    # Actualizar historial
    if result2.get("top_candidates"):
        top_code = result2["top_candidates"][0]["code"]
        top_desc = result2["top_candidates"][0]["description"]
        assistant_msg = f"Código: {top_code} ({top_desc})"
        missing = result2.get("missing_fields", [])
        if missing:
            assistant_msg += f" | Preguntó: {', '.join(missing[:2])}"
        conversation_history.append({
            "user": query2,
            "assistant": assistant_msg
        })
    
    time.sleep(2)
    
    # ============================================================
    # TURNO 3: Responder cilindrada (campo crítico para HS8)
    # ============================================================
    query3 = "Cilindrada de 1800 cc"
    result3 = make_request(query3, conversation_history, 3)
    
    # Actualizar historial
    if result3.get("top_candidates"):
        top_code = result3["top_candidates"][0]["code"]
        top_desc = result3["top_candidates"][0]["description"]
        assistant_msg = f"Código: {top_code} ({top_desc})"
        missing = result3.get("missing_fields", [])
        if missing:
            assistant_msg += f" | Preguntó: {', '.join(missing[:2])}"
        conversation_history.append({
            "user": query3,
            "assistant": assistant_msg
        })
    
    time.sleep(2)
    
    # ============================================================
    # TURNO 4: Responder condición (nuevo/usado) para HS10
    # ============================================================
    query4 = "Es un vehículo nuevo"
    result4 = make_request(query4, conversation_history, 4)
    
    # Actualizar historial
    if result4.get("top_candidates"):
        top_code = result4["top_candidates"][0]["code"]
        top_desc = result4["top_candidates"][0]["description"]
        assistant_msg = f"Código: {top_code} ({top_desc})"
        missing = result4.get("missing_fields", [])
        if missing:
            assistant_msg += f" | Preguntó: {', '.join(missing[:2])}"
        conversation_history.append({
            "user": query4,
            "assistant": assistant_msg
        })
    
    time.sleep(1)
    
    # ============================================================
    # RESUMEN FINAL
    # ============================================================
    print_separator("📊 RESUMEN DE LA CONVERSACIÓN")
    
    print("\n🔄 PROGRESIÓN DE LA CLASIFICACIÓN:")
    print("-" * 80)
    
    results = [result1, result2, result3, result4]
    for i, result in enumerate(results, 1):
        if result.get("top_candidates"):
            top = result["top_candidates"][0]
            code = top['code']
            confidence = top['confidence']
            level = top['level']
            missing_count = len(result.get("missing_fields", []))
            
            # Calcular longitud del código
            code_digits = len(code.replace(".", ""))
            
            print(f"Turno {i}: {code:12} ({level:11}) | Confianza: {confidence:>5.0%} | {missing_count} campos pendientes")
    
    print("-" * 80)
    
    # Análisis de evolución
    if len(results) >= 4:
        initial_code = results[0]["top_candidates"][0]["code"] if results[0].get("top_candidates") else "N/A"
        final_code = results[3]["top_candidates"][0]["code"] if results[3].get("top_candidates") else "N/A"
        
        initial_conf = results[0]["top_candidates"][0]["confidence"] if results[0].get("top_candidates") else 0
        final_conf = results[3]["top_candidates"][0]["confidence"] if results[3].get("top_candidates") else 0
        
        initial_level = results[0]["top_candidates"][0]["level"] if results[0].get("top_candidates") else "N/A"
        final_level = results[3]["top_candidates"][0]["level"] if results[3].get("top_candidates") else "N/A"
        
        print(f"\n📈 EVOLUCIÓN:")
        print(f"   Código:     {initial_code} → {final_code}")
        print(f"   Nivel:      {initial_level} → {final_level}")
        print(f"   Confianza:  {initial_conf:.0%} → {final_conf:.0%}")
        
        # Evaluar si se alcanzó clasificación completa
        final_missing = len(results[3].get("missing_fields", []))
        if final_missing == 0:
            print(f"\n✅ CLASIFICACIÓN COMPLETA ALCANZADA")
            print(f"   🎉 Código arancelario final: {final_code} ({final_level})")
        else:
            print(f"\n⚠️  CLASIFICACIÓN PARCIAL")
            print(f"   Aún quedan {final_missing} campos por especificar para refinamiento total")
    
    print_separator("✅ SIMULACIÓN COMPLETADA")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se pudo conectar al API")
        print("   Asegúrate de que el servicio esté corriendo en http://localhost:8000")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
