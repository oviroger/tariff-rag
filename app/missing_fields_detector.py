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
    textiles = ["textil", "textile", "tela", "tejido", "prenda", "ropa", "lana", "algodon", "algodón", "poliester", "poliéster", "seda", "hilo", "hilado"]
    frutas = ["fruta", "frutas", "manzana", "naranja", "plátano", "piña", "limón", "uva", "durazno", "pera"]
    carnes = ["carne", "carnes", "res", "pollo", "cerdo", "cordero", "ternera", "pavo", "conejo"]
    pescados = ["pescado", "peces", "atún", "tilapia", "salmón", "trucha", "anchoa", "sardina", "bacalao"]

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
    if any(t in blob for t in textiles):
        return [
            "De qué material está hecho (algodón, poliéster, lana, mezcla, sintético)",
            "Es tejido, punto, o no tejido",
            "Cuál es el uso final (prenda de vestir, tela por metro, artículos de hogar)",
            "Ancho de la tela en cm o pulgadas",
            "Gramaje o peso por metro cuadrado (si es tela)",
        ]
    if any(f in blob for f in frutas):
        return [
            "¿Qué tipo específico de fruta? (manzana, naranja, plátano, etc.)",
            "¿Está fresco/refrigerado, seco, o procesado?",
            "¿Está entero o ha sido procesado/pelado?"
        ]
    if any(c in blob for c in carnes):
        return [
            "¿Qué tipo de carne? (res, pollo, cerdo, cordero, etc.)",
            "¿Está entera, en trozos, o deshuesada?",
            "¿Fresca, refrigerada, congelada, o salada?"
        ]
    if any(p in blob for p in pescados):
        return [
            "¿Qué especie de pescado? (atún, tilapia, salmón, etc.)",
            "¿Está entero, fileteado, o en conserva?",
            "¿Fresco, congelado, o en conserva?"
        ]
    return [
        "Descripción precisa del producto (material, uso, presentación)",
        "Características técnicas clave (dimensiones, potencia, composición)",
        "Estado o presentación (nuevo/usado, a granel, envasado)",
    ]
