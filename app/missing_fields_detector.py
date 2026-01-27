"""
Simple missing fields detector used when the LLM does not return guidance.
"""
import unicodedata
from typing import List, Dict, Any


def _strip_accents(s: str) -> str:
    try:
        return unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode("utf-8")
    except Exception:
        return s or ""


def detect_missing_fields(query: str, docs: List[Dict[str, Any]] | None = None) -> List[str]:
    blob_parts = [query or ""]
    docs = docs or []
    for d in docs:
        src = d.get("_source", {}) if isinstance(d, dict) else {}
        text = src.get("text") or ""
        if text:
            blob_parts.append(str(text))
    blob = _strip_accents(" ".join(blob_parts).lower())

    vehicles = ["vehiculo", "vehículo", "auto", "carro", "coche", "camion", "camión", "bus", "autobus", "autobús", "microbus", "microbús", "moto", "motocicleta"]
    metals = ["acero", "steel", "hierro", "lamina", "lámina", "chapa", "plancha", "bobina", "inox", "aluminio", "cobre", "metal"]

    if any(v in blob for v in vehicles):
        return [
            "Tipo específico de vehículo (automóvil, camión, bus, motocicleta, etc.)",
            "Tipo de motor (gasolina, diésel, eléctrico, híbrido)",
            "Cilindrada del motor en cm³",
            "Número de plazas/pasajeros",
            "Si es nuevo o usado",
        ]
    if any(m in blob for m in metals):
        return [
            "Tipo de producto metálico y material (lámina, bobina, acero, aluminio, etc.)",
            "Espesor en mm",
            "Dimensiones (ancho y largo)",
            "Proceso (laminado en caliente o en frío)",
            "Recubrimiento si aplica (galvanizado, pintado, etc.)",
        ]
    return [
        "Descripción precisa del producto (material, uso, presentación)",
        "Características técnicas clave (dimensiones, potencia, composición)",
        "Estado o presentación (nuevo/usado, a granel, envasado)",
    ]
