from typing import List, Dict
import hashlib
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from .schemas import Fragment
from .chunking import juridical_chunks
from .config import get_settings

def extract_fragments_from_pdf(file_path: str, meta: Dict) -> List[Fragment]:
    s = get_settings()
    if not s.azure_formrec_endpoint or not s.azure_formrec_key:
        raise RuntimeError("Azure Document Intelligence no configurado (endpoint/key).")
    client = DocumentIntelligenceClient(
        endpoint=s.azure_formrec_endpoint,
        credential=AzureKeyCredential(s.azure_formrec_key)
    )
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document(
            model_id=getattr(s, "azure_fr_model", "prebuilt-layout"),
            document=f
        )
    result = poller.result()

    # Extrae texto por página -> concatenado
    pages_text = []
    for p in result.pages or []:
        lines = [ln.content for ln in (p.lines or [])]
        pages_text.append("\n".join(lines))
    full_text = "\n\n".join(pages_text)

    # Segmenta a fragmentos
    frags = juridical_chunks(full_text, meta)
    # Asigna IDs determinísticos por doc e índice
    out: List[Fragment] = []
    for i, frag in enumerate(frags):
        fid = hashlib.md5(f"{meta.get('doc_id','')}::{i}::{len(frag.text)}".encode()).hexdigest()[:12]
        frag.fragment_id = fid
        out.append(frag)
    return out