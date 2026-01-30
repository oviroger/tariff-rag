# 📊 ANÁLISIS COMPLETO DE ESTRUCTURA - MEJORAS SUGERIDAS

## 1. 🔴 PROBLEMAS IDENTIFICADOS

### 1.1 RAÍZ DEL PROYECTO (DESORGANIZADA)

```
❌ ARCHIVOS SUELTOS:
├─ .env                               ← Configuración (OK)
├─ .env.example                       ← Configuración (OK)
├─ .tmp_check.py                      ← Archivo temporal NO ORGANIZADO
├─ debug_api.py                       ← Debug script SIN CARPETA
├─ debug_responses.py                 ← Debug script SIN CARPETA
├─ verify_fix.py                      ← Verificación SIN CARPETA
├─ app (rag).zip                      ← Respaldo desorganizado
├─ app.zip                            ← Respaldo desorganizado
├─ app_rag_patched.zip                ← Respaldo desorganizado
├─ ingest_2026.log                    ← Log SUELTA
├─ metrics_output.txt                 ← Salida SUELTA
├─ presentation_output.txt            ← Salida SUELTA
├─ presentation_full.txt              ← Salida SUELTA
├─ test_output.txt                    ← Salida de test SUELTA
├─ test_steel_flow.ps1                ← Script PowerShell SIN CARPETA
├─ test_steel_improved.ps1            ← Script PowerShell SIN CARPETA
├─ test_vehicle_flow.ps1              ← Script PowerShell SIN CARPETA
└─ .pytest_cache/                     ← Cache NO IGNORADA CORRECTAMENTE
```

**Impacto**: Difícil de navegar, mezcla configuración, código, salidas y respaldos.

---

### 1.2 CARPETA `demos/` (MEZCLA DE VERSIONES)

```
❌ PROBLEMAS:
├─ demo_completa.py                  ✅ RECOMENDADA (principal)
├─ demo_rapida.py                    ✅ Alternativa rápida
├─ demo_lavadora.py                  ⚠️  Individual (¿necesaria si existe demo_completa?)
├─ demo_refrigerador.py              ⚠️  Individual (¿necesaria si existe demo_completa?)
├─ demo_automovil.py                 ⚠️  Individual (¿necesaria si existe demo_completa?)
├─ demo_monitor.py                   ⚠️  Individual (¿necesaria si existe demo_completa?)
├─ demo_computadora.py               ❌ DUPLICADA/VERSIÓN ANTIGUA
├─ demo_computadora_v2.py            ❌ VERSIÓN MEJORADA (en raíz, debería estar aquí)
├─ demo_three_cases.py               ❌ VERSIÓN ANTIGUA (similar a demo_completa)
├─ demo_web_lavadora.py              ⚠️  Versión web (¿todavía necesaria?)
├─ demo_web_refrigerador.py          ⚠️  Versión web (¿todavía necesaria?)
├─ demo_web_automovil.py             ⚠️  Versión web (¿todavía necesaria?)
├─ presentation_demo.py              ❌ VERSIÓN ANTIGUA
└─ run_demos_web.py                  ⚠️  Ejecutor (poco usado)
```

**Impacto**: 14 archivos con versiones antiguas, confusión sobre cuál usar.

---

### 1.3 CARPETA `tests/` (MUCHOS DUPLICADOS)

```
❌ PROBLEMAS:
├─ test_api.py                       ✅
├─ final_test.py                     ⚠️  Similar a test_api.py?
├─ test_complete_flow.py             ⚠️  
├─ test_full_flow.py                 ⚠️  Similar a test_complete_flow.py?
├─ test_new_flow.py                  ⚠️  Similar?
├─ test_simple.py                    ⚠️  Muy simple, ¿necesaria?
├─ final_validation_test.py          ⚠️  
├─ test_final_validation.py          ❌ DUPLICADA
├─ test_conversation_isolation.py    ✅
├─ test_turn3.py                     ⚠️  Muy específica
├─ test_turns_3_4.py                 ⚠️  Muy específica
├─ test_evidence_filtering.py        ✅
├─ test_ui_integration.py            ✅
├─ test_ui_isolation.py              ✅
├─ test_year_metadata.py             ✅
├─ test_categories.py                ✅
├─ test_debug.py                     ⚠️  Nombre vago
└─ __init__.py                       ✅
```

