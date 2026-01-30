# 🌟 MEJORES EJEMPLOS PARA DEMOSTRACIÓN
## Sistema de Clasificación Arancelaria Multi-Turno

---

## 📌 EJEMPLO #1: TELA (STAR DEMO - 3 TURNOS)

**Categoría**: Textiles y Calzado  
**Complejidad**: Media  
**Turnos**: 3  
**Confianza Final**: 95%  
**Código Final**: 5208.41

### 📝 Descripción
Este es el ejemplo más completo para demostración. Muestra cómo el chatbot:
1. Inicia con una consulta genérica
2. Solicita información clave (material, tejido, uso)
3. Refina progresivamente la clasificación
4. Alcanza especificidad máxima (HS8) con respuestas parciales

---

### 🎬 Flujo Conversacional

#### **TURNO 1: Consulta Inicial - Genérica**

**Usuario pregunta**: "Tela"

**API Responde**:
- **Código**: 5603.00 (47%)
- **Descripción**: Tela sin tejer
- **Missing Fields (3)**:
  - ¿De qué material está hecho? (algodón, poliéster, lana, mezcla, sintético)
  - ¿Es tejido, punto o no tejido?
  - ¿Cuál es el uso final? (prenda de vestir, tela por metro, artículos de hogar)

**UI Muestra**:
- Código: 5603.00 (47%)
- Clasificación pendiente - Necesita más información
- 3 preguntas claras al usuario

---

#### **TURNO 2: Usuario Responde Parcialmente**

**Usuario responde**: "Algodón 100%. Tejido plano"

**API Refina**:
- **Código**: 5208.51 (95%)
- **Descripción**: Tejidos de algodón, 100% algodón, en forma de tela, tejido plano
- **Confianza salta de 47% a 95%** ⬆️
- **Material** identificado: Algodón 100%
- **Tejido** identificado: Plano
- **Sigue pidiendo**: Uso final

**UI Actualiza**:
- Código refina a: 5209.00 (47%)
- Información actualizada sobre tejidos de algodón
- Mantiene pregunta sobre uso final

---

#### **TURNO 3: Usuario Proporciona Último Detalle**

**Usuario responde**: "Para vestimenta"

**API Finaliza**:
- **Código**: 5208.41 (95%)
- **Descripción**: Tejidos de algodón, en bruto, de peso inferior a 200 g/m², para vestimenta
- **Clasificación Completada** ✅
- **Detalles capturados**:
  - Material: Algodón 100%
  - Tipo de tejido: Plano
  - Uso: Vestimenta
  - Peso inferido: <200 g/m²

**UI Muestra**:
- Código **FINAL**: 5208.41 (95%)
- Descripción detallada del producto
- Clasificación lista para comercio

---

### 💡 Por qué es el mejor ejemplo:

✅ **Muestra complejidad real**: 3 turnos naturales  
✅ **Refinamiento progresivo**: 47% → 95%  
✅ **Preguntas relevantes**: Cada pregunta reduce ambigüedad  
✅ **Respuestas realistas**: Usuario no responde todo de una vez  
✅ **Convergencia API/UI**: Ambas llegan al código correcto  
✅ **Especificidad HS8**: Llega a nivel de detalle máximo  

---

---

## 📌 EJEMPLO #2: TUBO (STANDARD DEMO - 2 TURNOS)

**Categoría**: Productos Industriales  
**Complejidad**: Media  
**Turnos**: 2  
**Confianza Final**: 95%  
**Código Final**: 7304.41

### 🎬 Flujo Conversacional

#### **TURNO 1: Consulta Genérica**

**Usuario pregunta**: "Tubo"

**API Responde**:
- **Código**: 7306.90 (45%)
- **Descripción**: Tubería de hierro fundido (genérica)
- **Missing Fields (2)**:
  - ¿Qué material es el tubo? (acero, plástico, cobre, etc.)
  - ¿Cuál es el diámetro y la longitud?

**Observación**: 
- Confianza baja (45%) porque material es determinante
- Capítulo correcto pero muy genérico

---

#### **TURNO 2: Usuario Especifica Material y Dimensión**

**Usuario responde**: "Acero inoxidable. Diámetro 50 mm"

**API Refina**:
- **Código**: 7304.41 (95%)
- **Descripción**: Tuberías de acero inoxidable, con diámetro de 50 mm
- **Confianza salta**: 45% → 95% ⬆️
- **Material identificado**: Acero inoxidable
- **Clasificación específica**: HS8 preciso

**Resultado**:
- ✅ Clasificación definitiva lista
- ✅ Material y dimensiones confirmados
- ✅ Código exportable para arancel

---

### 💡 Por qué es buen ejemplo:

✅ **Flujo rápido**: Solo 2 turnos  
✅ **Material determinante**: Muestra importancia de detalles técnicos  
✅ **Mejora clara**: 45% → 95%  
✅ **Aplicación común**: Productos industriales reales  
✅ **Resultado específico**: HS8 con medidas  

---

---

## 📌 EJEMPLO #3: ACEITE (DEMO CON CORRECCIÓN - 2 TURNOS)

**Categoría**: Productos Industriales  
**Complejidad**: Media  
**Turnos**: 2  
**Confianza Final**: 95%  
**Código Final**: 2710.19

### 🎬 Flujo Conversacional

#### **TURNO 1: Consulta Ambigua**

**Usuario pregunta**: "Aceite"

