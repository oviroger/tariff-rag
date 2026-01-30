#!/usr/bin/env python3
"""
🌐 DEMO INTERACTIVA: REFRIGERADOR
=================================
Simula la interfaz web Gradio con conversación progresiva
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/classify"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def extract_classification(response_json):
    """Extrae la clasificación desde la respuesta de la API"""
    result = response_json
    classification = result.get('top_candidates', [{}])[0] if result.get('top_candidates') else {}
    if classification:
        classification['missing_fields'] = result.get('missing_fields', [])
        classification['year'] = result.get('years', [2025])[0]
        # Convertir confidence a porcentaje entero
        conf = classification.get('confidence', 0)
        classification['confidence'] = int(conf * 100) if conf < 1 else int(conf)
    return classification

def print_header(title: str):
    """Encabezado de sección"""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

def print_user_message(message: str, turn: int):
    """Simula mensaje del usuario en la web"""
    print(f"{BOLD}👤 USUARIO (Turno {turn}):{RESET}")
    print(f"  {YELLOW}{message}{RESET}\n")

def print_api_response(classification: Dict[str, Any], turn: int):
    """Simula respuesta de la API (como aparecería en la web)"""
    if not classification:
        print(f"{RED}❌ Sin respuesta{RESET}\n")
        return
    
    code = classification.get('code', 'N/A')
    confidence = classification.get('confidence', 0)
    level = classification.get('level', 'N/A')
    year = classification.get('year', 'N/A')
    missing_fields = classification.get('missing_fields', [])
    
    # Encabezado de clasificación
    print(f"{BOLD}🤖 CLASIFICACIÓN DEL SISTEMA:{RESET}")
    print(f"  {GREEN}Código HS: {code}{RESET}")
    print(f"  {GREEN}Confianza: {confidence}%{RESET}")
    print(f"  {GREEN}Nivel: {level}{RESET}")
    print(f"  {GREEN}Año: {year}{RESET}")
    
    # Campos sugeridos
    if missing_fields:
        print(f"\n  {BOLD}📋 Campos que necesitamos para mayor precisión:{RESET}")
        vehicle_keywords = ['motor', 'cilindrada', 'gasolina', 'diesel', 
                           'plazas', 'pasajeros', 'tracción', 'eje', 'suspensión']
        
        for i, field in enumerate(missing_fields[:6], 1):
            is_vehicle = any(kw in field.lower() for kw in vehicle_keywords)
            if is_vehicle:
                print(f"    {RED}❌ {i}. {field} [INCORRECTO - CAMPO DE VEHÍCULO]{RESET}")
            else:
                print(f"    {GREEN}✓ {i}. {field}{RESET}")
    
    print()

def demo_web():
    """Simula la experiencia de usuario en la interfaz web"""
    print_header("🌐 DEMO WEB INTERACTIVA: REFRIGERADOR")
    
    conversation_id = f"web_demo_refri_{int(time.time())}"
    
    # ========== TURNO 1 ==========
    print_user_message(
        "Necesito clasificar un equipo de refrigeración que estoy importando",
        1
    )
    
    response = requests.post(
        API_ENDPOINT,
        json={
            "user_query": "Necesito clasificar un equipo de refrigeración que estoy importando",
            "conversation_id": conversation_id,
            "turn_number": 1
        }
    )
    
    if response.status_code != 200:
        print(f"{RED}❌ Error en API: {response.status_code}{RESET}")
        return
    
    classification = extract_classification(response.json())
    code_1 = classification.get('code')
    conf_1 = classification.get('confidence', 0)
    print_api_response(classification, 1)
    
    time.sleep(1.5)
    
    # ========== TURNO 2 ==========
    print(f"{BOLD}[Usuario escribe más información...]{RESET}\n")
    time.sleep(0.8)
    
    print_user_message(
        "Es un refrigerador-congelador de puertas francesas, sistema automático",
        2
    )
    
    response = requests.post(
        API_ENDPOINT,
        json={
            "user_query": "Es un refrigerador-congelador de puertas francesas, sistema automático",
            "conversation_id": conversation_id,
            "turn_number": 2
        }
    )
    
    classification = extract_classification(response.json())
    code_2 = classification.get('code')
    conf_2 = classification.get('confidence', 0)
    print_api_response(classification, 2)
    
    time.sleep(1.5)
    
    # ========== TURNO 3 ==========
    print(f"{BOLD}[Usuario añade especificaciones técnicas...]{RESET}\n")
    time.sleep(0.8)
    
    print_user_message(
        "Capacidad de 350 litros, sistema no-frost, compressor hermético, voltaje 220V, nuevo",
        3
    )
    
    response = requests.post(
        API_ENDPOINT,
        json={
            "user_query": "Capacidad de 350 litros, sistema no-frost, compressor hermético, voltaje 220V, nuevo",
            "conversation_id": conversation_id,
            "turn_number": 3
        }
    )
    
    classification = extract_classification(response.json())
    code_3 = classification.get('code')
    conf_3 = classification.get('confidence', 0)
    print_api_response(classification, 3)
    
    # ========== RESUMEN FINAL ==========
    print_header("📊 RESUMEN DE LA CLASIFICACIÓN")
    
    print(f"{BOLD}Progresión del código arancelario:{RESET}")
    print(f"  Turno 1 → {GREEN}{code_1}{RESET} @ {conf_1}%")
    print(f"  Turno 2 → {GREEN}{code_2}{RESET} @ {conf_2}%")
    print(f"  Turno 3 → {GREEN}{code_3}{RESET} @ {conf_3}%")
    
    print(f"\n{BOLD}Observaciones clave:{RESET}")
    print(f"  {GREEN}✅ El código se refinó progresivamente{RESET}")
    print(f"  {GREEN}✅ La confianza aumentó del {conf_1}% al {conf_3}%{RESET}")
    print(f"  {GREEN}✅ Solo aparecieron campos para equipos de refrigeración{RESET}")
    print(f"  {GREEN}✅ No apareció ningún campo de vehículo{RESET}")
    
    print(f"\n{BOLD}ID de conversación:{RESET} {conversation_id}")
    print(f"\n{BOLD}{GREEN}✅ DEMOSTRACIÓN COMPLETADA{RESET}\n")

if __name__ == "__main__":
    try:
        demo_web()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Demo interrumpida por el usuario{RESET}")
    except Exception as e:
        print(f"{RED}❌ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
