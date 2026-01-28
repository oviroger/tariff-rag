# 📁 ESTRUCTURA ORGANIZADA DEL PROYECTO

```
tariff-rag/
│
├─ 📂 demos/                              ← Scripts de DEMOSTRACIÓN
│  │
│  ├─ 📋 DEMOSTRACIONES PRINCIPALES
│  │  ├─ demo_completa.py                ✅ 4 casos (RECOMENDADA)
│  │  ├─ demo_rapida.py                  ✅ 3 casos rápido
│  │  ├─ demo_lavadora.py                ✅ Electrodoméstico 1
│  │  ├─ demo_refrigerador.py            ✅ Electrodoméstico 2
│  │  ├─ demo_automovil.py               ✅ Vehículo (Contraste)
│  │  └─ demo_monitor.py                 ✅ Equipo informático
│  │
│  ├─ 🌐 DEMOS WEB (Interactivas)
│  │  ├─ demo_web_lavadora.py            🌐 Con colores ANSI
│  │  ├─ demo_web_refrigerador.py        🌐 Con colores ANSI
│  │  ├─ demo_web_automovil.py           🌐 Con colores ANSI
│  │  └─ run_demos_web.py                🌐 Ejecutor de demos
│  │
│  └─ 🎬 OTRAS DEMOSTRACIONES
│     ├─ demo_computadora.py
│     ├─ demo_computadora_v2.py
│     ├─ demo_three_cases.py
│     └─ presentation_demo.py
│
├─ 📂 tests/                              ← Scripts de PRUEBA/TEST
│  │
│  ├─ 🔍 Tests de API
│  │  ├─ test_api.py
│  │  └─ final_test.py
│  │
│  ├─ 🔄 Tests de Flujo
│  │  ├─ test_complete_flow.py
│  │  ├─ test_full_flow.py
│  │  ├─ test_new_flow.py
│  │  └─ test_complete_flow.py
│  │
│  ├─ 💬 Tests de Conversación
│  │  ├─ test_conversation_isolation.py
│  │  ├─ test_turn3.py
│  │  └─ test_turns_3_4.py
│  │
│  ├─ 🧪 Tests de Validación
│  │  ├─ final_validation_test.py
│  │  ├─ test_final_validation.py
│  │  ├─ test_evidence_filtering.py
│  │  └─ test_simple.py
│  │
│  ├─ 🖥️  Tests de UI
│  │  ├─ test_ui_integration.py
│  │  └─ test_ui_isolation.py
│  │
│  └─ 📅 Tests de Metadata
│     ├─ test_year_metadata.py
│     ├─ test_categories.py
│     └─ test_debug.py
│
├─ 📄 PRESENTACION_README.md              ← Guía de ejecución
├─ 📄 README.md                           ← Descripción del proyecto
├─ 📂 app/                                ← Código de la aplicación
├─ 📂 ui/                                 ← Interfaz Gradio
├─ 📂 docs/                               ← Documentación
└─ ... (otros archivos)

```

## 🚀 EJECUCIÓN RÁPIDA

### Demostración Completa (RECOMENDADA)
```bash
cd "d:\MAESTRIA - copia\tariff-rag"
python demos/demo_completa.py
```
✅ Muestra 4 casos: Lavadora, Refrigerador, Automóvil, Monitor
⏱️ Duración: ~2 minutos

### Demostración Rápida
```bash
python demos/demo_rapida.py
```
✅ Muestra 3 casos: Lavadora, Refrigerador, Automóvil
⏱️ Duración: ~1 minuto

### Demo Individual
```bash
python demos/demo_lavadora.py
python demos/demo_refrigerador.py
python demos/demo_automovil.py
python demos/demo_monitor.py
```

### Ejecutar Tests
```bash
# Test de API
python tests/test_api.py

# Test completo de flujo
python tests/test_complete_flow.py

# Test de UI
python tests/test_ui_integration.py
```

## 📊 RESUMEN DE ARCHIVOS

| Carpeta | Cantidad | Propósito |
|---------|----------|-----------|
| **demos/** | 14 | Demostraciones para presentación |
| **tests/** | 22 | Pruebas unitarias y de integración |
| **app/** | 15 | Código backend (API, RAG, etc.) |
| **ui/** | 1 | Interfaz Gradio |
| **docs/** | 6+ | Documentación del proyecto |

## ✨ CARACTERÍSTICAS

- ✅ **Demostración de 4 productos** mostrando inteligencia contextual
- ✅ **Field Pruning inteligente**: No sugiere campos inapropiados
- ✅ **Refinamiento progresivo** de códigos arancelarios
- ✅ **Multi-turno conversacional** con contexto persistente
- ✅ **RAG + LLM** para clasificación precisa
- ✅ **22 tests** validando funcionalidad del sistema

## 📝 NOTA

Para información detallada sobre cada demostración, ver [PRESENTACION_README.md](PRESENTACION_README.md)

---

**Última actualización**: Enero 27, 2026  
**Estado**: ✅ Sistema listo para presentación
