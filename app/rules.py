def apply_rules(query: str, output_json: dict) -> dict:
    txt = query.lower()
    # Ejemplos mínimos (amplía según tus capítulos prioritarios):
    if "kit" in txt or "juego" in txt or "conjunto" in txt:
        if "RGI 3(b)" not in output_json["applied_rgi"]:
            output_json["applied_rgi"].append("RGI 3(b)")
    if "parte" in txt or "partes de" in txt:
        # sugiere revisar notas de sección sobre "partes y accesorios"
        output_json["warnings"].append("Revisar notas de sección sobre 'partes y accesorios'.")
    return output_json
