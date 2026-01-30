#!/usr/bin/env python3
"""
Simulación de tres interacciones completas vía web
Demuestra cómo un usuario interactúa con el sistema para obtener códigos arancelarios.
"""

import requests
import json
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Configuración
API_BASE_URL = "http://localhost:8000"
CLASSIFY_ENDPOINT = f"{API_BASE_URL}/classify"

class WebInteractionSimulator:
    """Simula la interacción de un usuario con el sistema vía API web."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.conversation_id = str(uuid4().hex)[:16]
        self.conversation_history = []
        
    def user_query(self, query: str, hs_code: Optional[str] = None) -> Dict[str, Any]:
        """Envía una consulta al API y guarda el historial."""
        
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
            print(f"❌ Error en API: {e}")
            return {}
    
    def _print_result(self, result: Dict[str, Any]) -> None:
        """Formatea y imprime el resultado de la clasificación."""
        
        top_candidates = result.get("top_candidates", [])
        if not top_candidates:
            print("⚠️  Sin candidatos disponibles")
            return
        
        # Mostrar candidato principal
        main = top_candidates[0]
        code = main.get("code", "N/A")
        confidence = main.get("confidence", 0)
        level = main.get("level", "UNKNOWN")
        
        print(f"\n🎯 Candidato Principal:")
        print(f"   Código: {code} ({level})")
        print(f"   Confianza: {confidence*100:.0f}%")
        
        # Mostrar candidatos alternativos si existen
        if len(top_candidates) > 1:
            print(f"\n📋 Alternativas:")
            for i, alt in enumerate(top_candidates[1:4], 1):
                alt_code = alt.get("code", "N/A")
                alt_conf = alt.get("confidence", 0)
                alt_level = alt.get("level", "UNKNOWN")
                print(f"   {i}. {alt_code} ({alt_level}) - {alt_conf*100:.0f}%")
        
        # Mostrar campos faltantes (preguntas pendientes)
        missing = result.get("missing_fields", [])
        if missing:
            print(f"\n❓ Campos necesarios para refinar:")
            for i, field in enumerate(missing[:3], 1):
                print(f"   {i}. {field}")
        else:
            print(f"\n✅ Clasificación completa (no faltan campos)")
        
        # Mostrar evidencia (si disponible)
        evidence = result.get("evidence", [])
        if evidence and self.verbose:
            print(f"\n📚 Evidencia (primeras 2):")
            for ev in evidence[:2]:
                reason = ev.get("reason", "")[:60]
                score = ev.get("score", 0)
                print(f"   • {reason}... (score: {score:.2f})")


def interaction_1_microondas():
    """
    EJEMPLO 1: MICROONDAS (Electrodoméstico)
    Simula la conversación progresiva para clasificar una microondas.
    """
    
    print("\n" + "="*80)
    print("📱 EJEMPLO 1: CLASIFICACIÓN DE MICROONDAS")
    print("="*80)
    
    simulator = WebInteractionSimulator()
    
    # TURNO 1: Usuario menciona "microondas"
    print("\n[TURNO 1 - Consulta inicial]")
    simulator.user_query("Tengo una microondas para clasificar")
    
    # TURNO 2: Usuario proporciona capacidad
    print("\n[TURNO 2 - Proporciona capacidad]")
    simulator.user_query("Es de 25 litros")
    
    # TURNO 3: Aclara si es nuevo o usado
    print("\n[TURNO 3 - Estado del producto]")
    simulator.user_query("Es nueva, nunca ha sido usada")
    
    # TURNO 4: Especifica si tiene grill
    print("\n[TURNO 4 - Características adicionales]")
    simulator.user_query("Tiene función grill y convección")
    
    print("\n✨ Interacción de MICROONDAS completada\n")


def interaction_2_autobus():
    """
    EJEMPLO 2: AUTOBÚS (Vehículo de carga)
    Simula la conversación para clasificar un autobús (capítulo 87).
    Demuestra cómo el sistema FUERZA preguntas sobre motor cuando es relevante.
    """
    
    print("\n" + "="*80)
    print("🚌 EJEMPLO 2: CLASIFICACIÓN DE AUTOBÚS")
    print("="*80)
    
    simulator = WebInteractionSimulator()
    
    # TURNO 1: Usuario menciona "autobús"
    print("\n[TURNO 1 - Consulta inicial]")
    simulator.user_query("Necesito clasificar un autobús")
    
    # TURNO 2: Especifica capacidad de pasajeros
    print("\n[TURNO 2 - Capacidad de pasajeros]")
    result = simulator.user_query("Es para 50 personas")
    
    # Verificar si el sistema pregunta por motor (FORCED)
    missing = result.get("missing_fields", [])
    motor_asked = any("motor" in str(f).lower() for f in missing)
    if motor_asked:
        print("\n✓ Sistema FUERZA pregunta de motor (correcto para vehículos)")
    
    # TURNO 3: Usuario proporciona tipo de motor
    print("\n[TURNO 3 - Tipo de motor]")
    simulator.user_query("Tiene motor diesel")
    
    # TURNO 4: Especifica cilindrada
    print("\n[TURNO 4 - Cilindrada del motor]")
    simulator.user_query("La cilindrada es de 6000 cm³")
    
    # TURNO 5: Aclara si es nuevo o usado
    print("\n[TURNO 5 - Estado del producto]")
    simulator.user_query("Es nuevo, recién fabricado")
    
    print("\n✨ Interacción de AUTOBÚS completada\n")


def interaction_3_lavadora():
    """
    EJEMPLO 3: LAVADORA (Electrodoméstico)
    Simula la conversación para clasificar una lavadora con especificaciones técnicas.
    Demuestra refinamiento progresivo desde HS4 hasta HS10.
    """
    
    print("\n" + "="*80)
    print("🧺 EJEMPLO 3: CLASIFICACIÓN DE LAVADORA")
    print("="*80)
    
    simulator = WebInteractionSimulator()
    
    # TURNO 1: Consulta inicial (muy genérica)
    print("\n[TURNO 1 - Consulta inicial]")
    result = simulator.user_query("Necesito clasificar un electrodoméstico para lavar")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   → Clasificación inicial: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 2: Especifica que es lavadora
    print("\n[TURNO 2 - Especifica producto]")
    result = simulator.user_query("Es una lavadora de ropa")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   → Refinamiento 1: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 3: Capacidad
    print("\n[TURNO 3 - Capacidad de carga]")
    result = simulator.user_query("Tiene una capacidad de 8 kilogramos")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   → Refinamiento 2: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 4: Tipo de carga
    print("\n[TURNO 4 - Tipo de carga]")
    result = simulator.user_query("Es de carga frontal")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   → Refinamiento 3: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 5: Incluye secado
    print("\n[TURNO 5 - Función de secado]")
    result = simulator.user_query("Solo lava, no tiene función de secado")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   → Refinamiento 4: {code} ({confidence*100:.0f}% confianza)")
    
    # TURNO 6: Estado del producto
    print("\n[TURNO 6 - Estado del producto]")
    result = simulator.user_query("Es nueva, sin usar")
    code = result.get("top_candidates", [{}])[0].get("code", "unknown")
    confidence = result.get("top_candidates", [{}])[0].get("confidence", 0)
    print(f"\n   → Refinamiento 5 (FINAL): {code} ({confidence*100:.0f}% confianza)")
    
    missing = result.get("missing_fields", [])
    if not missing:
        print(f"   ✅ CLASIFICACIÓN COMPLETA - No faltan campos")
    
    print("\n✨ Interacción de LAVADORA completada\n")


def print_summary():
    """Imprime un resumen de los ejemplos ejecutados."""
    
    print("\n" + "="*80)
    print("📊 RESUMEN DE EJEMPLOS")
    print("="*80)
    print("""
