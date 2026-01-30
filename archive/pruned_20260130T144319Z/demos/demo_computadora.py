#!/usr/bin/env python3
"""
🌐 DEMO INTERACTIVA: COMPUTADORA
================================
Clasificación progresiva de una computadora laptop
Valida que aparecen campos de informática, no de vehículos/electrodomésticos
"""

import requests
import time

API = "http://localhost:8000/classify"

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title: str):
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

def print_turno(num: int, query: str):
    print(f"{BOLD}👤 USUARIO (Turno {num}):{RESET}")
    print(f"  {YELLOW}{query}{RESET}\n")

def print_resultado(data: dict):
    if data.get('top_candidates'):
        top = data['top_candidates'][0]
        code = top.get('code', 'N/A')
        conf = int(top.get('confidence', 0) * 100)
        level = top.get('level', 'N/A')
        year = top.get('years', ['2025'])[0] if top.get('years') else '2025'
        
        print(f"{BOLD}🤖 CLASIFICACIÓN DEL SISTEMA:{RESET}")
        print(f"  {GREEN}Código HS: {code}{RESET}")
        print(f"  {GREEN}Confianza: {conf}%{RESET}")
        print(f"  {GREEN}Nivel: {level}{RESET}")
        print(f"  {GREEN}Año: {year}{RESET}")
        
        missing = data.get('missing_fields', [])
        if missing:
            print(f"\n  {BOLD}📋 Campos que necesitamos:{RESET}")
            
            # Detectar tipos de campos
            vehicle_kw = ['motor', 'cilindrada', 'gasolina', 'diesel', 'pasajeros', 'tracción', 'eje']
            appliance_kw = ['voltaje', 'frecuencia', 'capacidad litros', 'funcion secado']
            it_kw = ['procesador', 'ram', 'almacenamiento', 'memoria', 'pantalla', 'gpu', 'cpu', 'ssd']
            
            for i, field in enumerate(missing[:6], 1):
                field_lower = field.lower()
                
                if any(kw in field_lower for kw in vehicle_kw):
                    marker = f"{RED}❌ [VEHÍCULO - INAPROPIADO]{RESET}"
                elif any(kw in field_lower for kw in appliance_kw):
                    marker = f"{YELLOW}⚠️  [ELECTRODOMÉSTICO - INAPROPIADO]{RESET}"
                elif any(kw in field_lower for kw in it_kw):
                    marker = f"{BLUE}✅ [INFORMÁTICA - CORRECTO]{RESET}"
                else:
                    marker = f"{GREEN}✓{RESET}"
                
                print(f"    {marker} {i}. {field}")
        
        # Validación final
        print()
        vehicle_fields = [f for f in missing if any(kw in f.lower() for kw in vehicle_kw)]
        if vehicle_fields:
            print(f"  {RED}❌ ERROR: Se detectaron campos de vehículos{RESET}")
        else:
            print(f"  {GREEN}✅ Sin campos de vehículos{RESET}")

def demo_computadora():
    print_header("🌐 DEMO: COMPUTADORA - EQUIPO INFORMÁTICO")
    print(f"{BOLD}Validaremos que el sistema sugiere campos relevantes para TI{RESET}\n")
    
    conv_id = f"demo_comp_{int(time.time())}"
    
    queries = [
        "Quiero importar una computadora",
        "Es una laptop/notebook con procesador Intel",
        "Intel Core i7, 16GB RAM DDR4, SSD 512GB, pantalla 15.6 pulgadas Full HD"
    ]
    
    print(f"{BOLD}Progresión esperada:{RESET}")
    print("  Turno 1: Código genérico (máquinas de procesamiento)")
    print("  Turno 2: Más específico (laptop vs desktop)")
    print("  Turno 3: Refinado (especificaciones técnicas)\n")
    
    codes = []
    confs = []
    
    for i, query in enumerate(queries, 1):
        print_turno(i, query)
        
        try:
            resp = requests.post(API, json={
                "user_query": query,
                "conversation_id": conv_id,
                "turn_number": i
            })
            
            if resp.status_code == 200:
                data = resp.json()
                print_resultado(data)
                
                if data.get('top_candidates'):
                    top = data['top_candidates'][0]
                    codes.append(top.get('code'))
                    confs.append(int(top.get('confidence', 0) * 100))
            else:
                print(f"{RED}❌ Error en API: {resp.status_code}{RESET}\n")
        
        except Exception as e:
            print(f"{RED}❌ Error: {e}{RESET}\n")
        
        time.sleep(1)  # Dar tiempo entre requests
    
    # Resumen
    print_header("📊 RESUMEN DE CLASIFICACIÓN")
    
    if codes:
        print(f"{BOLD}Progresión de códigos:{RESET}")
        for j, (code, conf) in enumerate(zip(codes, confs), 1):
            arrow = "→ " if j < len(codes) else "✓"
            print(f"  {arrow} Turno {j}: {GREEN}{code}{RESET} @ {conf}%")
    
    if confs:
        print(f"\n{BOLD}Aumento de confianza:{RESET}")
        print(f"  {confs[0]}% → {confs[-1]}% (+{confs[-1] - confs[0]}%)")
    
    print(f"\n{BOLD}Categoría:{RESET} Equipo Informático (HS 8471)")
    print(f"{BOLD}Campos esperados:{RESET} Procesador, RAM, Almacenamiento, Pantalla")
    print(f"{BOLD}Campos NO esperados:{RESET} Motor, cilindrada, voltaje, pasajeros")
    
    print(f"\n{BOLD}{GREEN}✅ DEMOSTRACIÓN COMPLETADA{RESET}\n")

if __name__ == "__main__":
    try:
        demo_computadora()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Demo interrumpida{RESET}")
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
