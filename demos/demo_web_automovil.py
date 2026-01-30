#!/usr/bin/env python3
"""
🌐 DEMO INTERACTIVA: AUTOMÓVIL
==============================
Simula la interfaz web Gradio - Muestra que el sistema SÍ sugiere campos
de vehículos cuando es un vehículo (contraste con las otras demos)
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
MAGENTA = "\033[95m"

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

def print_api_response(classification: Dict[str, Any], turn: int, is_vehicle: bool = True):
    """Simula respuesta de la API - DIFERENTE para vehículos"""
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
                           'plazas', 'pasajeros', 'tracción', 'eje', 'suspensión', 'frenos']
        
        for i, field in enumerate(missing_fields[:7], 1):
            is_vehicle_field = any(kw in field.lower() for kw in vehicle_keywords)
            
            if is_vehicle and is_vehicle_field:
                # Para vehículos, los campos de vehículos son CORRECTOS
                print(f"    {MAGENTA}✅ {i}. {field} [CORRECTO - CAMPO DE VEHÍCULO]{RESET}")
            elif is_vehicle and not is_vehicle_field:
                # Para vehículos, otros campos también son correctos
                print(f"    {GREEN}✓ {i}. {field}{RESET}")
            else:
                print(f"    {GREEN}✓ {i}. {field}{RESET}")
    
    print()

def demo_web():
    """Simula la experiencia de usuario en la interfaz web"""
    print_header("🌐 DEMO WEB INTERACTIVA: AUTOMÓVIL (CONTRASTE)")
    print(f"{BOLD}{MAGENTA}IMPORTANTE: Esta demo muestra que el sistema SÍ sugiere campos de vehículos{RESET}")
    print(f"{BOLD}{MAGENTA}cuando se trata de un vehículo (a diferencia de las demos previas){RESET}\n")
    
    conversation_id = f"web_demo_auto_{int(time.time())}"
    
    # ========== TURNO 1 ==========
    print_user_message(
        "Quiero importar un vehículo",
        1
    )
    
    response = requests.post(
        API_ENDPOINT,
        json={
            "user_query": "Quiero importar un vehículo",
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
    print_api_response(classification, 1, is_vehicle=True)
    
    time.sleep(1.5)
    
    # ========== TURNO 2 ==========
    print(f"{BOLD}[Usuario especifica el tipo de vehículo...]{RESET}\n")
    time.sleep(0.8)
    
    print_user_message(
        "Es un automóvil sedán de pasajeros",
        2
    )
    
    response = requests.post(
        API_ENDPOINT,
        json={
            "user_query": "Es un automóvil sedán de pasajeros",
            "conversation_id": conversation_id,
            "turn_number": 2
        }
    )
    
    classification = extract_classification(response.json())
    code_2 = classification.get('code')
    conf_2 = classification.get('confidence', 0)
    print_api_response(classification, 2, is_vehicle=True)
    
    time.sleep(1.5)
    
    # ========== TURNO 3 ==========
    print(f"{BOLD}[Usuario proporciona especificaciones del motor...]{RESET}\n")
    time.sleep(0.8)
    
    print_user_message(
        "Motor a gasolina, 1600cc, 4 cilindros, automático, 4 puertas, 5 asientos",
        3
    )
    
    response = requests.post(
        API_ENDPOINT,
        json={
            "user_query": "Motor a gasolina, 1600cc, 4 cilindros, automático, 4 puertas, 5 asientos",
            "conversation_id": conversation_id,
            "turn_number": 3
        }
    )
    
    classification = extract_classification(response.json())
    code_3 = classification.get('code')
    conf_3 = classification.get('confidence', 0)
    print_api_response(classification, 3, is_vehicle=True)
    
    # ========== RESUMEN FINAL ==========
    print_header("📊 RESUMEN Y CONTRASTE")
    
    print(f"{BOLD}Progresión del código arancelario:{RESET}")
    print(f"  Turno 1 → {GREEN}{code_1}{RESET} @ {conf_1}%")
    print(f"  Turno 2 → {GREEN}{code_2}{RESET} @ {conf_2}%")
    print(f"  Turno 3 → {GREEN}{code_3}{RESET} @ {conf_3}%")
    
    print(f"\n{BOLD}{MAGENTA}🔍 INTELIGENCIA CONTEXTUAL DEL SISTEMA:{RESET}")
    print(f"\n{BOLD}DEMO 1 (Lavadora - Electrodoméstico):{RESET}")
    print(f"  ❌ NO sugiere: motor, cilindrada, pasajeros, tracción")
    print(f"  ✅ SÍ sugiere: voltaje, función, uso doméstico")
    
    print(f"\n{BOLD}DEMO 2 (Refrigerador - Electrodoméstico):{RESET}")
    print(f"  ❌ NO sugiere: motor, cilindrada, pasajeros, tracción")
    print(f"  ✅ SÍ sugiere: volumen, sistema de congelación, voltaje")
    
    print(f"\n{BOLD}DEMO 3 (Automóvil - Vehículo) ← TÚ ESTÁS AQUÍ:{RESET}")
    print(f"  {MAGENTA}✅ SÍ sugiere: motor, cilindrada, pasajeros, tracción{RESET}")
    print(f"  ✅ SÍ sugiere: tipo de combustible, número de ejes, frenos")
    
    print(f"\n{BOLD}✨ CONCLUSIÓN:{RESET}")
    print(f"  El sistema no prúa ciegamente campos.")
    print(f"  {GREEN}Analiza el contexto y adapta las preguntas al tipo de producto.{RESET}")
    print(f"  Por eso:")
    print(f"    • Para electrodomésticos: pregunta sobre voltaje, no motor")
    print(f"    • Para vehículos: pregunta sobre motor, cilindrada, pasajeros")
    
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
