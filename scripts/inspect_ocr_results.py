import json
from pathlib import Path
from app.ocr_formrec import extract_fragments_from_pdf

pdf_path = Path("data/corpus/00_WCO/0001_2022e-gir.pdf")
base_metadata = {"bucket": "WCO", "unit": "GIR", "doc_id": "0001_2022e-gir"}

fragments = extract_fragments_from_pdf(str(pdf_path), base_metadata)

# Guardar en JSON
with open("storage/runs/ocr_inspection.json", "w", encoding="utf-8") as f:
    json.dump(fragments, f, indent=2, ensure_ascii=False)

print(f"Total fragmentos: {len(fragments)}")
print("Resultados guardados en: storage/runs/ocr_inspection.json\n")

sep = "=" * 80
dash = "-" * 80

for i, f in enumerate(fragments, 1):
    print(f"\n{sep}")
    print(f"FRAGMENTO {i}")
    print(sep)
    print(f"ID: {f.get('fragment_id')}")
    print(f"Bucket: {f.get('bucket')}")
    print(f"Unit: {f.get('unit')}")
    print(f"Doc ID: {f.get('doc_id')}")
    print(f"Longitud: {len(f.get('text', ''))} caracteres")
    print(f"\nPrimeros 600 caracteres:")
    print(f"{f.get('text', '')[:600]}")
    print(f"\nMetadata: {f.get('metadata')}")
    print(dash)
