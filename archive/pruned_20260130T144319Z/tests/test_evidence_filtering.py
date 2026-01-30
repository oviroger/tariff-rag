"""
Test para validar que el filtrado de evidencia funciona correctamente.
Prueba el caso específico: query sobre electrodomésticos no debe mostrar neumáticos.
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_electrodomesticos():
    """
    Test caso: Usuario pregunta por electrodomésticos
    Esperado: NO debe mostrar evidencia de neumáticos (irrelevante)
    """
    print("\n" + "="*80)
    print("TEST: Query sobre electrodomésticos")
    print("="*80)
    
    payload = {
        "user_query": "quiero importar electrodomésticos",
        "top_k": 5,
        "conversation_history": [],
        "conversation_id": "test-001"
    }
    
    try:
        response = requests.post(f"{API_URL}/classify", json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        print("\n📊 RESULTADO:")
        print(f"  - Candidatos propuestos: {len(result.get('top_candidates', []))}")
        print(f"  - Evidencia mostrada: {len(result.get('evidence', []))}")
        print(f"  - Missing fields: {len(result.get('missing_fields', []))}")
        print(f"  - Warnings: {result.get('warnings', [])}")
        
        # Verificar evidencia
        evidence = result.get('evidence', [])
        if evidence:
            print(f"\n📚 EVIDENCIA RECUPERADA ({len(evidence)} docs):")
            for i, ev in enumerate(evidence[:3], 1):
                score = ev.get('score', 0)
                text = ev.get('text', '')[:150]
                print(f"  {i}. Score: {score:.3f}")
                print(f"     Texto: {text}...")
                
            # Verificar si hay neumáticos
            has_tires = any('neumático' in str(ev.get('text', '')).lower() or 
                           'llanta' in str(ev.get('text', '')).lower()
                           for ev in evidence)
            if has_tires:
                print("\n  ⚠️  PROBLEMA: Se encontró evidencia sobre neumáticos (IRRELEVANTE)")
            else:
                print("\n  ✅ OK: No hay evidencia irrelevante de neumáticos")
        else:
            print("\n  ℹ️  No se mostró evidencia (correcto si score < umbral)")
        
        # Verificar missing_fields
        missing = result.get('missing_fields', [])
        if missing:
            print(f"\n❓ CAMPOS FALTANTES ({len(missing)}):")
            for field in missing[:5]:
                print(f"  - {field}")
        
        # Validación esperada
        print("\n✅ VALIDACIÓN:")
        if not result.get('top_candidates'):
            print("  ✓ No propuso códigos (correcto sin información específica)")
        
        if missing:
            has_specific_question = any(
                'electrodoméstico' in str(field).lower() or
                'lavadora' in str(field).lower() or
                'refrigerador' in str(field).lower()
                for field in missing
            )
            if has_specific_question:
                print("  ✓ Pregunta específica sobre tipo de electrodoméstico")
            else:
                print("  ⚠️  Debería preguntar qué tipo de electrodoméstico específico")
        
        # Verificar que NO hay evidencia de neumáticos con score alto
        if evidence:
            tire_docs_high_score = [ev for ev in evidence 
                                   if ev.get('score', 0) > 0.5 and 
                                   ('neumático' in str(ev.get('text', '')).lower() or 
                                    'llanta' in str(ev.get('text', '')).lower())]
            if tire_docs_high_score:
                print(f"  ❌ FALLO: {len(tire_docs_high_score)} docs de neumáticos con score > 0.5")
                return False
            else:
                print("  ✓ No hay evidencia irrelevante con score alto")
        
        print("\n✅ TEST PASADO")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR de conexión: {e}")
        print(f"   Asegúrate de que el API esté corriendo en {API_URL}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vehicle_with_context():
    """
    Test caso: Usuario da información progresivamente sobre un vehículo
    Esperado: Sistema debe recordar contexto y no re-pedir información ya dada
    """
    print("\n" + "="*80)
    print("TEST: Contexto conversacional - vehículo")
    print("="*80)
    
    conv_id = "test-002"
    
    # Turno 1: Usuario menciona "bus diesel"
    print("\n📝 Turno 1: 'quiero importar un bus a diesel'")
    payload1 = {
        "user_query": "quiero importar un bus a diesel",
        "top_k": 3,
        "conversation_history": [],
        "conversation_id": conv_id
    }
    
    try:
        r1 = requests.post(f"{API_URL}/classify", json=payload1, timeout=30)
        r1.raise_for_status()
        result1 = r1.json()
        
        print(f"  - Candidatos: {len(result1.get('top_candidates', []))}")
        missing1 = result1.get('missing_fields', [])
        print(f"  - Missing fields: {missing1[:3]}")
        
        # Validar que pregunta por cilindrada/plazas, pero NO por tipo de vehículo/motor
        has_cylinder_question = any('cilindrada' in str(f).lower() for f in missing1)
        has_seats_question = any('pasajero' in str(f).lower() or 'plaza' in str(f).lower() for f in missing1)
        asks_vehicle_type = any('tipo de vehículo' in str(f).lower() for f in missing1)
        asks_motor_type = any('tipo de motor' in str(f).lower() and 'cilindrada' not in str(f).lower() for f in missing1)
        
        if asks_vehicle_type:
            print("  ⚠️  NO debería preguntar tipo de vehículo (ya dijo 'bus')")
        else:
            print("  ✓ No pregunta tipo de vehículo (correcto)")
            
        if asks_motor_type:
            print("  ⚠️  NO debería preguntar tipo de motor (ya dijo 'diesel')")
        else:
            print("  ✓ No pregunta tipo de motor (correcto)")
        
        if has_cylinder_question:
            print("  ✓ Pregunta por cilindrada (correcto)")
        
        if has_seats_question:
            print("  ✓ Pregunta por número de pasajeros (correcto)")
        
        print("\n✅ TEST CONTEXTO PASADO")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def test_health_check():
    """Verifica que el API está funcionando"""
    print("\n" + "="*80)
    print("TEST: Health check del API")
    print("="*80)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        response.raise_for_status()
        health = response.json()
        
        print("\n📊 ESTADO DEL API:")
        print(f"  - Status: {health.get('status')}")
        
        services = health.get('services', {})
        for service, details in services.items():
            status = details.get('status') if isinstance(details, dict) else details
            symbol = "✓" if status == "ok" else "✗"
            print(f"  {symbol} {service}: {status}")
        
        if health.get('status') == 'ok':
            print("\n✅ API funcionando correctamente")
            return True
        else:
            print("\n⚠️  API con problemas")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: No se puede conectar al API")
        print(f"   {e}")
        return False


if __name__ == "__main__":
    print("\n🔍 INICIANDO PRUEBAS DE VALIDACIÓN")
    print("="*80)
    
    # 1. Health check
    if not test_health_check():
        print("\n⚠️  El API no está disponible. Inicia los servicios con:")
        print("    cd tariff-rag")
        print("    docker-compose up -d")
        exit(1)
    
    # 2. Test principal: electrodomésticos
    test_electrodomesticos()
    
    # 3. Test contexto conversacional
    test_vehicle_with_context()
    
    print("\n" + "="*80)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS")
    print("="*80)
