#!/usr/bin/env python3
"""
Test que simula EXACTAMENTE como Gradio ChatInterface llama a chat_minimal_validation
"""

import sys
sys.path.insert(0, '/tariff-rag')

from ui.gradio_app import chat_minimal_validation

def test_gradio_simulation():
    """Simula dos turnos como lo haría Gradio ChatInterface."""
    
    print("\n" + "="*80)
    print("[TEST] Simulando ChatInterface de Gradio")
    print("="*80)
    
    conv_id = ""
    years = ["2025", "2026"]
    
    # TURNO 1: Usuario escribe "Necesito clasificar un autobus"
    print("\n[TURNO 1] Usuario: 'Necesito clasificar un autobus'")
    print("-" * 80)
    
    msg1 = "Necesito clasificar un autobus"
    history1 = []  # Gradio comienza con historial vacío
    
    print(f"[PARAMS] message='{msg1}'")
    print(f"[PARAMS] history={history1}")
    print(f"[PARAMS] conv_id='{conv_id}'")
    print(f"[PARAMS] years={years}")
    
    response1, conv_id = chat_minimal_validation(msg1, history1, conv_id, years)
    
    print(f"\n[RESPONSE] chat_minimal_validation retorno:")
    print(f"Response: {response1[:150]}...")
    print(f"conv_id: {conv_id}")
    
    # Gradio AUTOMÁTICAMENTE agrega a history
    history1 = [(msg1, response1)]
    
    print(f"\n[AFTER_TURN1] history se convierte en: {len(history1)} turnos")
    
    # TURNO 2: Usuario escribe "Es a diesel"
    print("\n" + "="*80)
    print("[TURNO 2] Usuario: 'Es a diesel'")
    print("-" * 80)
    
    msg2 = "Es a diesel"
    # IMPORTANTE: history ahora incluye el turno anterior
    history2 = history1.copy()  # Gradio pasa el historial acumulado
    
    print(f"[PARAMS] message='{msg2}'")
    print(f"[PARAMS] history={history2}")
    print(f"[PARAMS] conv_id='{conv_id}'")
    print(f"[PARAMS] years={years}")
    
    print(f"\n[DEBUG] history content:")
    for i, (user, asst) in enumerate(history2):
        print(f"  Turno {i+1}: user='{user}' -> asst='{asst[:100]}...'")
    
    response2, conv_id_out = chat_minimal_validation(msg2, history2, conv_id, years)
    
    print(f"\n[RESPONSE] chat_minimal_validation retorno:")
    print(f"Response: {response2[:150]}...")
    print(f"conv_id: {conv_id_out}")
    
    # Verificar results
    print("\n" + "="*80)
    print("[VALIDATION]")
    print("="*80)
    
    if "8702" in response1:
        print("[OK] Turno 1: Detectó 8702 (autobus)")
    else:
        print("[FAIL] Turno 1: NO detectó 8702")
    
    if "8702.20" in response2 or "95%" in response2:
        print("[OK] Turno 2: Refinó a 8702.20 o mostró 95%")
    else:
        print("[UNCLEAR] Turno 2: NO refinó correctamente")
        print(f"Response: {response2}")
    
    if "motor" in response2.lower():
        print("[BUG] Turno 2: AUN pregunta por motor (debería NO)")
    else:
        print("[OK] Turno 2: NO pregunta motor (correcto)")

if __name__ == "__main__":
    import os
    os.chdir("/tariff-rag")
    
    try:
        test_gradio_simulation()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
