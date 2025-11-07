import re
from typing import List, Dict, Any
from .schemas import Fragment

def juridical_chunks(text: str, meta: Dict[str, Any], max_chars: int = 1800, overlap: int = 0) -> List[Fragment]:
    """
    Segmenta por unidades legales aproximadas (capítulos/secciones/artículos) y limita tamaño.
    Permite solapamiento entre fragmentos (overlap en caracteres).
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
        step = max_chars - overlap if overlap < max_chars else 1
        while s < len(t):
            e = min(s + max_chars, len(t))
            chunks.append(t[s:e])
            s += step
        return chunks

    out: List[Fragment] = []
    for p in parts:
        for c in slice_by_size(p):
            out.append(Fragment(
                fragment_id="",
                text=c,
                metadata=meta.copy()
            ))
    return out