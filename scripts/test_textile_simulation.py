import pprint
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import generator_gemini as gen
pp = pprint.PrettyPrinter(indent=2)

base_res = {"top_candidates": [{"code": "9999.00", "confidence": 0.47, "level": "HS6"}], "warnings": []}

def run():
    print('\n=== Test A: Usuario inicial: "Quiero importar tela" ===')
    out1 = gen._ensure_missing_fields(dict(base_res), blob="Quiero importar tela", conversation_history=None)
    pp.pprint({"missing_fields": out1.get("missing_fields")})

    print('\n=== Test B: Usuario responde: "es de poliester" ===')
    history = [{"user": "es de poliester"}]
    print('text_blob_norm:', gen._text_blob_from_query_history('Quiero importar tela', history, include_assistant=False))
    out2 = gen._ensure_missing_fields(dict(base_res), blob="Quiero importar tela", conversation_history=history)
    pp.pprint({"missing_fields": out2.get("missing_fields")})

    print('\n=== Test C: Usuario responde: "es de poliéster y tejido" ===')
    history2 = [{"user": "es de poliéster y tejido"}]
    print('text_blob_norm:', gen._text_blob_from_query_history('Quiero importar tela', history2, include_assistant=False))
    out3 = gen._ensure_missing_fields(dict(base_res), blob="Quiero importar tela", conversation_history=history2)
    pp.pprint({"missing_fields": out3.get("missing_fields")})

if __name__ == '__main__':
    run()