**Impacto**: 18 archivos con muchas similitudes, bajo mantenimiento.

---

### 1.4 CARPETA `scripts/` (SIN ORGANIZACIÓN)

```
❌ 27 SCRIPTS SIN CATEGORIZAR:
├─ Ingesta (5): ingest_2026_data.py, ingest_docs.py, ingest_mysql.py, etc.
├─ Inspección (5): inspect_*.py, investigate_*.py
├─ Validación (3): validate_search.py, verify_ingest.py, verify_fix.py
├─ Evaluación (1): eval_ir.py
├─ Inicialización (1): init_index.py
├─ Depuración (3): debug_*.py, temp_inspect.py
├─ Reingestión (2): reingest_*.py
├─ Pruebas (2): test_*.py (¿deberían estar en tests/?)
├─ Otros (3): add_year_*, create_2026_*, preprocess_*
└─ Archivos temporales (2): .tmp_*.py, reingest_*_checkpoint.json
```

**Impacto**: Imposible encontrar scripts específicos.

---

### 1.5 CARPETA `evaluation/` (DESORGANIZADA)

```
evaluación/
├─ Scripts (5): eval_*.py, export_*.py
├─ Datos (8): queries_*.csv, queries_*.txt, test_queries_*
├─ Documentación (6): .md, guías
├─ Subfolder: results/
├─ Subfolder: tools/
├─ Subfolder: templates/
└─ .docx files (3) - ¿Por qué Word aquí?
```

**Impacto**: Mezcla código, datos y documentación.

---

### 1.6 CARPETA `data/` (DESORGANIZADA)

```
data/
├─ afr/                  ← ¿Qué es exactamente?
├─ afr_2025_partes_only/ ← Versión 2025
├─ afr_2026_partes_only/ ← Versión 2026
├─ afr_done/             ← Procesada 2025?
├─ afr_done_2026/        ← Procesada 2026?
├─ afr_done_filtered/    ← Filtrada?
├─ corpus/               ← Corpus del RAG
└─ gold/                 ← Dataset de oro (validación)
```

**Impacto**: No está claro qué versión usar, hay duplicación evidente.

---

### 1.7 ARCHIVOS DE DOCUMENTACIÓN (DISPERSOS)

```
❌ DOCUMENTACIÓN DESORGANIZADA:
├─ RAÍZ: README.md, PRESENTACION_README.md, STRUCTURE.md
├─ RAÍZ: PLAN_MULTI_YEAR.md, GUIDE_MULTI_YEAR.md, YEAR_*.md (3)
├─ RAÍZ: MEJORAS_*.md (2), UI_FIX_SUMMARY.md, SOLUTION_SUMMARY.md
├─ RAÍZ: VERIFICACION.md
├─ docs/: ARQUITECTURA.md, CHECKLIST.md, EXPLICACION_*.md, RESUMEN_*
├─ docs/: Word files (.docx) - ¿Por qué no .md?
├─ evaluation/: README.md, GUIA_*.md, INSTRUCCIONES_*.md, RESUMEN_*
└─ RAÍZ: Partidas_Asgard.sql (¿SQL en raíz?)
```

**Impacto**: Documentación dispersa, difícil mantener coherencia.

---

## 2. ✅ ESTRUCTURA RECOMENDADA

