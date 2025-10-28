from pathlib import Path
from app.ocr_formrec import extract_fragments_from_pdf

pdf_path = Path("data/corpus/00_WCO/0001_2022e-gir.pdf")
base_metadata = {
    "bucket": "WCO",
    "unit": "GIR",
    "doc_id": "0001_2022e-gir"
}

fragments = extract_fragments_from_pdf(str(pdf_path), base_metadata)

print("\n" + "="*80)
print(f"Total de fragmentos extraidos: {len(fragments)}")
print("="*80 + "\n")

for i, frag_dict in enumerate(fragments, 1):
    print(f"\nFRAGMENTO {i}:")
    print(f"   fragment_id: {frag_dict.get('fragment_id', 'N/A')}")
    print(f"   bucket: {frag_dict.get('bucket', 'N/A')}")
    print(f"   unit: {frag_dict.get('unit', 'N/A')}")
    print(f"   doc_id: {frag_dict.get('doc_id', 'N/A')}")
    print(f"   Longitud del texto: {len(frag_dict.get('text', ''))} caracteres")
    print(f"\n   Primeros 500 caracteres del texto:")
    print(f"   {frag_dict.get('text', '')[:500]}...")
    print(f"\n   Metadata: {frag_dict.get('metadata', {})}")
    print("   " + "-"*76)