**API Responde**:
- **Código**: 9999.00 (45%)
- **Descripción**: Clasificación pendiente - Necesita más información
- **Missing Fields (2)**:
  - ¿Qué tipo de aceite? (oliva, girasol, soja, mineral, etc.)
  - ¿Es refinado o en bruto?

**UI Inicialmente confunde**:
- **Código UI**: 1509.10 (45%)
- **Descripción**: Aceites vegetales, otros aceites
- **Error**: Presume aceite vegetal por defecto

---

#### **TURNO 2: Usuario Especifica Origen**

**Usuario responde**: "Aceite mineral"

**API Corrige Correctamente**:
- **Código**: 2710.19 (95%)
- **Descripción**: Aceites minerales, otros aceites, en bruto o refinados
- **Confianza salta**: 45% → 95% ⬆️
- **Capítulo correcto**: 2710 (productos del petróleo)

**UI se Auto-Corrige**:
- **Código UI Final**: 2710.19 (95%)
- **Descripción actualizada** a aceites minerales
- **Convergencia lograda** ✅

---

### 💡 Por qué es útil ejemplo:

✅ **Muestra ambigüedad común**: Aceite puede ser mineral O vegetal  
✅ **Demuestra auto-corrección**: UI corrige su error inicial  
✅ **Diferencia crítica**: Capítulo 15 vs 27 = aranceles muy diferentes  
✅ **Respuesta simple**: Una palabra soluciona ambigüedad  
✅ **Aplicación real**: Producto importado real que requiere precisión  

---

---

## 📌 EJEMPLO #4: GUANTES (DEMO CON MATERIAL - 2 TURNOS)

**Categoría**: Textiles y Calzado  
**Complejidad**: Media  
**Turnos**: 2  
**Confianza Final**: 95%  
**Código Final**: 4203.21

### 🎬 Flujo Conversacional

#### **TURNO 1: Producto Ambiguo**

**Usuario pregunta**: "Guantes"

**API Responde**:
- **Código**: 6116.10 (45%)
- **Descripción**: Guantes de otras telas
- **Missing Fields (2)**:
  - ¿De qué material están hechos? (caucho, tela, cuero, etc.)
  - ¿Son desechables o reutilizables?

---

#### **TURNO 2: Material Determinante**

**Usuario responde**: "Cuero. Reutilizables"

**API Refina**:
- **Código**: 4203.21 (95%)
- **Descripción**: Guantes de cuero, con forro
- **Cambio de capítulo**: 61xx → 42xx (de textil a cuero)
- **Material determinante**: Cuero especifica capítulo diferente

**UI También Corrige**:
- API: 6116.10 → 4203.21
- UI: 6216.00 → 4203.10
- Ambas llegan a capítulo 42 (artículos de cuero)

---

### 💡 Por qué es útil ejemplo:

✅ **Material es determinante**: Cambia de capítulo completamente  
✅ **Dos preguntas claves**: Material + Tipo de uso  
✅ **Convergencia de sistema**: API y UI llegan a código similar  
✅ **Aplicación real**: Importación de prendas de cuero  

---

---

## 📌 EJEMPLO #5: BOMBA (DEMO CON MÚLTIPLES CAMPOS - 2 TURNOS)

**Categoría**: Productos Industriales  
**Complejidad**: Media  
**Turnos**: 2  
**Confianza Final**: 95%  
**Código Final**: 8413.70

### 🎬 Flujo Conversacional

#### **TURNO 1: Producto Muy Genérico**

**Usuario pregunta**: "Bomba"

**API Responde**:
- **Código**: 9999.00 (45%)
- **Descripción**: Clasificación pendiente
- **Missing Fields (3)**:
  - ¿Qué tipo de bomba? (manual, eléctrica, hidráulica)
  - ¿Cuál es el uso? (agua, combustible, neumática)
  - ¿Es nueva o usada?

**Observación**: 3 campos solicitados pero usuario solo responde 2

---

#### **TURNO 2: Usuario Responde Parcialmente**

**Usuario responde**: "Bomba centrífuga. Para agua"

**API Refina Exitosamente**:
- **Código**: 8413.70 (95%)
- **Descripción**: Bombas centrífugas (tipo genérico)
- **Confianza alcanza 95%** aunque faltan datos
- **Capacidad**: Sistema clasifica con información parcial

---

### 💡 Por qué es útil ejemplo:

✅ **Muestra tolerancia**: Clasifica aunque falten algunos campos  
✅ **Múltiples preguntas**: Usuario solo contesta las críticas  
✅ **Eficiencia real**: No requiere todos los detalles  
✅ **Aplicación práctica**: Usuario no siempre sabe todo  

---

---

## 🎥 Script para Presentación

### Minutos 0-2: Introducción (TELA)
"Veamos cómo el sistema clasifica un producto textil sin especificación inicial..."

### Minutos 2-5: Turno 1 (TELA)
"El usuario simplemente dice 'Tela'. El sistema responde con 5603.00 al 47% de confianza..."

### Minutos 5-8: Turno 2 (TELA)
"El usuario proporciona material y tipo de tejido. Observe cómo la confianza sube a 95%..."

### Minutos 8-11: Turno 3 (TELA)
"Con el uso final (vestimenta), llegamos a 5208.41 - ¡HS8 completo!"

### Minutos 11-15: Casos Adicionales
"Veamos otros ejemplos: TUBO (industrial), ACEITE (ambigüedad), GUANTES (material)..."

### Minutos 15-20: Q&A
"¿Preguntas? ¿Quieren ver cómo clasificaría otro producto?"

---

**Archivo generado**: 2026-01-29
