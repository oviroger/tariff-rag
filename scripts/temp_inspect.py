"""
app/ocr_formrec.py
Extracción de texto mediante Azure Document Intelligence (antes Form Recognizer).
"""

import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from .chunking import juridical_chunks

def extract_fragments_from_pdf(pdf_path: str, base_metadata: dict) -> list:
    """
    Usa Azure DI para extraer layout (prebuilt-layout) y devuelve chunks jurídicos.
    """
    endpoint = os.environ.get("AZURE_FR_ENDPOINT")
    key = os.environ.get("AZURE_FR_KEY")
    if not endpoint or not key:
        raise ValueError("Missing AZURE_FR_ENDPOINT or AZURE_FR_KEY")

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    with open(pdf_path, "rb") as f:
        file_content = f.read()
    
    # For azure-ai-documentintelligence 1.0.2, pass the bytes directly as the body parameter
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=file_content  # Pass bytes directly as the body parameter
    )
    result = poller.result()

    text_blocks = []
    if result.paragraphs:
        for para in result.paragraphs:
            if para.content:
                text_blocks.append(para.content)
    else:
        # Fallback: concatenate page content
        if result.pages:
            for pg in result.pages:
                if pg.lines:
                    for line in pg.lines:
                        text_blocks.append(line.content)

    full_text = "\n".join(text_blocks)
    
    # Pass base_metadata as the second argument 'meta'
    chunks_list = juridical_chunks(full_text, base_metadata)

    fragments = []
    for idx, chunk_obj in enumerate(chunks_list):
        frag_id = f"{base_metadata.get('doc_id', 'unknown')}_{idx:04d}"
        
        # Extract text from Fragment object if it's a Pydantic model
        if hasattr(chunk_obj, 'text'):
            chunk_text = chunk_obj.text
        elif isinstance(chunk_obj, str):
            chunk_text = chunk_obj
        else:
            chunk_text = str(chunk_obj)
        
        frag = {
            "fragment_id": frag_id,
            "chunk_id": frag_id,
            "text": chunk_text,  # Now it's guaranteed to be a string
            **base_metadata,
        }
        fragments.append(frag)

    return fragments
if __name__ == "__main__":
    from pathlib import Path
    pdf_path = Path("data/corpus/00_WCO/0001_2022e-gir.pdf")
    base_metadata = {"bucket": "WCO", "unit": "GIR", "doc_id": "0001_2022e-gir"}
    
    fragments = extract_fragments_from_pdf(str(pdf_path), base_metadata)
    
    print("\n" + "="*80)
    print(f"Total fragmentos: {len(fragments)}")
    print("="*80)
    
    for i, f in enumerate(fragments, 1):
        print(f"\nFRAGMENTO {i}:")
        print(f"  ID: {f.get('fragment_id')}")
        print(f"  Longitud: {len(f.get('text', ''))} caracteres")
        print(f"  Texto: {f.get('text', '')[:400]}...")
        print("-"*80)
