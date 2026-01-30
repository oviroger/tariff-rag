#!/usr/bin/env python3
"""
🌐 DEMO: COMPUTADORA - EQUIPO INFORMÁTICO
=========================================
Clasificación progresiva de una computadora
Muestra cómo el sistema adapta campos según el tipo de producto
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

def demo():
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}  🌐 DEMO: COMPUTADORA - EQUIPO INFORMÁTICO{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    conv_id = f"demo_comp_{int(time.time())}"
    
    queries = [
        ("Quiero importar una computadora", 1),
        ("Es una laptop/notebook con procesador Intel", 2),
        ("Intel Core i7, 16GB RAM DDR4, SSD 512GB, pantalla 15.6 pulgadas", 3)
    ]
    
    print(f"{BOLD}Turno 1 → Código genérico (máquinas de procesamiento){RESET}")
    print(f"{BOLD}Turno 2 → Más específico (laptop vs desktop){RESET}")
    print(f"{BOLD}Turno 3 → Refinado (especificaciones técnicas){RESET}\n")
    
    codes = []
    confs = []
    
    for query, turn in queries:
        print(f"{BOLD}👤 TURNO {turn}:{RESET} {YELLOW}{query}{RESET}\n")
        
        resp = requests.post(API, json={
            "user_query": query,
            "conversation_id": conv_id,
            "turn_number": turn
        })
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('top_candidates'):
                top = data['top_candidates'][0]
                code = top.get('code', 'N/A')
                conf = int(top.get('confidence', 0) * 100)
                
                codes.append(code)
                confs.append(conf)
                
                print(f"{BOLD}🤖 CLASIFICACIÓN:{RESET}")
                print(f"  {GREEN}Código: {code}{RESET}")
                print(f"  {GREEN}Confianza: {conf}%{RESET}")
                print(f"  {GREEN}Nivel: {top.get('level', 'N/A')}{RESET}\n")
                
                # Mostrar campos sugeridos
                missing = data.get('missing_fields', [])
                if missing:
                    print(f"  {BOLD}Campos sugeridos:{RESET}")
                    for i, field in enumerate(missing[:4], 1):
                        field_lower = field.lower()
                        
                        # Detectar tipo de campo
                        if any(kw in field_lower for kw in ['motor', 'cilindrada', 'pasajeros', 'tracción']):
                            marker = f"{RED}❌ [VEHÍCULO]{RESET}"
                        elif any(kw in field_lower for kw in ['procesador', 'ram', 'almacenamiento', 'ssd', 'gpu', 'cpu']):
                            marker = f"{BLUE}✅ [INFORMÁTICA]{RESET}"
                        elif any(kw in field_lower for kw in ['voltaje', 'frecuencia', 'capacidad']):
                            marker = f"{YELLOW}⚠️  [ELECTRODOMÉSTICO]{RESET}"
                        else:
                            marker = f"{GREEN}✓{RESET}"
                        
                        print(f"    {marker} {i}. {field[:60]}")
                
                # Validación
                vehicle_fields = [f for f in missing if any(
                    kw in f.lower() for kw in ['motor', 'cilindrada', 'gasolina', 'pasajeros', 'tracción'])]
                
                if vehicle_fields:
                    print(f"\n  {RED}❌ ERROR: Campos de vehículos detectados{RESET}\n")
                else:
                    print(f"\n  {GREEN}✅ Sin campos inapropiados{RESET}\n")
        
        time.sleep(0.8)
    
    # RESUMEN
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}  📊 RESUMEN{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    print(f"{BOLD}Progresión de códigos:{RESET}")
    for i, (code, conf) in enumerate(zip(codes, confs), 1):
        bar = "→" if i < len(codes) else "✓"
        print(f"  {bar} Turno {i}: {GREEN}{code:12}{RESET} @ {conf}%")
    
    if len(confs) > 1:
        print(f"\n{BOLD}Evolución de confianza:{RESET}")
        print(f"  Inicial: {confs[0]}%")
        print(f"  Final:   {confs[-1]}%")
        print(f"  Cambio:  +{confs[-1] - confs[0]}%")
    
    print(f"\n{BOLD}Categoría HS:{RESET} 8471 (Máquinas automáticas de procesamiento de datos)")
    print(f"{BOLD}Tipo:{RESET} Computadora personal (laptop)")
    print(f"{BOLD}Campos apropiados:{RESET} Procesador, RAM, Almacenamiento, Pantalla")
    print(f"{BOLD}Campos NO apropiados:{RESET} Motor, cilindrada, pasajeros, voltaje")
    
    print(f"\n{BOLD}{GREEN}✅ DEMOSTRACIÓN COMPLETADA{RESET}\n")

if __name__ == "__main__":
    try:
        demo()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrumpido{RESET}")
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
