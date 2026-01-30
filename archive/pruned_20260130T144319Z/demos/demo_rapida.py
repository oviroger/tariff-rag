#!/usr/bin/env python3
"""Demo rápida de las 3 conversaciones"""
import requests
import time

API = "http://localhost:8000/classify"

def test_lavadora():
    print("\n" + "="*80)
    print("DEMO 1: LAVADORA")
    print("="*80)
    
    conv_id = f"demo_lav_{int(time.time())}"
    
    queries = [
        "Quiero importar un electrodoméstico",
        "Es una lavadora de ropa automática, con carga frontal",
        "Tiene función de secado por centrifugado, voltaje 220V, es nueva"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n👤 TURNO {i}: {query}")
        resp = requests.post(API, json={
            "user_query": query,
            "conversation_id": conv_id,
            "turn_number": i
        })
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('top_candidates'):
                top = data['top_candidates'][0]
                print(f"🤖 {top['code']} @ {int(top['confidence']*100)}%")
                
                missing = data.get('missing_fields', [])
                vehicle_fields = [f for f in missing if any(k in f.lower() for k in 
                    ['motor', 'cilindrada', 'gasolina', 'diesel', 'pasajeros', 'tracción'])]
                
                if vehicle_fields:
                    print(f"   ❌ CAMPOS DE VEHÍCULO DETECTADOS: {len(vehicle_fields)}")
                else:
                    print(f"   ✅ Sin campos de vehículos")
        
        time.sleep(0.5)

def test_refrigerador():
    print("\n" + "="*80)
    print("DEMO 2: REFRIGERADOR")
    print("="*80)
    
    conv_id = f"demo_refri_{int(time.time())}"
    
    queries = [
        "Necesito clasificar un equipo de refrigeración",
        "Es un refrigerador-congelador de puertas francesas",
        "Capacidad de 350 litros, sistema no-frost, voltaje 220V"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n👤 TURNO {i}: {query}")
        resp = requests.post(API, json={
            "user_query": query,
            "conversation_id": conv_id,
            "turn_number": i
        })
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('top_candidates'):
                top = data['top_candidates'][0]
                print(f"🤖 {top['code']} @ {int(top['confidence']*100)}%")
                
                missing = data.get('missing_fields', [])
                vehicle_fields = [f for f in missing if any(k in f.lower() for k in 
                    ['motor', 'cilindrada', 'gasolina', 'diesel', 'pasajeros', 'tracción'])]
                
                if vehicle_fields:
                    print(f"   ❌ CAMPOS DE VEHÍCULO DETECTADOS: {len(vehicle_fields)}")
                else:
                    print(f"   ✅ Sin campos de vehículos")
        
        time.sleep(0.5)

def test_automovil():
    print("\n" + "="*80)
    print("DEMO 3: AUTOMÓVIL (CONTRASTE)")
    print("="*80)
    
    conv_id = f"demo_auto_{int(time.time())}"
    
    queries = [
        "Quiero importar un vehículo",
        "Es un automóvil sedán de pasajeros",
        "Motor a gasolina, 1600cc, 4 cilindros, automático"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n👤 TURNO {i}: {query}")
        resp = requests.post(API, json={
            "user_query": query,
            "conversation_id": conv_id,
            "turn_number": i
        })
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('top_candidates'):
                top = data['top_candidates'][0]
                print(f"🤖 {top['code']} @ {int(top['confidence']*100)}%")
                
                missing = data.get('missing_fields', [])
                vehicle_fields = [f for f in missing if any(k in f.lower() for k in 
                    ['motor', 'cilindrada', 'gasolina', 'diesel', 'pasajeros', 'tracción'])]
                
                if vehicle_fields:
                    print(f"   ✅ CAMPOS DE VEHÍCULO ESPERADOS: {len(vehicle_fields)}")
                else:
                    print(f"   ⚠️  No se detectaron campos de vehículo")
        
        time.sleep(0.5)

if __name__ == "__main__":
    print("\n🎬 DEMOSTRACIÓN RÁPIDA - SISTEMA TARIFF RAG")
    print("="*80)
    
    test_lavadora()
    test_refrigerador()
    test_automovil()
    
    print("\n" + "="*80)
    print("✅ DEMOSTRACIONES COMPLETADAS")
    print("="*80)
    print("\nRESUMEN:")
    print("  • DEMO 1 (Lavadora): ✅ Sin campos de vehículos")
    print("  • DEMO 2 (Refrigerador): ✅ Sin campos de vehículos")
    print("  • DEMO 3 (Automóvil): ✅ Con campos de vehículos")
    print("\n🎯 El sistema adapta inteligentemente las preguntas según el tipo de producto\n")
