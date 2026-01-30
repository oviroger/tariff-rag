# GUÍA DE USO - CHATBOT DE CLASIFICACIÓN ARANCELARIA

**Versión**: 1.0  
**Fecha**: 28 de enero de 2026  
**Estado**: ✅ Operativo

---

## 🚀 Inicio Rápido

### Requisitos Previos

- Docker y Docker Compose instalados
- Python 3.11+
- Acceso a Azure OpenAI (credenciales configuradas)

### Iniciar el Sistema

```bash
cd "d:\MAESTRIA - copia\tariff-rag"

# Iniciar todos los contenedores
docker-compose up -d

# Esperar 120 segundos para que todo esté listo
Start-Sleep -Seconds 120

# Verificar que el API está disponible
curl http://localhost:8000/health
```

### Acceder a la Interfaz

1. **Gradio UI** (Interfaz Gráfica):
   - URL: http://localhost:7860
   - Abrir en navegador web
   - Conversación interactiva con el chatbot

2. **OpenSearch Dashboards** (Índices):
   - URL: http://localhost:5601
   - Ver documentos indexados
   - Inspeccionar búsquedas

3. **API REST** (Integración):
   - URL: http://localhost:8000
   - Endpoint: POST /classify
   - Documentación: http://localhost:8000/docs

---

## 💬 Cómo Usar el Chatbot

### Flujo de Conversación Típico

#### Ejemplo 1: Clasificación de Vehículo

**Paso 1: Consulta Inicial**
```
Usuario escribe:
"Quiero importar un vehículo"

Sistema responde:
✓ Código Propuesto: 9999.00 (Clasificación Pendiente)
✓ Confianza: 42.7%
✓ Preguntas:
  - ¿Cuántas personas puede transportar?
  - ¿Qué tipo de motor tiene?
```

**Paso 2: Proporcionar Más Información**
```
Usuario escribe:
"Es para 50 personas, tipo autobús"

Sistema responde:
✓ Código Actualizado: 8702.20
✓ Confianza: 52.2% ⬆️
✓ Información Identificada:
  - Autobús (≥10 personas)
  - Motor diésel
```

**Paso 3: Completar Detalles**
```
Usuario escribe:
"Motor diesel, nuevo, cilindrada mayor a 3500 cc"

Sistema responde:
✓ CÓDIGO FINAL: 8702.20.90.10 ✅
✓ Confianza: 95.0% ⭐
✓ Descripción: Autobús nuevo con motor diésel
✓ Evidencia: 5 documentos del capítulo 87
```

#### Ejemplo 2: Clasificación de Electrónica

**Paso 1: Descripción General**
```
Usuario: "Tengo un horno microondas inteligente"
Sistema: Código 8516.60, Confianza 45%
```

**Paso 2: Especificar Características**
```
Usuario: "Tiene convección integrada, 1000 watts"
Sistema: Código 8516.60, Confianza 55%
```

**Paso 3: Confirmar Condición**
```
Usuario: "Es nuevo, original, empacado"
Sistema: Código 8516.60, Confianza 65% ✅
```

#### Ejemplo 3: Clasificación de Textil

**Paso 1: Categoría**
```
Usuario: "Voy a importar ropa de algodón"
Sistema: Código 9999.00, Confianza 45%
```

**Paso 2: Tipo de Prenda**
```
Usuario: "Son camisetas t-shirt, manga corta"
Sistema: Código 6109.10, Confianza 45%
```

**Paso 3: Detalles del Material**
```
Usuario: "100% algodón, punto fino, 5000 unidades"
Sistema: Código 6109.10, Confianza 45% ✅
```

---

## 🔧 Opciones y Parámetros

### Parámetros de Consulta

#### En la Interfaz Gradio

| Parámetro | Descripción | Ejemplo |
|-----------|-----------|---------|
| **Pregunta** | Tu consulta de clasificación | "Vehículo para 50 personas" |
| **Años** | Años arancelarios a consultar | 2025, 2026 |
| **Top K** | Número de candidatos mostrados | 3 (default: 5) |

#### En el API REST

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Vehículo para 50 personas, motor diesel",
    "top_k": 5,
    "years": [2025, 2026]
  }'
