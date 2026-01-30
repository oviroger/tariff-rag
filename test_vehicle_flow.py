"""
Script de prueba para flujo conversacional de vehículos
Simula: vehículo → 50 personas, diesel, nuevo → verificar clasificación correcta
"""

import requests
import json
import time

API_URL = "http://localhost:8000/classify"

def test_vehicle_flow():
    print("=" * 80)
    print("TEST: Flujo conversacional de vehículo")
    print("=" * 80)
    
    # Turno 1: Consulta genérica "vehículo"
    print("\n[TURNO 1] Usuario: 'Hola, tengo un vehículo para importar de USA'")
    response1 = requests.post(API_URL, json={
        "user_query": "Hola, tengo un vehículo para importar de USA. ¿Cuál sería su clasificación arancelaria?",
        "years": [2025, 2026],
        "conversation_id": None
    })
    
    result1 = response1.json()
    conv_id = result1.get("conversation_id")
    candidates1 = result1.get("top_candidates", [])
    missing1 = result1.get("missing_fields", [])
    
    print(f"\n✓ Response Status: {response1.status_code}")
    print(f"✓ Conversation ID: {conv_id}")
    
    if candidates1:
        top = candidates1[0]
        print(f"\n🎯 Clasificación propuesta:")
        print(f"   Código: {top.get('code')}")
        print(f"   Descripción: {top.get('description')}")
        print(f"   Confianza: {top.get('confidence', 0):.0%}")
    else:
        print("\n❌ ERROR: No se propuso ningún código")
    
    if missing1:
        print(f"\n❓ Campos faltantes solicitados:")
        for field in missing1[:3]:
            print(f"   - {field}")
    
    time.sleep(1)
    
    # Turno 2: Proporcionar TODOS los detalles
    print("\n" + "=" * 80)
    print("[TURNO 2] Usuario: 'Es para 50 personas, motor a diesel, y es nuevo'")
    response2 = requests.post(API_URL, json={
        "user_query": "Es para 50 personas, motor a diesel, y es nuevo",
        "years": [2025, 2026],
        "conversation_id": conv_id
    })
    
    result2 = response2.json()
    candidates2 = result2.get("top_candidates", [])
    missing2 = result2.get("missing_fields", [])
    
    print(f"\n✓ Response Status: {response2.status_code}")
    
    if candidates2:
        top = candidates2[0]
        code = top.get('code', '')
        desc = top.get('description', '')
        conf = top.get('confidence', 0)
        
        print(f"\n🎯 Clasificación propuesta:")
        print(f"   Código: {code}")
        print(f"   Descripción: {desc}")
        print(f"   Confianza: {conf:.0%}")
        
        # Validar si el código es correcto
        print(f"\n📊 Validación:")
        if code.startswith("8702"):
            print(f"   ✅ CORRECTO: Código 8702 (autobús ≥10 plazas)")
        elif code.startswith("8703"):
            print(f"   ❌ ERROR: Código 8703 (automóvil <10 plazas) - DEBERÍA SER 8702")
        elif code.startswith("8711"):
            print(f"   ❌ ERROR CRÍTICO: Código 8711 (motocicleta) - DEBERÍA SER 8702")
        else:
            print(f"   ❌ ERROR: Código {code} - DEBERÍA SER 8702.xx (autobús diesel)")
        
        if "diesel" in desc.lower() or "diésel" in desc.lower():
            print(f"   ✅ Descripción menciona diesel")
        else:
            print(f"   ⚠️  Descripción NO menciona diesel: {desc}")
        
        if conf >= 0.75:
            print(f"   ✅ Confianza alta (≥75%)")
        else:
            print(f"   ⚠️  Confianza baja (<75%)")
    else:
        print("\n❌ ERROR: No se propuso ningún código")
    
    if missing2:
        print(f"\n❓ Campos faltantes (deberían ser pocos o ninguno):")
        for field in missing2:
            print(f"   - {field}")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN DE LA PRUEBA")
    print("=" * 80)
    
    if candidates2:
        top_code = candidates2[0].get('code', '')
        if top_code.startswith("8702"):
            print("✅ PRUEBA EXITOSA: Sistema clasificó correctamente como autobús (8702)")
        else:
            print(f"❌ PRUEBA FALLIDA: Sistema clasificó como {top_code} en lugar de 8702")
            print(f"   Esperado: 8702.xx (autobús diesel ≥10 plazas)")
            print(f"   Obtenido: {top_code}")
    else:
        print("❌ PRUEBA FALLIDA: No se generó clasificación")
    
    print("\nDetalles completos:")
    print(json.dumps(result2, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    try:
        test_vehicle_flow()
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se pudo conectar al API en http://localhost:8000")
        print("   Verifica que el contenedor esté ejecutándose: docker-compose ps")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