```
tariff-rag/
│
├─ 📋 CONFIGURACIÓN & RAÍZ
│  ├─ .env
│  ├─ .env.example
│  ├─ .gitignore
│  ├─ README.md                    ← Punto de entrada único
│  ├─ requirements.txt
│  ├─ requirements.ui.txt
│  ├─ requirements-test.txt
│  ├─ docker-compose.yml
│  ├─ Dockerfile
│  └─ Partidas_Asgard.sql          ← Datos iniciales
│
├─ 📦 CÓDIGO FUENTE
│  ├─ app/                         ← Lógica del RAG
│  │  ├─ __init__.py
│  │  ├─ api.py                    (80 líneas aprox)
│  │  ├─ chain_rag.py              (lógica principal)
│  │  ├─ chunking.py               (procesamiento)
│  │  ├─ config.py                 (config centralizado)
│  │  ├─ embedder_gemini.py        (embeddings)
│  │  ├─ generator_gemini.py       (generación)
│  │  ├─ retriever_opensearch.py   (búsqueda)
│  │  ├─ rules.py                  (reglas de negocio)
│  │  ├─ schemas.py                (validaciones Pydantic)
│  │  └─ utils/                    ← Utilidades
│  │     ├─ __init__.py
│  │     ├─ guardrails.py
│  │     ├─ metrics.py
│  │     ├─ missing_fields_detector.py
│  │     ├─ device_keywords.json
│  │     └─ ocr_formrec.py
│  │
│  ├─ ui/                          ← Interfaz Gradio
│  │  ├─ __init__.py
│  │  ├─ gradio_app.py             (aplicación web)
│  │  └─ static/                   (si hay CSS/JS)
│  │
│  └─ storage/                     ← Conexiones
│     ├─ __init__.py
│     ├─ opensearch.py             (cliente OpenSearch)
│     ├─ mysql.py                  (cliente MySQL)
│     └─ redis.py                  (cache Redis)
│
├─ 📊 DATOS
│  ├─ raw/                         ← Datos crudos
│  │  ├─ asgard_tariffs/
│  │  │  ├─ 2025_original/
│  │  │  └─ 2026_original/
│  │  └─ documents/
│  │
│  ├─ processed/                   ← Datos procesados
│  │  ├─ 2025/
│  │  │  ├─ asgard_partes.csv
│  │  │  └─ corpus.txt
│  │  └─ 2026/
│  │     ├─ asgard_partes.csv
│  │     └─ corpus.txt
│  │
│  ├─ validation/                  ← Datos de validación
│  │  ├─ gold_standard.csv
│  │  └─ test_queries.csv
│  │
│  └─ indices/                     ← Índices OpenSearch
│     ├─ 2025_metadata.json
│     └─ 2026_metadata.json
│
├─ 🧪 PRUEBAS & VALIDACIÓN
│  ├─ tests/
│  │  ├─ __init__.py
│  │  ├─ unit/                     ← Tests unitarios
│  │  │  ├─ test_chunking.py
│  │  │  ├─ test_guardrails.py
│  │  │  ├─ test_schemas.py
│  │  │  └─ test_rules.py
│  │  │
│  │  ├─ integration/              ← Tests de integración
│  │  │  ├─ test_api.py
│  │  │  ├─ test_full_flow.py
│  │  │  └─ test_conversation.py
│  │  │
│  │  ├─ ui/                       ← Tests UI
│  │  │  ├─ test_ui_integration.py
│  │  │  └─ test_ui_isolation.py
│  │  │
│  │  └─ validation/               ← Tests de validación
│  │     ├─ test_metadata.py
│  │     ├─ test_categories.py
│  │     └─ test_evidence_filtering.py
│  │
│  ├─ demos/                       ← Demostraciones
│  │  ├─ __init__.py
│  │  ├─ demo_complete.py          ← DEMO PRINCIPAL (4 casos)
│  │  ├─ demo_quick.py             ← Demo rápida (3 casos)
│  │  ├─ components/               ← Componentes reutilizables
│  │  │  ├─ __init__.py
│  │  │  ├─ product_demo.py        (clase base)
│  │  │  └─ utils.py
│  │  ├─ products/                 ← Demostraciones por producto
│  │  │  ├─ washing_machine.py     (lavadora)
│  │  │  ├─ refrigerator.py        (refrigerador)
│  │  │  ├─ vehicle.py             (automóvil)
│  │  │  └─ computer.py            (computadora)
│  │  └─ README.md                 (instrucciones)
│  │
│  └─ evaluation/                  ← Evaluación de resultados
│     ├─ eval_retrieval.py
│     ├─ eval_classification.py
│     ├─ eval_operational.py
│     ├─ export_logs.py
│     ├─ data/                     ← Datos de evaluación
│     │  ├─ queries/
│     │  ├─ ground_truth/
│     │  └─ results/
│     ├─ tools/                    ← Herramientas de eval
│     └─ README.md
│
├─ 🛠️ SCRIPTS & MANTENIMIENTO
│  ├─ scripts/
│  │  ├─ ingest/                   ← Ingesta de datos
│  │  │  ├─ __init__.py
│  │  │  ├─ ingest_tariffs.py      (aranceles 2025/2026)
│  │  │  ├─ ingest_documents.py    (documentos)
│  │  │  ├─ ingest_mysql.py        (datos MySQL)
│  │  │  └─ ingest_opensearch.py   (índices OS)
│  │  │
│  │  ├─ maintenance/              ← Mantenimiento
│  │  │  ├─ __init__.py
│  │  │  ├─ init_indices.py        (crear índices)
│  │  │  ├─ reingest_checkpoint.py (reingestión con checkpoint)
│  │  │  ├─ validate_search.py     (validar búsqueda)
│  │  │  └─ rebuild_indices.py     (reconstruir índices)
│  │  │
│  │  ├─ inspection/               ← Inspección/debug
│  │  │  ├─ __init__.py
│  │  │  ├─ inspect_data.py        (inspeccionar datos)
│  │  │  ├─ inspect_indices.py     (inspeccionar índices)
│  │  │  ├─ debug_retrieval.py     (debug búsqueda)
│  │  │  └─ debug_api.py           (debug API)
│  │  │
│  │  └─ migration/                ← Migración de datos
│     ├─ __init__.py
│     ├─ add_year_metadata.py      (agregar año)
│     ├─ migrate_to_2026.py        (migración 2026)
│     └─ backup_restore.py         (backup/restore)
│
├─ 📚 DOCUMENTACIÓN
│  ├─ README.md                    ← Punto de entrada
│  ├─ QUICKSTART.md                ← Inicio rápido
│  ├─ ARCHITECTURE.md              ← Arquitectura técnica
│  ├─ DEPLOYMENT.md                ← Deployment
│  ├─ API_REFERENCE.md             ← Referencia API
│  ├─ TROUBLESHOOTING.md           ← Solución de problemas
│  │
│  └─ guides/                      ← Guías específicas
│     ├─ MULTI_YEAR_SUPPORT.md
│     ├─ FIELD_PRUNING.md
│     ├─ OCR_FORMREC.md
│     ├─ UI_CUSTOMIZATION.md
│     └─ YEAR_FILTERING.md
│
├─ 📁 RESPALDOS & ARCHIVOS LEGACY (OPCIONAL)
│  └─ .backups/
│     ├─ app_v1.zip
│     ├─ app_v2.zip
│     └─ README.md (qué es cada uno)
│
├─ 🐳 DOCKER & DEPLOYMENT
│  ├─ Dockerfile
│  ├─ docker-compose.yml
│  ├─ docker-compose.prod.yml      (si existe)
│  ├─ .dockerignore
│  └─ docker/                      ← Configs si necesario
│
└─ ⚙️ CONFIGURACIÓN & GIT
   ├─ .git/
   ├─ .gitignore
   ├─ .github/
   ├─ .env
   └─ .env.example
```

