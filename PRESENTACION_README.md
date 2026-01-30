# 🎬 DEMOSTRACIÓN FINAL - SISTEMA TARIFF RAG

## Descripción General

Este conjunto de tres demostraciones presenta el sistema de clasificación automática de códigos arancelarios HS utilizando RAG (Retrieval-Augmented Generation) y LLM.

**Objetivo**: Mostrar cómo el sistema:
1. ✅ Clasifica productos con progresiva refinación
2. ✅ Mantiene contexto conversacional multi-turno
3. ✅ Sugiere campos contextualmente relevantes
4. ✅ Prúa inteligentemente campos inapropiados según el tipo de producto

---

## 🚀 Pre-requisitos

```bash
# Verificar que los servicios estén corriendo
docker compose ps

# Esperado:
# ✓ rag-api     (puerto 8000)
# ✓ rag-ui      (puerto 7860)
# ✓ redis       (puerto 6379)
# ✓ opensearch  (puerto 9200)
```

Si algún servicio está detenido:
```bash
docker compose up -d
```

---

## 📋 DEMO 1: LAVADORA (Electrodoméstico)

### Propósito
Demostrar la clasificación de un electrodoméstico simple con progresión de refinamiento de código.

### Ejecución
```bash
cd "d:\MAESTRIA - copia\tariff-rag"
python demos/demo_lavadora.py
```

### Qué observar

| Turno | Input | Código Esperado | Confianza | Observación |
|-------|-------|-----------------|-----------|-------------|
| 1 | "Quiero importar un electrodoméstico" | 8509.80 (genérico) | ~43% | Inicial - código amplio |
| 2 | "Es una lavadora de ropa automática" | 8450.11 (específico) | ~78% | Se refina con 'lavadora' |
| 3 | "Tiene función de secado, voltaje 220V" | 8450.11.10 (detallado) | ~90% | Máximo refinamiento |

### Campos sugeridos esperados ✅
- ✓ Función de secado o solo lavado
- ✓ Voltaje/Frecuencia (110/220V, 50/60Hz)
- ✓ Uso doméstico o industrial
- ✓ Condición (nuevo/usado)
- ✓ Capacidad de carga

### Campos que NO deben aparecer ❌
- ❌ Tipo de motor (gasolina/diesel/eléctrico)
- ❌ Cilindrada del motor
- ❌ Número de pasajeros
- ❌ Tracción del vehículo
- ❌ Tipo de eje/suspensión

---

## 📋 DEMO 2: REFRIGERADOR (Electrodoméstico)

### Propósito
Demostrar que el sistema maneja múltiples tipos de electrodomésticos con el mismo nivel de inteligencia.

### Ejecución
```bash
python demos/demo_refrigerador.py
```

### Qué observar

| Turno | Input | Código Esperado | Confianza | Observación |
|-------|-------|-----------------|-----------|-------------|
| 1 | "Necesito clasificar equipo de refrigeración" | 8418.xx (genérico) | ~35% | Inicial - categoría ancha |
| 2 | "Es un refrigerador-congelador estándar" | 8418.10 (específico) | ~72% | Se refina con tipo de equipo |
| 3 | "300L, sistema no-frost, 10kg/24h congelación" | 8418.1010 (detallado) | ~85% | Refinamiento con specs |

### Campos sugeridos esperados ✅
- ✓ Volumen/Capacidad (litros)
- ✓ Sistema de congelación (no-frost, frost)
- ✓ Capacidad de congelación (kg/24h)
- ✓ Voltaje/Frecuencia
- ✓ Uso doméstico o comercial

### Validación de inteligencia contextual 🧠
Este ejemplo valida que:
- El sistema detecta "refrigerador" como electrodoméstico
- Automáticamente prúa campos de vehículos
- NO incluye "motor", "cilindrada", "pasajeros"

---

## 📋 DEMO 3: AUTOMÓVIL (Vehículo)

### Propósito
**Contrastar con DEMO 1 y 2**: Mostrar que el sistema SÍ sugiere campos de vehículos cuando es apropiado.

**Objetivo pedagógico**: Validar que el pruning es inteligente, no ciego.

### Ejecución
```bash
python demo_automovil.py
```

### Qué observar

| Turno | Input | Código Esperado | Confianza | Observación |
|-------|-------|-----------------|-----------|-------------|
| 1 | "Quiero importar un vehículo" | 8704.xx (genérico) | ~40% | Inicial - categoría ancha |
| 2 | "Es un automóvil sedán compacto" | 8704.21 (específico) | ~75% | Se refina con tipo |
| 3 | "Gasolina, 1600cc, 4 cil, 4 puertas, 5 pas." | 8704.21xx (detallado) | ~88% | Máximo refinamiento |

### Campos sugeridos esperados ✅ (DIFERENTE A DEMO 1 Y 2)
- ✓ **Tipo de motor (gasolina/diesel)** ← APARECE (apropiado)
- ✓ **Cilindrada del motor** ← APARECE (apropiado)
- ✓ **Número de plazas/pasajeros** ← APARECE (apropiado)
- ✓ Tracción (delantera/trasera/integral)
- ✓ Número de ejes
- ✓ Sistema de frenos

### Validación de inteligencia contextual 🧠
Este ejemplo valida que:
- El sistema detecta "automóvil" como vehículo
- **NO prúa** campos de vehículos (a diferencia de DEMO 1 y 2)
- **SÍ sugiere** "tipo de motor", "cilindrada", "pasajeros"

---

## 📊 Comparativa de Resultados

