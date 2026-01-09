# Mostrar Referencia de Año en el Chatbot - COMPLETADO ✅

## Implementación

Se modificó la función `render_evidence_markdown()` en [ui/gradio_app.py](ui/gradio_app.py#L960) para mostrar el año de referencia de cada documento en la evidencia.

### Cambios Realizados

**Antes:**
```
- (0.573) Cámaras de caucho para neumáticos...
  `frag:` b3281e65bc04bfeb_p16429
```

**Ahora:**
```
- (0.573) Cámaras de caucho para neumáticos...
  `frag:` b3281e65bc04bfeb_p16429 | 📅 2025
```

## Ubicación en la UI

En ambas pestaña del chatbot, cuando se muestra la evidencia recuperada:

### 📌 Evidencia del código principal
```
- (0.456) Texto del documento...
  `frag:` xxx_p123 | 📅 2025
```

### 📚 Evidencia recuperada por la consulta
```
- (0.573) Texto del documento...
  `frag:` xxx_p456 | 📅 2026

- (0.512) Texto del documento...
  `frag:` xxx_p789 | 📅 2025
```

## Características

✅ **Emoji visual**: Usa 📅 para indicar año (fácil de identificar)  
✅ **Posición clara**: El año aparece al final de cada ítem de evidencia  
✅ **Manejo de valores nulos**: Si no hay año, simplemente no se muestra  
✅ **Compatibilidad**: Funciona con ambas fuentes de evidencia (support_evidence y evidence)  
✅ **Responsive**: Se adapta a diferentes tamaños de pantalla  

## Código Modificado

```python
def render_evidence_markdown(result: dict) -> str:
    support = result.get("support_evidence") or []
    generic = result.get("evidence") or result.get("context_docs") or []
    lines = []

    if support:
        lines.append("### 📌 Evidencia del código principal\n")
        for ev in support:
            year = ev.get('year')
            year_str = f" | 📅 {year}" if year else ""
            lines.append(f"- ({float(ev.get('score',0)):0.3f}) {ev.get('text','')[:240]}…  \n  `frag:` {ev.get('fragment_id')}{year_str}")

    if generic:
        lines.append("\n### 📚 Evidencia recuperada por la consulta\n")
        for ev in generic:
            text = ev.get("text") or (ev.get("_source", {}) or {}).get("text", "")
            score = ev.get("score") or ev.get("_score", 0)
            frag = ev.get("fragment_id") or (ev.get("_source", {}) or {}).get("fragment_id")
            year = ev.get("year") or (ev.get("_source", {}) or {}).get("year")
            year_str = f" | 📅 {year}" if year else ""
            lines.append(f"- ({float(score):0.3f}) {text[:240]}…  \n  `frag:` {frag}{year_str}")
    
    # ... resto del código
```

## Cómo Funciona

1. **Extrae el año**: Busca el campo `year` en cada objeto de evidencia
2. **Formatea con emoji**: Agrega `| 📅 2025` o `| 📅 2026` si existe el año
3. **Renderiza en Markdown**: Lo integra en el formato de evidencia existente
4. **Maneja valores nulos**: Si no hay año, continúa normalmente sin mostrar nada

## Flujo de Datos

```
API (/classify)
    ↓
Returns: { evidence: [{ fragment_id, year, text, score, ... }, ...] }
    ↓
render_evidence_markdown(result)
    ↓
Extrae year de cada documento
    ↓
Formatea: "frag | 📅 2025"
    ↓
Muestra en Gradio ChatInterface
```

## Ejemplo en la Interfaz

```
💬 Usuario: "Botellas de plástico"

📚 Evidencia recuperada por la consulta
- (0.573) Cámaras de caucho para neumáticos (llantas neumáticas).
  `frag:` b3281e65bc04bfeb_p16429 | 📅 2025

- (0.512) Neumáticos (llantas neumáticas) nuevos de caucho.
  `frag:` b3281e65bc04bfeb_p16226 | 📅 2025
```

## Git Commit

```
commit 0b914f0
Author: Sistema
Date: Jan 9, 2026

feat: Display year reference in evidence section of UI

- Modified render_evidence_markdown() to show year with calendar emoji (📅)
- Year appears at the end of each evidence item: | 📅 2025 or | 📅 2026
- Works for both support_evidence and generic evidence
- Handles cases where year is missing (optional field)
```

## Próximos Pasos Opcionales

Si deseas mejorar aún más la visualización del año:

### 1. Agregar selector de años en el UI
```python
years_input = gr.Dropdown(
    choices=[2025, 2026, "Todos"],
    value="Todos",
    label="Filtrar por año"
)
```

### 2. Colorear por año
```python
year_str = f" | 🟦 2025" if year == 2025 else f" | 🟥 2026" if year == 2026 else ""
```

### 3. Agrupar evidencia por año
```python
# Separar resultados por año antes de renderizar
for year in [2025, 2026]:
    year_evs = [e for e in evidence if e.get('year') == year]
    # Mostrar por año
```

## Estado Final

✅ **COMPLETADO**: Los usuarios ahora pueden ver claramente el año de referencia de cada documento en la evidencia del chatbot.