---

## 3. 🎯 CAMBIOS ESPECÍFICOS RECOMENDADOS

### 3.1 RAÍZ DEL PROYECTO

| Acción | Archivo | Destino |
|--------|---------|---------|
| 🗑️ Eliminar | `.pytest_cache/` | (excepto gitignore) |
| 🗑️ Eliminar | `app*.zip` | `.backups/` o eliminar |
| 🗑️ Eliminar | `.tmp_*.py` | Limpiar |
| 📦 Mover | `debug_api.py` | `scripts/inspection/` |
| 📦 Mover | `debug_responses.py` | `scripts/inspection/` |
| 📦 Mover | `verify_fix.py` | `scripts/maintenance/` |
| 📦 Mover | `test_*.ps1` | `scripts/` o documentar |
| 📦 Mover | `*_output.txt`, `ingest_*.log` | `.logs/` (gitignored) |
| 🔗 Consolidar | Todos los `.md` | Revisar y mover a `docs/` o raíz |

---

### 3.2 CARPETA `demos/`

| Acción | Archivo | Nueva Estructura |
|--------|---------|------------------|
| ✅ Mantener | `demo_complete.py` | `demos/demo_complete.py` (renombrar) |
| ✅ Mantener | `demo_quick.py` | `demos/demo_quick.py` (renombrar) |
| 🗑️ Eliminar | `demo_*.py` individuales | Refactorizar en `components/products/` |
| 🗑️ Eliminar | `demo_web_*.py` | Si no se usan activamente |
| 🗑️ Eliminar | `presentation_demo.py`, `demo_three_cases.py` | Versiones antiguas |
| 🗑️ Eliminar | `demo_computadora_v2.py` | Versión antigua (está en raíz) |
| 📁 Crear | `demos/components/` | Para código reutilizable |
| 📁 Crear | `demos/products/` | Una demo por producto |
| 📝 Crear | `demos/README.md` | Instrucciones de uso |

