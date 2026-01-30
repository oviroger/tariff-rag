import json
import unicodedata
from pathlib import Path
from typing import Dict, List

_ROOT = Path(__file__).parent
_CATEGORY_PATH = _ROOT / "category_keywords.json"
_MATERIALS_PATH = _ROOT / "materials_keywords.json"

_CACHE: Dict[str, Dict] = {
    "categories": None,
    "materials": None,
}

def _strip_accents(s: str) -> str:
    try:
        return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode('utf-8')
    except Exception:
        return (s or '')

def normalize_text(s: str) -> str:
    return _strip_accents((s or '').lower())

def load_category_keywords() -> Dict:
    if _CACHE.get("categories") is None:
        try:
            if _CATEGORY_PATH.exists():
                with open(_CATEGORY_PATH, "r", encoding="utf-8") as f:
                    _CACHE["categories"] = json.load(f)
            else:
                _CACHE["categories"] = {}
        except Exception:
            _CACHE["categories"] = {}
    return _CACHE["categories"]

def load_materials_keywords() -> Dict:
    if _CACHE.get("materials") is None:
        try:
            if _MATERIALS_PATH.exists():
                with open(_MATERIALS_PATH, "r", encoding="utf-8") as f:
                    _CACHE["materials"] = json.load(f)
            else:
                _CACHE["materials"] = {}
        except Exception:
            _CACHE["materials"] = {}
    return _CACHE["materials"]

def get_category_synonyms(category: str) -> List[str]:
    cfg = load_category_keywords() or {}
    entry = cfg.get(category)
    if isinstance(entry, dict):
        syns = entry.get("synonyms", []) or []
    elif isinstance(entry, list):
        syns = entry
    else:
        syns = []
    return [normalize_text(str(s)) for s in syns]

def get_vehicle_keywords() -> List[str]:
    cfg = load_category_keywords() or {}
    syns = cfg.get("vehicles", {}).get("synonyms", []) or []
    fields = cfg.get("vehicle_fields", []) or []
    out = [normalize_text(str(s)) for s in syns]
    out += [normalize_text(str(s)) for s in fields]
    # dedupe while preserving order
    seen = set()
    res = []
    for s in out:
        if s not in seen:
            seen.add(s)
            res.append(s)
    return res

def get_vehicle_fields() -> List[str]:
    cfg = load_category_keywords() or {}
    fields = cfg.get("vehicle_fields", []) or []
    return [normalize_text(str(s)) for s in fields]
