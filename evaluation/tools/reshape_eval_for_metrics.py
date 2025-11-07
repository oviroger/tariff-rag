"""
Convierte evaluation/templates/eval_clasificador_hs6_asgard.csv al formato esperado por evaluation/eval_clasificador.py
Entrada: columnas [query_id, query, true_hs6, pred_top1..3, score_top1..3]
Salida: columnas [id, descripcion, hs6_ref, pred_codes, pred_scores]
- hs6_ref y pred_codes normalizados a 6 dígitos (sin puntos)
- pred_scores si hay columnas de score; si no, se omite
"""
import csv
import sys
import re
from pathlib import Path
from typing import List, Optional


def norm_hs6(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return None
    # keep only digits, take first 6
    digits = re.sub(r"\D", "", s)
    if len(digits) >= 6:
        return digits[:6]
    # if exactly 4 digits (chapter+heading), pad two zeros? better return None to avoid wrong matches
    return digits if digits else None


def to_list_str(items: List[Optional[str]]) -> str:
    xs = [x for x in (norm_hs6(i) for i in items) if x]
    # devolver como string de lista python para que ast.literal_eval funcione en eval_clasificador.py
    return str(xs)


def reshape(inp: str, outp: str) -> None:
    with open(inp, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows_out = []
        has_scores = all(k in reader.fieldnames for k in ["score_top1", "score_top2", "score_top3"]) if reader.fieldnames else False
        for row in reader:
            pred_codes = to_list_str([row.get("pred_top1"), row.get("pred_top2"), row.get("pred_top3")])
            if has_scores:
                # convertir a float si existe, de lo contrario None
                scores = []
                for k in ("score_top1", "score_top2", "score_top3"):
                    v = row.get(k)
                    try:
                        scores.append(float(v) if v not in (None, "", "nan") else None)
                    except Exception:
                        scores.append(None)
                pred_scores = str(scores)
            else:
                pred_scores = None
            rows_out.append({
                "id": row.get("query_id"),
                "descripcion": row.get("query"),
                "hs6_ref": norm_hs6(row.get("true_hs6")),
                "pred_codes": pred_codes,
                **({"pred_scores": pred_scores} if pred_scores is not None else {}),
            })
    # escribir salida
    fieldnames = ["id", "descripcion", "hs6_ref", "pred_codes"] + (["pred_scores"] if rows_out and "pred_scores" in rows_out[0] else [])
    with open(outp, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"✅ Escrito: {outp} ({len(rows_out)} filas)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python reshape_eval_for_metrics.py <input_csv> <output_csv>")
        sys.exit(1)
    reshape(sys.argv[1], sys.argv[2])
