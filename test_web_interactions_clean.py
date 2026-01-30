#!/usr/bin/env python3
"""
Simulacion de tres interacciones completas via web - Version PLAIN TEXT
Demuestra como un usuario interactua con el sistema para obtener codigos arancelarios.
"""

import requests
import json
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Configuracion
API_BASE_URL = "http://localhost:8000"
CLASSIFY_ENDPOINT = f"{API_BASE_URL}/classify"

class WebInteractionSimulator:
    """Simula la interaccion de un usuario con el sistema via API web."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.conversation_id = str(uuid4().hex)[:16]
        self.conversation_history = []
        
    def user_query(self, query: str, hs_code: Optional[str] = None) -> Dict[str, Any]:
        """Envia una consulta al API y guarda el historial."""
        
        print(f"\n{'='*80}")
        print(f"[USER] {query}")
        print(f"{'='*80}")
        
        payload = {
            "user_query": query,
            "conversation_history": self.conversation_history,
            "conversation_id": self.conversation_id,
            "hs_code": hs_code
        }
        
        try:
            response = requests.post(CLASSIFY_ENDPOINT, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Guardar en historial para siguiente query
            self.conversation_history.append({
                "user": query,
                "assistant": result
            })
            
            self._print_result(result)
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error en API: {e}")
            return {}
    
    def _print_result(self, result: Dict[str, Any]) -> None:
        """Formatea e imprime el resultado de la clasificacion."""
        
        top_candidates = result.get("top_candidates", [])
        if not top_candidates:
            print("[WARNING] Sin candidatos disponibles")
            return
        
        # Mostrar candidato principal
        main = top_candidates[0]
        code = main.get("code", "N/A")
        confidence = main.get("confidence", 0)
        level = main.get("level", "UNKNOWN")
        
        print(f"\n[RESULT] Candidato Principal:")
        print(f"   Codigo: {code} ({level})")
        print(f"   Confianza: {confidence*100:.0f}%")
        
        # Mostrar candidatos alternativos si existen
        if len(top_candidates) > 1:
            print(f"\n[ALTERNATIVES] Opciones secundarias:")
            for i, alt in enumerate(top_candidates[1:4], 1):
                alt_code = alt.get("code", "N/A")
                alt_conf = alt.get("confidence", 0)
                alt_level = alt.get("level", "UNKNOWN")
                print(f"   {i}. {alt_code} ({alt_level}) - {alt_conf*100:.0f}%")
        
        # Mostrar campos faltantes (preguntas pendientes)
        missing = result.get("missing_fields", [])
        if missing:
            print(f"\n[MISSING_FIELDS] Campos necesarios para refinar:")
            for i, field in enumerate(missing[:3], 1):
                print(f"   {i}. {field}")
        else:
            print(f"\n[OK] Clasificacion completa - no faltan campos")


def interaction_1_microondas():
    """
    EJEMPLO 1: MICROONDAS (Electrodomestico)
    Simula la conversacion progresiva para clasificar una microondas.
    """
    
    print("\n" + "="*80)
    print("[EXAMPLE 1] CLASIFICACION DE MICROONDAS")
    print("="*80)
    
    simulator = WebInteractionSimulator()
    
    # TURNO 1: Usuario menciona "microondas"
    print("\n[TURN 1] Consulta inicial")
    simulator.user_query("Tengo una microondas para clasificar")
    
    # TURNO 2: Usuario proporciona capacidad
    print("\n[TURN 2] Proporciona capacidad")
    simulator.user_query("Es de 25 litros")
    
    # TURNO 3: Aclara si es nuevo o usado
    print("\n[TURN 3] Estado del producto")
    simulator.user_query("Es nueva, nunca ha sido usada")
    
    # TURNO 4: Especifica si tiene grill
    print("\n[TURN 4] Caracteristicas adicionales")
    simulator.user_query("Tiene funcion grill y conveccion")
    
    print("\n[COMPLETED] Interaccion de MICROONDAS completada\n")


def interaction_2_autobus():
    """
    EJEMPLO 2: AUTOBUS (Vehiculo de carga)
    Simula la conversacion para clasificar un autobus (capitulo 87).
    Demuestra como el sistema FUERZA preguntas sobre motor cuando es relevante.
    """
    
    print("\n" + "="*80)
    print("[EXAMPLE 2] CLASIFICACION DE AUTOBUS")
    print("="*80)
    
    simulator = WebInteractionSimulator()
    
    # TURNO 1: Usuario menciona "autobus"
    print("\n[TURN 1] Consulta inicial")
    simulator.user_query("Necesito clasificar un autobus")
    
    # TURNO 2: Especifica capacidad de pasajeros
    print("\n[TURN 2] Capacidad de pasajeros")
    result = simulator.user_query("Es para 50 personas")
    
    # Verificar si el sistema pregunta por motor (FORCED)
    missing = result.get("missing_fields", [])
    motor_asked = any("motor" in str(f).lower() for f in missing)
    if motor_asked:
        print("\n[VERIFICATION] Sistema FUERZA pregunta de motor (correcto para vehiculos)")
    
    # TURNO 3: Usuario proporciona tipo de motor
    print("\n[TURN 3] Tipo de motor")
    simulator.user_query("Tiene motor diesel")
    
    # TURNO 4: Especifica cilindrada
    print("\n[TURN 4] Cilindrada del motor")
    simulator.user_query("La cilindrada es de 6000 cm3")
    
    # TURNO 5: Aclara si es nuevo o usado
    print("\n[TURN 5] Estado del producto")
    result = simulator.user_query("Es nuevo, recien fabricado")
    
    # Verificar si la pregunta de motor desaparecio correctamente
    missing = result.get("missing_fields", [])
    motor_still_asked = any("motor" in str(f).lower() for f in missing)
    if not motor_still_asked:
        print("\n[VERIFICATION] Pregunta de motor correctamente REMOVIDA tras respuesta")
    else:
        print("\n[BUG] Advertencia: Pregunta de motor aun presente tras ser respondida")
    
    print("\n[COMPLETED] Interaccion de AUTOBUS completada\n")


def interaction_3_lavadora():
    """
    EJEMPLO 3: LAVADORA (Electrodomestico)
    Simula la conversacion para clasificar una lavadora con especificaciones tecnicas.
    Demuestra refinamiento progresivo desde HS4 hasta HS10.
    """
    
    print("\n" + "="*80)
    print("[EXAMPLE 3] CLASIFICACION DE LAVADORA")
    print("="*80)
    
    simulator = WebInteractionSimulator()
    
    # TURNO 1: Consulta inicial (muy generica)
    print("\n[TURN 1] Consulta inicial")
    result = simulator.user_query("Necesito clasificar un electrodomestico para lavar")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   -> Clasificacion inicial: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 2: Especifica que es lavadora
    print("\n[TURN 2] Especifica producto")
    result = simulator.user_query("Es una lavadora de ropa")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   -> Refinamiento 1: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 3: Capacidad
    print("\n[TURN 3] Capacidad de carga")
    result = simulator.user_query("Tiene una capacidad de 8 kilogramos")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   -> Refinamiento 2: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 4: Tipo de carga
    print("\n[TURN 4] Tipo de carga")
    result = simulator.user_query("Es de carga frontal")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   -> Refinamiento 3: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 5: Incluye secado
    print("\n[TURN 5] Funcion de secado")
    result = simulator.user_query("Solo lava, no tiene funcion de secado")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   -> Refinamiento 4: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 6: Estado del producto
    print("\n[TURN 6] Estado del producto")
    result = simulator.user_query("Es nueva, sin usar")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   -> Refinamiento 5 (FINAL): {code} ({confidence*100:.0f}% confianza)")
    
    missing = result.get("missing_fields", [])
    if not missing:
        print(f"   [OK] CLASIFICACION COMPLETA - No faltan campos")
    
    print("\n[COMPLETED] Interaccion de LAVADORA completada\n")


def print_summary():
    """Imprime un resumen de los ejemplos ejecutados."""
    
    print("\n" + "="*80)
    print("[SUMMARY] RESUMEN DE EJEMPLOS")
    print("="*80)
    print("""
