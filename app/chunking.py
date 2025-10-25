import re
from typing import List, Dict, Any
from .schemas import Fragment

def juridical_chunks(text: str, meta: Dict[str, Any], max_chars: int = 1800) -> List[Fragment]:
    """
    Segmenta por unidades legales aproximadas (capítulos/secciones/artículos) y limita tamaño.
    Heurístico simple para empezar.
    """
    if not text or not text.strip():
        return []

    # Cortes por patrones comunes
    separators = re.compile(
        r"(?im)^(cap[ií]tulo\s+\w+|secci[oó]n\s+\w+|art[ií]culo\s+\d+|t[ií]tulo\s+\w+)\b"
    )

    parts = []
    last = 0
    for m in separators.finditer(text):
        start = m.start()
        if start > last:
            parts.append(text[last:start].strip())
        last = start
    parts.append(text[last:].strip())

    # Ajuste por tamaño
    def slice_by_size(t: str) -> List[str]:
        t = t.strip()
        if len(t) <= max_chars:
            return [t]
        chunks = []
        s = 0
        while s < len(t):
            e = min(s + max_chars, len(t))
            chunks.append(t[s:e])
            s = e
        return chunks

    out: List[Fragment] = []
    for p in parts:
        for c in slice_by_size(p):
            out.append(Fragment(
                fragment_id="",
                source=meta.get("source", "DOC"),
                doc_id=meta.get("doc_id", ""),
                chapter=meta.get("chapter"),
                heading=meta.get("heading"),
                subheading=meta.get("subheading"),
                unit=meta.get("unit", "SECTION"),
                text=c,
                edition=meta.get("edition"),
                validity_from=meta.get("validity_from"),
                validity_to=meta.get("validity_to"),
                metadata=meta.get("metadata", {})
            ))
    return out