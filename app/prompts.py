OUTPUT_SCHEMA = {
  "type":"object",
  "properties":{
    "top_candidates":{"type":"array","items":{
      "type":"object","properties":{
        "code":{"type":"string"},
        "level":{"type":"string","enum":["HS6","NANDINA8","NATIONAL10"]},
        "confidence":{"type":"number","minimum":0,"maximum":1}
      },"required":["code","level","confidence"]
    }},
    "applied_rgi":{"type":"array","items":{"type":"string"}},
    "inclusions":{"type":"array","items":{"type":"string"}},
    "exclusions":{"type":"array","items":{"type":"string"}},
    "missing_fields":{"type":"array","items":{"type":"string"}},
    "evidence":{"type":"array","items":{
      "type":"object","properties":{
        "fragment_id":{"type":"string"},
        "score":{"type":"number"},
        "reason":{"type":"string"}
      },"required":["fragment_id","score","reason"]
    }},
    "versions":{"type":"object"},
    "warnings":{"type":"array","items":{"type":"string"}}
  },
  "required":["top_candidates","applied_rgi","evidence","versions","warnings"]
}

SYSTEM_INSTRUCTIONS = """Eres un asistente de clasificación arancelaria.
- Usa SOLO la evidencia proporcionada.
- Cita siempre fragmentos por fragment_id y explica brevemente el porqué (reason).
- Si faltan datos (material, uso, kit/partes), indícalo en missing_fields.
- No inventes códigos; si la evidencia no alcanza, devuelve top_candidates vacío y explica.
- Prioriza RGI 1; si hay concurrencia, RGI 3(b).
- Indica versiones HS/NANDINA/Arancel entregadas en 'versions'."""