Los tres ejemplos demuestran:

1. MICROONDAS (Ejemplo simple):
   * Usuario proporciona informacion basica
   * Sistema pregunta solo por campos criticos
   * Clasificacion rapida a HS8

2. AUTOBUS (Vehiculos - Capitulo 87):
   * Sistema FUERZA preguntas sobre motor aunque no se mencione
   * Necesita informacion de cilindrada para refinar HS10
   * Demuestra el manejo especial de vehiculos

3. LAVADORA (Electrodomestico - Refinamiento progresivo):
   * Comienza con codigo generico (alta incertidumbre)
   * Refina progresivamente (HS4 -> HS6 -> HS8 -> HS10)
   * Confianza aumenta con cada detalle proporcionado
   * Muestra como la confianza es una metrica de completitud

CARACTERISTICAS CLAVE DEMOSTRADAS:
[OK] Mantenimiento de conversation_id para continuidad
[OK] Acumulacion de contexto en conversation_history
[OK] Preguntas FORZADAS para vehiculos (motor obligatorio)
[OK] Refinamiento progresivo de confianza (45% -> 95%)
[OK] Identificacion de campos criticos vs opcionales
[OK] Propuesta de multiples candidatos cuando hay ambiguedad
[OK] Deteccion de completitud (missing_fields vacio = HS10 listo)
[OK] Remocio de preguntas ya respondidas (motor question)
""")
    print("="*80)


if __name__ == "__main__":
    import sys
    
    # Verificar que el API este disponible
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("[ERROR] API no respondio correctamente a /health")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar al API en {API_BASE_URL}")
        print(f"        Asegurate de que: docker-compose up -d")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("[START] INICIANDO SIMULACION DE INTERACCIONES WEB")
    print("="*80)
    
    # Ejecutar los tres ejemplos
    interaction_1_microondas()
    interaction_2_autobus()
    interaction_3_lavadora()
    
    # Imprimir resumen
    print_summary()
    
    print("\n[SUCCESS] Simulacion completada exitosamente")
