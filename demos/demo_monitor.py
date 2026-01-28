#!/usr/bin/env python3
"""
🌐 DEMO: MONITOR ELECTRÓNICO
============================
Clasificación progresiva de un monitor para computadora
Muestra adaptación contextual de campos
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
    print(f"{BOLD}{CYAN}  🌐 DEMO: MONITOR ELECTRÓNICO{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    conv_id = f"demo_monitor_{int(time.time())}"
    
    queries = [
        ("Quiero importar un monitor electrónico", 1),
        ("Es un monitor LED para computadora, pantalla plana", 2),
        ("Monitor de 27 pulgadas, resolución 4K UHD, conectores HDMI DisplayPort", 3)
    ]
    
    print(f"{BOLD}Turno 1 → Código genérico (dispositivo electrónico){RESET}")
    print(f"{BOLD}Turno 2 → Más específico (tipo de monitor){RESET}")
    print(f"{BOLD}Turno 3 → Detallado (especificaciones técnicas){RESET}\n")
    
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
                        if any(kw in field_lower for kw in ['motor', 'cilindrada', 'pasajeros', 'tracción', 'gasolina']):
                            marker = f"{RED}❌ [VEHÍCULO]{RESET}"
                        elif any(kw in field_lower for kw in ['tamaño pantalla', 'pulgadas', 'resolucion', 'puertos', 'conectores', 'hdmi']):
                            marker = f"{BLUE}✅ [MONITOR]{RESET}"
                        elif any(kw in field_lower for kw in ['voltaje', 'frecuencia', 'capacidad', 'funcion secado']):
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
            else:
                print(f"  {YELLOW}⚠️  Sin clasificación obtenida (puede ser normal en turno 1){RESET}\n")
        
        time.sleep(1)
    
    # RESUMEN
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}  📊 RESUMEN{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    if codes:
        print(f"{BOLD}Progresión de códigos:{RESET}")
        for i, (code, conf) in enumerate(zip(codes, confs), 1):
            bar = "→" if i < len(codes) else "✓"
            print(f"  {bar} Turno {i}: {GREEN}{code:12}{RESET} @ {conf}%")
        
        if len(confs) > 1 and confs[-1] > 0:
            print(f"\n{BOLD}Evolución de confianza:{RESET}")
            print(f"  Inicial: {confs[0]}%")
            print(f"  Final:   {confs[-1]}%")
            if confs[-1] != confs[0]:
                print(f"  Cambio:  +{confs[-1] - confs[0]}%")
    
    print(f"\n{BOLD}Categoría HS:{RESET} 8528 (Receptores de televisión, monitores)")
    print(f"{BOLD}Subcategoría:{RESET} Monitor electrónico para computadora")
    print(f"{BOLD}Campos apropiados:{RESET} Tamaño pantalla, resolución, puertos/conectores")
    print(f"{BOLD}Campos NO apropiados:{RESET} Motor, cilindrada, pasajeros, voltaje, capacidad")
    
    print(f"\n{BOLD}{GREEN}✅ DEMOSTRACIÓN COMPLETADA{RESET}\n")

if __name__ == "__main__":
    try:
        demo()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrumpido{RESET}")
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
