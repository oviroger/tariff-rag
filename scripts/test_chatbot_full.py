#!/usr/bin/env python3
"""
Prueba completa del chatbot con consulta de 'microondas'
para verificar que el fix funciona end-to-end
"""
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"

def test_chatbot_full():
    print("="*70)
    print("PRUEBA COMPLETA DEL CHATBOT")
    print("="*70)
    print()
    
    # Test 1: Health check
    print("[TEST 1] Health Check")
    response = requests.get(f"{API_URL}/health")
    if response.status_code == 200:
        health = response.json()
        print(f"✅ API Status: {health['status']}")
        print(f"✅ OpenSearch: {health['services']['opensearch']['status']}")
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return
    print()
    
    # Test 2: Clasificar producto primero
    print("[TEST 2] Clasificación: 'microondas'")
    print("-" * 70)
    
    classify_payload = {
        "user_query": "microondas"
    }
    
    response = requests.post(
        f"{API_URL}/classify",
        json=classify_payload,
        headers={"Content-Type": "application/json"}
    )
    
    conversation_id = None
    
    if response.status_code == 200:
        classify_result = response.json()
        conversation_id = classify_result.get('conversation_id')
        
        print(f"✅ Clasificación exitosa")
        print(f"  - Conversation ID: {conversation_id}")
        print(f"  - Categoría: {classify_result.get('category', 'N/A')}")
        print(f"  - HS Code: {classify_result.get('hs_code', 'N/A')}")
        print(f"  - Confianza: {classify_result.get('confidence', 'N/A')}")
        print()
    else:
        print(f"❌ Clasificación falló: {response.status_code}")
        print(f"Response: {response.text}")
        return
    
    # Test 3: Query con contexto de clasificación
    print("[TEST 3] Consulta: '¿Cuál es el arancel para este producto?'")
    print("-" * 70)
    
    payload = {
        "question": "¿Cuál es el arancel para este producto?",
        "conversation_id": conversation_id
    }
    
    response = requests.post(
        f"{API_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"✅ Status Code: {response.status_code}")
        print()
        print(f"📝 RESPUESTA DEL CHATBOT:")
        print(f"{result.get('response', 'N/A')}")
        print()
        
        # Metadata
        metadata = result.get('metadata', {})
        print(f"📊 METADATA:")
        print(f"  - Confianza: {metadata.get('confidence', 'N/A')}")
        print(f"  - Categoria: {metadata.get('category', 'N/A')}")
        print(f"  - HS Code: {metadata.get('hs_code', 'N/A')}")
        print(f"  - Año tarifa: {metadata.get('tariff_year', 'N/A')}")
        print()
        
        # Sources
        sources = result.get('sources', [])
        print(f"📚 FUENTES UTILIZADAS: {len(sources)}")
        for i, src in enumerate(sources[:3], 1):
            print(f"  {i}. Score: {src.get('score', 'N/A'):.4f}")
            print(f"     Unit: {src.get('unit', 'N/A')}")
            print(f"     Year: {src.get('year', 'N/A')}")
            if 'hs_code' in src:
                print(f"     HS Code: {src.get('hs_code')}")
            print(f"     Preview: {src.get('text', '')[:80]}...")
            print()
        
        # Verificaciones
        print("="*70)
        print("VERIFICACIONES:")
        print("="*70)
        
        checks = []
        
        # Check 1: Respuesta no vacía
        if result.get('response'):
            print("✅ Respuesta generada correctamente")
            checks.append(True)
        else:
            print("❌ Respuesta vacía")
            checks.append(False)
        
        # Check 2: Fuentes con datos de tablas
        has_table = any(s.get('unit') == 'table' for s in sources)
        if has_table:
            print("✅ Fuentes incluyen datos de tablas (fix aplicado)")
            checks.append(True)
        else:
            print("⚠️  No se encontraron fuentes de tablas")
            checks.append(False)
        
        # Check 3: Confianza > 0
        confidence = metadata.get('confidence', 0)
        if confidence and confidence > 0:
            print(f"✅ Confianza > 0: {confidence}")
            checks.append(True)
        else:
            print(f"❌ Confianza baja o 0: {confidence}")
            checks.append(False)
        
        # Check 4: HS Code detectado
        if metadata.get('hs_code'):
            print(f"✅ HS Code detectado: {metadata.get('hs_code')}")
            checks.append(True)
        else:
            print("⚠️  HS Code no detectado en metadata")
            checks.append(False)
        
        # Check 5: Año correcto (debe usar 2025 o 2026)
        year = metadata.get('tariff_year')
        if year and year in ['2025', '2026']:
            print(f"✅ Año de tarifa válido: {year}")
            checks.append(True)
        else:
            print(f"⚠️  Año de tarifa: {year}")
            checks.append(False)
        
        print()
        print("="*70)
        passed = sum(checks)
        total = len(checks)
        print(f"RESULTADO: {passed}/{total} verificaciones pasadas")
        
        if passed == total:
            print("✅ ÉXITO COMPLETO - El chatbot funciona correctamente!")
        elif passed >= 3:
            print("✅ ÉXITO PARCIAL - Funcionalidad principal OK")
        else:
            print("❌ FALLO - Revisar configuración")
        print("="*70)
        
    else:
        print(f"❌ Query failed: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    try:
        test_chatbot_full()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