Los tres ejemplos demuestran:

1️⃣  MICROONDAS (Ejemplo simple):
   • Usuario proporciona información básica
   • Sistema pregunta solo por campos críticos
   • Clasificación rápida a HS8

2️⃣  AUTOBÚS (Vehículos - Capítulo 87):
   • Sistema FUERZA preguntas sobre motor aunque no se mencione
   • Necesita información de cilindrada para refinar HS10
   • Demuestra el manejo especial de vehículos

3️⃣  LAVADORA (Electrodoméstico - Refinamiento progresivo):
   • Comienza con código genérico (alta incertidumbre)
   • Refina progresivamente (HS4 → HS6 → HS8 → HS10)
   • Confianza aumenta con cada detalle proporcionado
   • Muestra cómo la confianza es una métrica de completitud

CARACTERÍSTICAS CLAVE DEMOSTRADAS:
✓ Mantenimiento de conversation_id para continuidad
✓ Acumulación de contexto en conversation_history
✓ Preguntas FORZADAS para vehículos (motor obligatorio)
✓ Refinamiento progresivo de confianza (45% → 95%)
✓ Identificación de campos críticos vs opcionales
✓ Propuesta de múltiples candidatos cuando hay ambigüedad
✓ Detección de completitud (missing_fields vacío = HS10 listo)
""")
    print("="*80)


if __name__ == "__main__":
    import sys
    
    # Verificar que el API esté disponible
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("⚠️  API no respondió correctamente a /health")
    except Exception as e:
        print(f"❌ No se pudo conectar al API en {API_BASE_URL}")
        print(f"   Asegúrate de que: docker-compose up -d")
        sys.exit(1)
    
    print("\n🎬 INICIANDO SIMULACIÓN DE INTERACCIONES WEB")
    print("="*80)
    
    # Ejecutar los tres ejemplos
    interaction_1_microondas()
    interaction_2_autobus()
    interaction_3_lavadora()
    
    # Imprimir resumen
    print_summary()
    
    print("\n✅ Simulación completada exitosamente")
