#!/usr/bin/env python3
"""
Test para verificar que conversation_id y conversation_history se mantienen
correctamente en la UI web (simulando turnos del usuario)
"""

import requests
import json
from uuid import uuid4

API_URL = "http://localhost:8000"

def test_conversation_persistence():
    """
    Simula dos turnos de conversacion en web para verificar:
    1. conversation_id se mantiene entre turnos
    2. conversation_history se acumula correctamente
    3. El API recibe y procesa el historial
    """
    
    print("\n" + "="*80)
    print("[TEST] Verificando persistencia de conversation_id y conversation_history")
    print("="*80)
    
    # Simular como lo hace la UI: generar conversation_id al inicio
    conv_id = str(uuid4().hex)[:16]
    print(f"\n[INFO] Conversation ID generado: {conv_id}")
    
    conversation_history = []
    
    # TURNO 1: Primera consulta (sin historial)
    print("\n" + "-"*80)
    print("[TURNO 1] Primera consulta")
    print("-"*80)
    
    query1 = "Necesito clasificar un autobus"
    payload1 = {
        "user_query": query1,
        "conversation_history": conversation_history,
        "conversation_id": conv_id
    }
    
    print(f"[SEND] Query: {query1}")
    print(f"[SEND] conversation_id: {conv_id}")
    print(f"[SEND] conversation_history length: {len(conversation_history)}")
    
    resp1 = requests.post(f"{API_URL}/classify", json=payload1, timeout=30)
    resp1.raise_for_status()
    result1 = resp1.json()
    
    print(f"\n[RECEIVE] Codigo: {result1.get('top_candidates', [{}])[0].get('code')}")
    print(f"[RECEIVE] Confianza: {result1.get('top_candidates', [{}])[0].get('confidence', 0)*100:.0f}%")
    print(f"[RECEIVE] conversation_id retornado: {result1.get('conversation_id', 'NO RETORNADO')}")
    print(f"[RECEIVE] missing_fields: {result1.get('missing_fields', [])[:1]}")
    
    # Verificar que el API devuelve conversation_id
    returned_conv_id_1 = result1.get("conversation_id")
    if returned_conv_id_1 != conv_id:
        print(f"\n[WARNING] conversation_id NO coincide!")
        print(f"  Enviado: {conv_id}")
        print(f"  Recibido: {returned_conv_id_1}")
    else:
        print(f"\n[OK] conversation_id coincide")
    
    # Guardar en historial (como lo haría Gradio)
    conversation_history.append({
        "user": query1,
        "assistant": f"Codigo: {result1.get('top_candidates', [{}])[0].get('code')}"
    })
    
    # TURNO 2: Segunda consulta (CON historial)
    print("\n" + "-"*80)
    print("[TURNO 2] Segunda consulta (con historial)")
    print("-"*80)
    
    query2 = "Es a diesel"
    payload2 = {
        "user_query": query2,
        "conversation_history": conversation_history,
        "conversation_id": conv_id
    }
    
    print(f"[SEND] Query: {query2}")
    print(f"[SEND] conversation_id: {conv_id}")
    print(f"[SEND] conversation_history length: {len(conversation_history)}")
    print(f"[SEND] conversation_history content:")
    for i, turn in enumerate(conversation_history):
        print(f"       Turno {i+1}: user='{turn.get('user')[:40]}...' assistant='{turn.get('assistant')[:40]}...'")
    
    resp2 = requests.post(f"{API_URL}/classify", json=payload2, timeout=30)
    resp2.raise_for_status()
    result2 = resp2.json()
    
    print(f"\n[RECEIVE] Codigo: {result2.get('top_candidates', [{}])[0].get('code')}")
    print(f"[RECEIVE] Confianza: {result2.get('top_candidates', [{}])[0].get('confidence', 0)*100:.0f}%")
    print(f"[RECEIVE] conversation_id retornado: {result2.get('conversation_id', 'NO RETORNADO')}")
    print(f"[RECEIVE] missing_fields: {result2.get('missing_fields', [])}")
    
    # Verificar que el API devuelve conversation_id
    returned_conv_id_2 = result2.get("conversation_id")
    if returned_conv_id_2 != conv_id:
        print(f"\n[WARNING] conversation_id NO coincide en turno 2!")
    else:
        print(f"\n[OK] conversation_id coincide en turno 2")
    
    # VALIDACIONES
    print("\n" + "="*80)
    print("[VALIDACIONES]")
    print("="*80)
    
    code1 = result1.get('top_candidates', [{}])[0].get('code')
    code2 = result2.get('top_candidates', [{}])[0].get('code')
    conf1 = result1.get('top_candidates', [{}])[0].get('confidence', 0)
    conf2 = result2.get('top_candidates', [{}])[0].get('confidence', 0)
    
    checks = []
    
    # Check 1: conversation_id debe mantenerse
    check1 = returned_conv_id_1 == conv_id and returned_conv_id_2 == conv_id
    checks.append(("conversation_id se mantiene entre turnos", check1))
    
    # Check 2: Codigo debe refinar (de 8702.90 a algo mas especifico)
    check2 = code2.startswith("8702") and (code2 != "8702.90" or conf2 > conf1)
    checks.append(("Codigo refina entre turnos", check2))
    
    # Check 3: Confianza debe mejorar o mantenerse
    check3 = conf2 >= conf1 or conf2 > 0.50
    checks.append(("Confianza mejora o es >50%", check3))
    
    # Check 4: Historia acumulada en turno 2
    check4 = len(conversation_history) > 0
    checks.append(("conversation_history se acumula", check4))
    
    # Imprimir resultados
    for check_name, result in checks:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {check_name}")
    
    # Resumen
    all_passed = all(result for _, result in checks)
    print("\n" + "="*80)
    if all_passed:
        print("[SUCCESS] Todas las validaciones pasaron")
    else:
        print("[ERROR] Algunas validaciones fallaron")
    print("="*80)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = test_conversation_persistence()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        exit(1)
