#!/usr/bin/env python3
"""
🎬 EJECUTOR DE DEMOSTRACIÓN WEB COMPLETA
========================================
Ejecuta las tres demostraciones interactivas en secuencia
"""

import subprocess
import sys
import time

BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def print_header(text: str):
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

def run_demo(script_name: str, description: str):
    """Ejecuta una demostración"""
    print_header(f"▶️  {description}")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=r"d:\MAESTRIA - copia\tariff-rag",
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"\n{GREEN}✅ {description} completada{RESET}")
        else:
            print(f"\n{RED}❌ {description} falló{RESET}")
            return False
    except Exception as e:
        print(f"{RED}❌ Error ejecutando {description}: {e}{RESET}")
        return False
    
    time.sleep(2)
    return True

def main():
    """Ejecuta todas las demostraciones"""
    print_header("🎬 DEMOSTRACIÓN WEB COMPLETA - SISTEMA TARIFF RAG")
    print(f"{BOLD}Esta demostración muestra 3 casos de uso del sistema:{RESET}\n")
    print("  1. 🌐 LAVADORA (Electrodoméstico simple)")
    print("     → Clasificación progresiva con pruning de campos")
    print()
    print("  2. 🌐 REFRIGERADOR (Electrodoméstico complejo)")
    print("     → Demostración de adaptabilidad a diferentes tipos")
    print()
    print("  3. 🌐 AUTOMÓVIL (Vehículo)")
    print("     → CONTRASTE: Muestra que el pruning es inteligente")
    print()
    print(f"{YELLOW}Presiona ENTER para comenzar...{RESET}")
    input()
    
    demos = [
        ("demo_web_lavadora.py", "DEMO 1: LAVADORA"),
        ("demo_web_refrigerador.py", "DEMO 2: REFRIGERADOR"),
        ("demo_web_automovil.py", "DEMO 3: AUTOMÓVIL"),
    ]
    
    completed = 0
    for script, description in demos:
        if run_demo(script, description):
            completed += 1
        else:
            print(f"{YELLOW}Continuando con la siguiente demo...{RESET}\n")
    
    # Resumen final
    print_header("📊 RESUMEN DE DEMOSTRACIONES")
    print(f"{GREEN}Demostraciones completadas: {completed}/{len(demos)}{RESET}\n")
    
    if completed == len(demos):
        print(f"{GREEN}✅ TODAS LAS DEMOSTRACIONES SE EJECUTARON CORRECTAMENTE{RESET}")
        print(f"\n{BOLD}Puntos clave observados:{RESET}")
        print(f"  ✅ Refinamiento progresivo de códigos HS")
        print(f"  ✅ Aumento de confianza con más detalles")
        print(f"  ✅ Pruning inteligente: se adapta al tipo de producto")
        print(f"  ✅ Multi-turno: mantiene contexto conversacional")
        print(f"  ✅ RAG + LLM: genera sugerencias coherentes")
    else:
        print(f"{YELLOW}⚠️  Algunas demostraciones no se completaron{RESET}")
        print(f"Verifica que la API esté corriendo: docker compose ps")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Ejecución interrumpida por el usuario{RESET}")
    except Exception as e:
        print(f"{RED}❌ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
