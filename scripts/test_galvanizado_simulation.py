import pprint
import sys
from pathlib import Path
# Ensure repo root in path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import generator_gemini as gen

pp = pprint.PrettyPrinter(indent=2)


def run_test():
    base_res = {"top_candidates": [{"code": "7208.90", "confidence": 0.47, "level": "HS6"}], "warnings": []}

    print("\n=== Test 1: Turno 1 - Usuario: 'Láminas de acero' (sin history) ===")
    out1 = gen._ensure_missing_fields(dict(base_res), blob="Láminas de acero", conversation_history=None)
    pp.pprint({"missing_fields": out1.get("missing_fields")})

    print("\n=== Test 2: Turno 2 - Usuario responde: 'El espesor es de 2 mm' ===")
    history = [{"user": "El espesor es de 2 mm"}]
    print("text_blob_norm:", gen._text_blob_from_query_history("Láminas de acero", history, include_assistant=False))
    out2 = gen._ensure_missing_fields(dict(base_res), blob="Láminas de acero", conversation_history=history)
    pp.pprint({"missing_fields": out2.get("missing_fields")})
    # Quick direct check for satisfaction detection
    tb = gen._text_blob_from_query_history("Láminas de acero", history, include_assistant=False)
    print("direct check - 'galvanizado' in tb:", 'galvanizado' in tb)

    print("\n=== Test 3: Turno 2 - Usuario responde: 'El espesor es 2 mm y está galvanizado' ===")
    history2 = [{"user": "El espesor es 2 mm y está galvanizado"}]
    print("text_blob_norm:", gen._text_blob_from_query_history("Láminas de acero", history2, include_assistant=False))
    out3 = gen._ensure_missing_fields(dict(base_res), blob="Láminas de acero", conversation_history=history2)
    pp.pprint({"missing_fields": out3.get("missing_fields")})
    tb2 = gen._text_blob_from_query_history("Láminas de acero", history2, include_assistant=False)
    print("direct check - tb2 contains galvanizado:", 'galvanizado' in tb2)
    # Recreate cleaned_missing_fields and simulate prune logic to debug
    original_fields = [
        "¿Cuál es el espesor de la lámina en mm? → Define si es lámina fina, plancha o chapa gruesa",
        "¿Está galvanizado, pintado, o sin recubrimiento? → Puede cambiar la partida",
        "¿Cuál es el acabado? (laminado en caliente, laminado en frío, pulido, etc.) → Diferencia entre capítulos",
        "¿Cuál es la composición? (acero al carbono, inoxidable, etc.) → Podría cambiar de capítulo",
    ]
    cleaned_missing_fields = [gen._normalize_text(f) for f in original_fields]
    print('\n-- Simulated prune loop for Test 3 --')
    for f in cleaned_missing_fields:
        print('field_norm:', f)
        # our simplified satisfaction keywords for recubrimiento
        satisfaction_keywords = ["galvanizado", "galvanizacion", "zincado", "pintado", "sin recubrimiento", "recubierto"]
        field_matches = any(kw in f for kw in ["recubrimiento", "galvanizado", "pintado", "zincado"])
        satisfied = any(kw in tb2 for kw in satisfaction_keywords)
        print(' field_matches=', field_matches, ' satisfied=', satisfied)

    print("\n=== Test 4: Mensaje inicial incluye 'galvanizado' ===")
    print("text_blob_norm:", gen._text_blob_from_query_history("Láminas de acero 2 mm galvanizado", None, include_assistant=False))
    out4 = gen._ensure_missing_fields(dict(base_res), blob="Láminas de acero 2 mm galvanizado", conversation_history=None)
    pp.pprint({"missing_fields": out4.get("missing_fields")})
    tb3 = gen._text_blob_from_query_history("Láminas de acero 2 mm galvanizado", None, include_assistant=False)
    print("direct check - tb3 contains galvanizado:", 'galvanizado' in tb3)
    print('\n-- Simulated prune loop for Test 4 --')
    for f in cleaned_missing_fields:
        field_matches = any(kw in f for kw in ["recubrimiento", "galvanizado", "pintado", "zincado"])
        satisfied = any(kw in tb3 for kw in ["galvanizado", "galvanizacion", "zincado", "pintado", "sin recubrimiento", "recubierto"])
        print('field_norm=', f, ' field_matches=', field_matches, ' satisfied=', satisfied)

    print("\nResumen: Si 'galvanizado' aparece en el historial o en el mensaje, no debe aparecer la pregunta correspondiente en missing_fields.")


if __name__ == '__main__':
    run_test()