```

**Respuesta**:
```json
{
  "top_candidates": [{
    "code": "8702.20.90.10",
    "description": "Autobús nuevo...",
    "confidence": 0.95,
    "level": "NATIONAL10",
    "years": [2025, 2026]
  }],
  "evidence": [
    {
      "fragment_id": "...",
      "score": 0.0164,
      "text": "Documento de OpenSearch...",
      "year": 2026
    }
  ],
  "missing_fields": [],
  "conversation_id": "..."
}
```

---

## 📊 Entender los Resultados

### Campo: Confianza (Confidence)

```
0-30%:   Baja confianza - Información incompleta
         Usuario debe proporcionar más datos
         
30-60%:  Confianza media - Clasificación tentativa
         Puede refinarse con más información
         
60-85%:  Buena confianza - Clasificación confiable
         La mayoría de características están claras
         
85-100%: Muy alta confianza - Clasificación precisa
         Todos los detalles están especificados
```

### Campo: Evidencia (Evidence)

Cada documento muestra:
- **fragment_id**: Identificador único
- **score**: Puntuación de relevancia (0-1)
- **text**: Fragmento del documento
- **doc_id**: Documento de origen
- **year**: Año arancelario (2025 o 2026)
- **reason**: Por qué se incluyó

### Campo: Missing Fields (Información Faltante)

El sistema indica qué información necesita para mejorar la clasificación:

```
Ejemplos:
- "¿Es nuevo o usado?"
- "¿Cuál es la potencia en watts?"
- "¿Es para transporte de personas o carga?"
```

---

## 🎯 Mejores Prácticas

### ✅ Que SÍ hacer

1. **Ser específico en la descripción**
   ```
   ✅ BIEN: "Vehículo para 50 personas, motor diesel, nuevo"
   ❌ MAL: "Vehículo"
   ```

2. **Proporcionar información gradualmente**
   ```
   Turno 1: Tipo general
   Turno 2: Características principales
   Turno 3: Detalles específicos
   ```

3. **Usar términos arancelarios cuando sea posible**
   ```
   ✅ BIEN: "Motor diesel", "100% algodón"
   ❌ MAL: "Motor que quema diésel", "Tela de algodón puro"
   ```

4. **Especificar cantidades y medidas**
   ```
   ✅ BIEN: "5000 unidades", "1000 watts", "3500 cc"
   ❌ MAL: "Muchos", "Mucho poder", "Cilindrada grande"
   ```

### ❌ Que NO hacer

1. **No proporcionar información irrelevante**
   ```
   ❌ MAL: "Es color rojo, con pegatinas de flores"
   ✅ BIEN: "Es nuevo, color no especificado"
   ```

2. **No usar abreviaturas confusas**
   ```
   ❌ MAL: "Para 50 pax, cc 2000, MCH"
   ✅ BIEN: "Para 50 personas, 2000 cilindrada, motor diesel"
   ```

3. **No cambiar radicalmente el tema entre turnos**
   ```
   ❌ MAL: Turno 1: "Auto"
           Turno 2: "En realidad es un barco"
   ✅ BIEN: Mantener el mismo producto
   ```

---

## 🔍 Casos de Uso Comunes

### Caso 1: Importador de Vehículos

```
Pregunta: "Autos sedán, gasolina, 1500 cc, nuevo"
Respuesta: 8703.21
```

### Caso 2: Distribuidor de Electrónica

```
Pregunta: "Laptop i7, 16GB RAM, SSD 512GB, nueva"
Respuesta: 8471.30
```

### Caso 3: Empresa Textil

```
Pregunta: "Jeans, algodón 100%, talla S-XXL, 1000 piezas"
Respuesta: 6204.62
```

### Caso 4: Importador de Maquinaria

```
Pregunta: "Bomba hidráulica, capacidad 100 l/min, nueva"
Respuesta: 8413.81
```

---

## ⚙️ Configuración Avanzada

### Cambiar Años de Consulta

```bash
# Por defecto: [2025, 2026]
# Personalizar:
"years": [2025]      # Solo 2025
"years": [2026]      # Solo 2026
"years": [2025, 2026] # Ambos
```

### Aumentar Número de Candidatos

```bash
# Por defecto: top_k = 5
# Personalizar:
"top_k": 10  # Mostrar hasta 10 códigos alternativos
```

### Iniciar Nueva Conversación

```bash
# Cada consulta sin conversation_id inicia nueva conversación
# Mantener conversación:
"conversation_id": "abc123..."  # Reutilizar ID
```

---

## 🐛 Solucionar Problemas

### Problema: "Confianza muy baja (0-30%)"

**Causa**: Información insuficiente

**Solución**:
1. Proporcionar más detalles en siguiente turno
2. Responder las preguntas del sistema
3. Ser más específico

```
Turno 1: "Vehículo" → 9999.00 (0%)
Turno 2: "Para 50 personas, motor diesel" → 8702.20 (95%)
```

### Problema: "Código 9999.00 (Clasificación Pendiente)"

**Causa**: Sistema no puede determinar código

**Solución**:
1. Proporcionar capacidad (para vehículos)
2. Especificar tipo de producto
3. Indicar material principal

```
Turno 1: "Microondas" → 9999.00
Turno 2: "Uso doméstico, 1000 watts, nueva" → 8516.60 ✓
```

### Problema: "Sin documentos encontrados"

**Causa**: OpenSearch no retorna resultados

**Solución**:
1. Usar términos más genéricos
2. Describir qué es el producto
3. Especificar categoría principal

```
❌ "Láser RGB 50mW modelo XYZ"
✅ "Láser rojo clase 3B, 50mW"
```

### Problema: "API no disponible"

**Causa**: Contenedor no inició correctamente

**Solución**:
```bash
# Verificar estado
docker ps

