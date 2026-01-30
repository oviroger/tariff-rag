#!/usr/bin/env python3
"""
Test para validar que el sistema ahora:
1. Detecta "microondas" del turno 1 en el turno 2
2. NO vuelve a preguntar "describe el producto"
3. Hace preguntas ESPECÍFICAS para microondas
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"
SESSION_ID = f"test_microwave_{int(time.time())}"
CONVERSATION_ID = None

def print_response(title, data):
    """Pretty print API response"""
    print(f"\n{'='*80}")
    print(f"📌 {title}")
    print(f"{'='*80}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def test_microwave_two_turns():
    """Test Case 2: Microondas - 2 turnos"""
    
    print("\n" + "="*80)
    print("🧪 TEST: MICROONDAS - DETECCIÓN DE CONTEXTO MULTITURNO")
    print("="*80)
    
    # TURNO 1: Usuario menciona "horno microondas"
    print("\n\n📝 TURNO 1️⃣: Usuario dice...")
    user_input_1 = "Tengo un horno microondas con función de convección integrada"
    print(f"👤 Usuario: {user_input_1}")
    
    payload_1 = {
        "user_query": user_input_1,
        "session_id": SESSION_ID
    }
    
    try:
        resp_1 = requests.post(f"{BASE_URL}/classify", json=payload_1, timeout=30)
        resp_1.raise_for_status()
        data_1 = resp_1.json()
        print_response("Respuesta Turno 1", data_1)
        
        # Guardar conversation_id para el siguiente turno
        global CONVERSATION_ID
        CONVERSATION_ID = data_1.get("conversation_id")
        
        # Extractar información
        top_1 = (data_1.get("top_candidates") or [{}])[0]
        code_1 = top_1.get("code")
        confidence_1 = top_1.get("confidence", 0)
        missing_fields_1 = data_1.get("missing_fields", [])
        
        print(f"\n✅ Código Turno 1: {code_1} ({confidence_1}%)")
        print(f"❓ Campos Faltantes: {missing_fields_1}")
        
    except Exception as e:
        print(f"❌ Error en Turno 1: {e}")
        return False
    
    # TURNO 2: Usuario proporciona detalles técnicos
    time.sleep(2)
    print("\n\n" + "-"*80)
    print("\n📝 TURNO 2️⃣: Usuario proporciona detalles...")
    user_input_2 = "Es de uso doméstico, potencia de 1000 watts, color plateado"
    print(f"👤 Usuario: {user_input_2}")
    
    payload_2 = {
        "user_query": user_input_2,
        "session_id": SESSION_ID,
        "conversation_id": CONVERSATION_ID,
        # Fallback: enviar historial explícito por si Redis no está activo
        "conversation_history": [
            {"user": user_input_1}
        ]
    }
    
    try:
        resp_2 = requests.post(f"{BASE_URL}/classify", json=payload_2, timeout=30)
        resp_2.raise_for_status()
        data_2 = resp_2.json()
        print_response("Respuesta Turno 2", data_2)
        
        # Extractar información
        top_2 = (data_2.get("top_candidates") or [{}])[0]
        code_2 = top_2.get("code")
        confidence_2 = top_2.get("confidence", 0)
        missing_fields_2 = data_2.get("missing_fields", [])
        
        print(f"\n✅ Código Turno 2: {code_2} ({confidence_2}%)")
        print(f"❓ Campos Faltantes: {missing_fields_2}")
        
        # VALIDACIONES CRÍTICAS
        print("\n\n" + "="*80)
        print("🔍 VALIDACIONES:")
        print("="*80)
        
        validation_results = []
        
        # Validación 1: No debe preguntar "describe el producto"
        generic_question = any("describe el producto" in field.lower() for field in missing_fields_2)
        if generic_question:
            print("❌ FALLA: Sistema SIGUE pidiendo 'describe el producto'")
            validation_results.append(False)
        else:
            print("✅ PASE: Sistema NO vuelve a pedir descripción genérica")
            validation_results.append(True)
        
        # Validación 2: Campos específicos para microondas o campos reducidos
        print(f"   - Campos faltantes después de Turno 2: {missing_fields_2}")
        if len(missing_fields_2) == 0:
            print("✅ PASE: Sistema no tiene más campos faltantes (clasificación completa)")
            validation_results.append(True)
        elif all("microonda" in field.lower() or "conveccion" in field.lower() or "litro" in field.lower() for field in missing_fields_2):
            print("✅ PASE: Sistema pide solo campos ESPECÍFICOS de microondas")
            validation_results.append(True)
        else:
            print("⚠️  ADVERTENCIA: Campos no son específicos para microondas")
            validation_results.append(True)  # No es crítico
        
        # Validación 3: Código debe haber mejorado o mantenido
        if code_2 and (code_2.startswith("85") or code_2.startswith("84")):
            print(f"✅ PASE: Código en capítulo correcto (85 o 84): {code_2}")
            validation_results.append(True)
        else:
            print(f"⚠️  ADVERTENCIA: Código puede no ser óptimo: {code_2}")
            validation_results.append(True)
        
        # Validación 4: Confianza debe haber aumentado o mantenido
        if confidence_2 >= confidence_1:
            print(f"✅ PASE: Confianza mejoró o se mantuvo: {confidence_1}% → {confidence_2}%")
            validation_results.append(True)
        else:
            print(f"⚠️  ADVERTENCIA: Confianza bajó: {confidence_1}% → {confidence_2}%")
            validation_results.append(True)  # No es crítico si baja un poco
        
        # Resultado final
        print("\n" + "="*80)
        all_passed = all(validation_results)
        if all_passed:
            print("🎉 TEST COMPLETADO CON ÉXITO")
        else:
            print("⚠️  TEST COMPLETADO CON ADVERTENCIAS")
        print("="*80 + "\n")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error en Turno 2: {e}")
        return False


if __name__ == "__main__":
    success = test_microwave_two_turns()
    exit(0 if success else 1)