**Nuevo contenido demos/**:
```
demos/
├─ demo_complete.py          ← 4 casos (renombrada)
├─ demo_quick.py             ← 3 casos (renombrada)
├─ components/
│  ├─ __init__.py
│  ├─ base.py                (clase ProductDemo base)
│  └─ utils.py               (helpers)
├─ products/
│  ├─ __init__.py
│  ├─ washing_machine.py     (lavadora)
│  ├─ refrigerator.py        (refrigerador)
│  ├─ vehicle.py             (automóvil)
│  └─ computer.py            (computadora)
└─ README.md
```

---

### 3.3 CARPETA `tests/`

| Acción | Archivo | Nueva Ubicación |
|--------|---------|-----------------|
| 📁 Crear | `tests/unit/` | Tests unitarios |
| 📁 Crear | `tests/integration/` | Tests de integración |
| 📁 Crear | `tests/ui/` | Tests UI |
| 📁 Crear | `tests/validation/` | Tests de validación |
| ✅ Mantener | `test_api.py` | `tests/integration/` |
| ✅ Mantener | `test_full_flow.py` | `tests/integration/` |
| ✅ Mantener | `test_conversation_isolation.py` | `tests/integration/` |
| 🗑️ Eliminar | `final_test.py` | Duplicada de test_api.py |
| 🗑️ Eliminar | `test_final_validation.py` | Duplicada de final_validation_test.py |
| 🗑️ Unificar | `test_complete_flow.py`, `test_full_flow.py`, `test_new_flow.py` | Mantener una versión |
| 🗑️ Eliminar | `test_turn3.py`, `test_turns_3_4.py` | Muy específicas |
| 📝 Crear | `tests/README.md` | Guía de pruebas |
| 📝 Crear | `conftest.py` | Configuración pytest |

---

### 3.4 CARPETA `scripts/`

| Acción | Script | Nueva Ubicación |
|--------|--------|-----------------|
| 📁 Crear | `scripts/ingest/` | Ingesta de datos |
| 📁 Crear | `scripts/maintenance/` | Mantenimiento |
| 📁 Crear | `scripts/inspection/` | Inspección/debug |
| 📁 Crear | `scripts/migration/` | Migración de datos |
| 📝 Crear | `scripts/README.md` | Índice de scripts |

**Mapeo**:
- `ingest_*.py` → `scripts/ingest/`
- `reingest_*.py` → `scripts/maintenance/`
- `inspect_*.py`, `debug_*.py`, `investigate_*.py` → `scripts/inspection/`
- `validate_*.py`, `verify_*.py` → `scripts/maintenance/`
- `init_*.py`, `create_2026_*.py` → `scripts/maintenance/`
- `add_year_*.py` → `scripts/migration/`
- `eval_ir.py` → `evaluation/` (es evaluación, no script)

---

### 3.5 CARPETA `data/`

| Acción | Carpeta | Nueva Estructura |
|--------|---------|-----------------|
| 📁 Crear | `data/raw/` | Datos originales |
| 📁 Crear | `data/processed/` | Datos procesados |
| 📁 Crear | `data/validation/` | Datos de validación |
| 📁 Crear | `data/indices/` | Metadatos de índices |
| 📦 Mover | `afr/*` → `data/raw/asgard_tariffs/` | Reorganizar |
| 📝 Crear | `data/README.md` | Documentación de datos |
| 🔗 Consolidar | `corpus/` y duplicados | Versiones 2025/2026 separadas |

---

### 3.6 CARPETA `evaluation/`

| Acción | Contenido | Nueva Ubicación |
|--------|-----------|-----------------|
| 📁 Crear | `evaluation/data/` | Datos de evaluación |
| 📁 Crear | `evaluation/tools/` | Ya existe - OK |
| 📁 Crear | `evaluation/results/` | Ya existe - OK |
| 📝 Mover | `.docx` files | `docs/` o convertir a `.md` |
| 📝 Crear | `evaluation/README.md` | Guía de evaluación |

---

### 3.7 DOCUMENTACIÓN

| Acción | Archivo | Nueva Ubicación |
|--------|---------|-----------------|
| 📄 Consolidar | Todos los `.md` en raíz | Organizar en `docs/` |
| 📝 Crear | `docs/guides/` | Guías específicas |
| 📝 Crear | `README.md` (raíz) | Punto de entrada único |
| 📝 Crear | `QUICKSTART.md` | Inicio rápido |
| 📝 Crear | `ARCHITECTURE.md` | Arquitectura técnica |
| 📝 Crear | `API_REFERENCE.md` | Referencia API |
| 🗑️ Eliminar | Documentos Word (.docx) | Convertir a Markdown |
| 🔗 Consolidar | `YEAR_DISPLAY_IN_UI.md`, `YEAR_FILTERING_SOLUTION.md` | `docs/guides/YEAR_SUPPORT.md` |

---

## 4. 🚀 PLAN DE IMPLEMENTACIÓN

### Fase 1: Preparación (15 min)
1. ✅ Crear estructura de directorios recomendada
2. ✅ Crear archivos `.gitignore` actualizados
3. ✅ Documentar cambios en `MIGRATION_PLAN.md`

### Fase 2: Reorganización de Código (1 hora)
1. Mover `app/` a nueva estructura
2. Mover `ui/` a nueva estructura
3. Mover `scripts/` a subdirectorios
4. Refactorizar `demos/`
5. Refactorizar `tests/`

### Fase 3: Reorganización de Datos (30 min)
1. Mover `data/` a `data/raw/`, `data/processed/`, etc.
2. Documentar cada carpeta

### Fase 4: Consolidación de Documentación (30 min)
1. Consolidar `.md` files
2. Actualizar referencias en código
3. Convertir `.docx` a `.md`

### Fase 5: Limpieza (15 min)
1. Eliminar archivos duplicados
2. Limpiar archivos temporales
3. Actualizar `.gitignore`

### Fase 6: Testing & Validación (45 min)
1. Ejecutar todos los tests
2. Verificar imports
3. Verificar Docker build
4. Commit final

---

## 5. 📋 IMPACTO DE LOS CAMBIOS

### Beneficios
✅ Navegación mucho más clara
✅ Mantenimiento facilitado
✅ Onboarding de nuevos desarrolladores
✅ Escalabilidad mejorada
✅ Estándares de industria seguidos

### Riesgos (Mitigables)
⚠️ Hay que actualizar imports en todo el código
⚠️ Cambios en rutas de archivos de datos
⚠️ Posibles conflictos en Docker

### Esfuerzo Estimado
- **Total**: ~3-4 horas de trabajo
- **Automatable**: ~60% (scripts)
- **Manual**: ~40% (validación, actualización imports)

---

## 6. 🎯 PRÓXIMOS PASOS

1. **¿Deseas que implemente esta estructura?**
   - Opción A: Implementación completa (3-4 horas)
   - Opción B: Implementación por fases
   - Opción C: Solo reorganización de carpetas sin refactoring

2. **¿Qué prioridad?**
   - Limpiar raíz del proyecto (rápido, alto impacto)
   - Organizar `demos/` y `tests/` (mejora claridad)
   - Reorganizar `scripts/` (mejora mantenimiento)
   - Consolidar documentación (mejora UX)

3. **Consideraciones**
   - ¿Mantener respaldos `.zip`? (podrían moverse a `.backups/`)
   - ¿Mantener archivos PS1 de prueba?
   - ¿Estandarizar todo a Markdown (eliminar `.docx`)?

---

**¿Cuál es tu preferencia? 🎯**