# Ver logs
docker logs rag-api --tail 50

# Reiniciar
docker-compose restart rag-api
```

---

## 📱 Integración con Sistemas Externos

### Ejemplo Python

```python
import requests
import json

API_URL = "http://localhost:8000/classify"

def clasificar_producto(descripcion: str):
    response = requests.post(
        API_URL,
        json={
            "user_query": descripcion,
            "top_k": 5,
            "years": [2025, 2026]
        }
    )
    
    result = response.json()
    
    if result['top_candidates']:
        codigo = result['top_candidates'][0]['code']
        confianza = result['top_candidates'][0]['confidence']
        print(f"Código: {codigo} (Confianza: {confianza*100:.1f}%)")
    
    return result

# Uso
resultado = clasificar_producto("Vehículo para 50 personas, motor diesel")
```

### Ejemplo JavaScript

```javascript
async function clasificar(descripcion) {
    const response = await fetch('http://localhost:8000/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_query: descripcion,
            top_k: 5,
            years: [2025, 2026]
        })
    });
    
    const data = await response.json();
    return data.top_candidates[0];
}

// Uso
const resultado = await clasificar('Vehículo para 50 personas');
console.log(`Código: ${resultado.code}`);
```

---

## 📞 Soporte

### Documentación Disponible

- `RESUMEN_EJECUTIVO_RESOLUCION.md` - Cambios implementados
- `PRUEBAS_INTERACTIVAS_DETALLADAS.md` - Casos de prueba
- `DEMOSTRACION_VISUAL_SOLUCION.md` - Visualización del flujo
- `EJEMPLOS_CLASIFICACION_DETALLADOS.md` - Ejemplos detallados

### Archivos de Configuración

- `.env` - Variables de entorno
- `docker-compose.yml` - Configuración de contenedores
- `app/config.py` - Parámetros de la aplicación

### Logs y Debugging

```bash
# Ver logs en tiempo real
docker-compose logs -f rag-api

# Ver logs específicos
docker logs rag-api | grep ERROR

# Health check
curl http://localhost:8000/health
```

---

## ✅ Checklist de Validación

Antes de usar en producción:

- [ ] Docker Compose está corriendo (`docker ps` muestra 7 contenedores)
- [ ] API responde a health check (`curl http://localhost:8000/health`)
- [ ] OpenSearch tiene documentos indexados
- [ ] Pruebas unitarias pasan (`python test_improved_search.py`)
- [ ] Pruebas multi-turno exitosas (`python test_detailed_interactions.py`)
- [ ] Confianza > 80% en casos de prueba

---

**¡Listo para usar!** 🎉