```
CARACTERÍSTICA          DEMO 1 (Lavadora)  DEMO 2 (Refrigerador)  DEMO 3 (Automóvil)
Categoría              Electrodoméstico    Electrodoméstico        Vehículo
Tipo de motor          ❌ NO aparece       ❌ NO aparece           ✅ SÍ aparece
Cilindrada             ❌ NO aparece       ❌ NO aparece           ✅ SÍ aparece
Pasajeros              ❌ NO aparece       ❌ NO aparece           ✅ SÍ aparece
Voltaje/Frecuencia     ✅ SÍ aparece       ✅ SÍ aparece           ❌ NO aparece
Progresión de código   8509→8450→8450.11   8418→8418.10→8418.10xx  8704→8704.21→8704.21xx
Confianza final        ~90%                ~85%                    ~88%
```

---

## 🔧 Troubleshooting

### Error: "No se puede conectar a localhost:8000"
```bash
# Verificar que la API está corriendo
docker compose logs rag-api

# Si no está corriendo
docker compose restart rag-api
```

### Error: "Connection timeout en Redis"
```bash
# Reiniciar Redis
docker compose restart redis

# Verificar que está escuchando
docker compose exec redis redis-cli PING
```

### Error: "Respuestas vacías o códigos None"
```bash
# Verificar logs de OpenSearch
docker compose logs opensearch

# Reiniciar todo
docker compose down && docker compose up -d

# Esperar 30 segundos a que todo inicie
```

---

## 📝 Notas Importantes

1. **Orden de ejecución**: Se recomienda ejecutar en orden: Demo 1 → Demo 2 → Demo 3 → Demo 4
   - Cada una muestra progresivamente más complejidad
   - La comparativa es más impactante en este orden

2. **Conversaciones independientes**: Cada script usa un `conversation_id` único
   - Las demostraciones son independientes
   - No interferirán entre sí

3. **Redis persiste el historial**: Si ejecutas la misma demo dos veces
   - La segunda tendrá mejor confianza (más contexto)
   - Es esperado y demuestra que el sistema aprende

4. **Tiempos de espera**: Hay pausas entre turnos
   - Permite leer salidas cómodamente
   - Evita cargas simultáneas en OpenSearch

---

## 🔧 Troubleshooting

### Error: "No se puede conectar a localhost:8000"
```bash
# Verificar que la API está corriendo
docker compose logs api

# Si no está corriendo
docker compose restart api
```

## 🎯 Puntos clave para la presentación

### 1️⃣ **Inteligencia Contextual**
> "El sistema no solo clasifica - entiende el contexto. Por eso sabe qué preguntas hacer."

**Demostraciones**:
- Demo 1-2: NO pregunta sobre motor de un electrodoméstico
- Demo 3: SÍ pregunta sobre motor de un automóvil

### 2️⃣ **Refinamiento Progresivo**
> "Conforme el usuario proporciona más detalles, el código se especializa y la confianza sube."

**Métricas**:
- Demo 1: 43% → 78% → 90%
- Demo 2: 35% → 72% → 85%
- Demo 3: 40% → 75% → 88%

### 3️⃣ **RAG + LLM + Guardrails**
> "Cada componente trabaja junto para garantizar clasificaciones acertadas."

**Componentes visibles**:
- RAG: Recupera fragmentos de contexto de códigos relacionados
- LLM: Genera clasificación con confianza y reasoning
- Guardrails: Valida que los campos sugeridos sean relevantes

---

## 📂 Archivos de la demostración

```
tariff-rag/
├── demos/                    ← Scripts de demostración
│   ├── demo_lavadora.py       → DEMO 1: Electrodoméstico simple
│   ├── demo_refrigerador.py   → DEMO 2: Electrodoméstico complejo
│   ├── demo_automovil.py      → DEMO 3: Vehículo (contraste)
│   ├── demo_monitor.py        → DEMO 4: Equipo informático
│   ├── demo_rapida.py         → Versión rápida (3 productos)
│   ├── demo_completa.py       → Versión completa (4 productos)
│   ├── demo_web_lavadora.py   → Demo interactiva
│   ├── demo_web_refrigerador.py → Demo interactiva
│   ├── demo_web_automovil.py  → Demo interactiva
│   ├── run_demos_web.py       → Ejecutor de demos
│   └── presentation_demo.py    → Demo para presentación
│
├── tests/                    ← Scripts de prueba
│   ├── test_api.py
│   ├── test_complete_flow.py
│   ├── test_conversation_isolation.py
│   ├── test_ui_integration.py
│   └── ... (más tests)
│
└── PRESENTACION_README.md ← Este archivo
```

---

## ✅ Checklist pre-presentación

- [ ] Verificar que `docker compose ps` muestra todos los servicios en `Up`
- [ ] Ejecutar `python demos/demo_completa.py` (demostración completa con 4 casos)
- [ ] O ejecutar demos individuales: `python demos/demo_lavadora.py`, etc.
- [ ] Limpiar terminal
- [ ] Tener abierto el documento de arquitectura (`docs/ARQUITECTURA.md`)
- [ ] Opcional: Tener abierto el UI en `http://localhost:7860` para demostr. interactiva

---

## 🚀 Ejecución rápida

```bash
# Demostración completa (RECOMENDADA)
cd "d:\MAESTRIA - copia\tariff-rag"
python demos/demo_completa.py

# Demostración rápida
python demos/demo_rapida.py

# Demo individual
python demos/demo_lavadora.py
```

---

**Última actualización**: Enero 27, 2026
**Estado**: ✅ Listo para presentación
