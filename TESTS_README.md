# Tests de Clasificación Arancelaria Multi-Turno

## Estructura de Tests

Este conjunto de tests valida el comportamiento del chatbot de clasificación arancelaria en conversaciones multi-turno, donde el usuario responde parcialmente a las preguntas sugeridas.

### Archivos de Test

#### **Grupo 1: Productos Industriales** (ya ejecutado)
- **Script**: `test_chatbot_simulation.ps1`
- **Resultados**: `test_chatbot_group1_resultados.txt`
- **Productos**: Válvula, Tubo, Bomba, Motor eléctrico, Aceite

#### **Grupo 2: Alimentos y Bebidas**
- **Script**: `test_chatbot_group2.ps1`
- **Resultados**: `test_chatbot_group2_resultados.txt`
- **Productos**: Queso, Vino, Chocolate, Jugo de fruta, Pescado

#### **Grupo 3: Textiles y Calzado**
- **Script**: `test_chatbot_group3.ps1`
- **Resultados**: `test_chatbot_group3_resultados.txt`
- **Productos**: Tela, Alfombra, Botas, Guantes, Bolso

#### **Grupo 4: Químicos y Farmacéuticos**
- **Script**: `test_chatbot_group4.ps1`
- **Resultados**: `test_chatbot_group4_resultados.txt`
- **Productos**: Pintura, Medicamento, Fertilizante, Detergente, Pegamento

#### **Grupo 5: Electrónica y Electrodomésticos**
- **Script**: `test_chatbot_group5.ps1`
- **Resultados**: `test_chatbot_group5_resultados.txt`
- **Productos**: Televisor, Parlante, Impresora, Ventilador, Calefactor

---

## Ejecución

### Ejecutar todos los grupos
```powershell
pwsh -ExecutionPolicy Bypass -File .\run_all_tests.ps1
```

### Ejecutar un grupo específico
```powershell
pwsh -ExecutionPolicy Bypass -File .\test_chatbot_group2.ps1
```

---

## Metodología de Test

### Flujo de Conversación

1. **Turno 1**: Usuario hace consulta genérica (ej: "Queso")
2. **Sistema**: Genera código arancelario y solicita información faltante
3. **Turno 2**: Usuario responde parcialmente (1-2 datos)
4. **Sistema**: Refina clasificación y puede solicitar más datos
5. **Turno 3+**: Proceso continúa hasta alcanzar confianza ≥95% o 4 turnos

### Validación Dual

Cada producto se prueba en dos flujos:
- **API**: Llamada directa al endpoint `/classify`
- **UI**: Interacción con Gradio (chat_minimal_validation)

### Lógica de Respuestas Parciales

El test simula respuestas realistas del usuario:
- **No responde todo** en un solo turno
- **Prioriza información crítica** (material, tipo, uso)
- **Evita repeticiones** de datos ya proporcionados

---

## Análisis de Resultados

### Estructura del Output

```
=== Producto ===
Turno 1 | Query: [consulta inicial]
API -> [código] ([confianza]%) | Missing: [cantidad]
Opciones sugeridas por el chatbot:
 - [pregunta 1]
 - [pregunta 2]
Respuesta parcial del usuario:
 - [respuesta parcial]

UI Turno 1 -> [código]
UI respuesta: [respuesta formateada]
UI opciones sugeridas:
 - [pregunta 1]
UI respuesta parcial del usuario:
 - [respuesta parcial]

UI -> Código final: [código]
```

### Métricas a Evaluar

1. **Convergencia API/UI**: Ambos flujos deben llegar al mismo código
2. **Número de turnos**: Productos complejos requieren 2-3 turnos
3. **Calidad de preguntas**: Deben ser específicas y relevantes
4. **Consistencia categorial**: No drift entre categorías (ej: textil→vehículo)

---

## Casos de Uso Cubiertos

### ✅ Productos con Clasificación Inmediata
- Productos específicos con código único (ej: "Lavadora automática" → 8450.11)

### ✅ Productos Ambiguos (Requieren Refinamiento)
- **Material determinante**: Tubo (acero vs plástico vs cobre)
- **Tipo determinante**: Aceite (mineral vs vegetal)
- **Uso determinante**: Bomba (agua vs combustible)

### ✅ Productos Multi-Atributo
- Requieren varios datos para clasificación completa
- Ejemplo: Queso (tipo de leche + maduración + grasa)

### ⚠️ Casos Problemáticos Detectados
- **Motor eléctrico**: API confundió con vehículo (8702 en lugar de 8501)
- **Bomba**: Divergencia API (8413.70) vs UI (8413.19)

---

## Mejoras Detectadas

### ✅ Resuelto: Prompt con Lógica de Vehículos
- **Problema**: Prompt incluía lógica de vehículos para todos los productos
- **Síntoma**: "Camiseta" retornaba N/A porque LLM buscaba atributos de vehículo
- **Solución**: Lógica de vehículos ahora es condicional (solo si query menciona vehículo)

### ✅ Resuelto: Category Locking
- **Problema**: Textiles derivaban a vehículos en multi-turno
- **Solución**: Validación de consistencia categorial con locks para capítulos 50-63 (textil) y 72-76 (metal)

---

## Requisitos

- API corriendo en `localhost:8000`
- UI Gradio corriendo en `localhost:7860`
- PowerShell 7+
- Año de referencia: 2026

---

## Próximos Pasos

1. Ejecutar `run_all_tests.ps1` para generar línea base completa
2. Analizar divergencias API/UI en resultados
3. Revisar casos donde se requieren más de 3 turnos (posible sobre-fragmentación)
4. Validar que preguntas generadas sean pertinentes al contexto

---

**Última actualización**: 2026-01-29
