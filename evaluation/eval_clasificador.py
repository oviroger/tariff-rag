"""
Evaluación del clasificador HS.

Lectura de CSV con columnas:
  id, descripcion, hs6_ref, pred_codes, pred_scores

Calcula:
  - acc@1, acc@3
  - macro_f1, micro_f1 (si scikit-learn disponible)
  - mrr@3
  - ece (opcional, si se entrega columna 'pred_scores' con prob. top1)

Uso:
  python evaluation/eval_clasificador.py --csv evaluation/templates/eval_clasificador_hs6.csv
"""

import ast
import argparse
import json
from typing import Optional

import numpy as np
import pandas as pd

# scikit-learn es opcional. Si no está, degradamos el cálculo de F1.
try:
    from sklearn.metrics import f1_score
    _SKLEARN = True
except Exception:
    _SKLEARN = False


def hit_at_k(row: pd.Series, k: int = 1) -> int:
    try:
        preds = ast.literal_eval(row["pred_codes"]) or []
    except Exception:
        preds = []
    gold = str(row["hs6_ref"]) if row.get("hs6_ref") is not None else None
    return 1 if gold and gold in preds[:k] else 0


def rr_at_k(row: pd.Series, k: int = 3) -> float:
    try:
        preds = ast.literal_eval(row["pred_codes"])[:k]
    except Exception:
        preds = []
    gold = str(row["hs6_ref"]) if row.get("hs6_ref") is not None else None
    if not gold:
        return 0.0
    try:
        rank = preds.index(gold) + 1
        return 1.0 / rank
    except ValueError:
        return 0.0


def ece_score(y_true: np.ndarray, y_pred: np.ndarray, conf: np.ndarray, M: int = 10) -> float:
    """Expected Calibration Error (ECE) con bins uniformes [0,1]."""
    bins = np.linspace(0, 1, M + 1)
    ece = 0.0
    N = len(conf)
    for i in range(M):
        lb, ub = bins[i], bins[i + 1]
        idx = (conf > lb) & (conf <= ub)
        if idx.sum() == 0:
            continue
        acc = (y_pred[idx] == y_true[idx]).mean()
        ece += (idx.sum() / N) * abs(acc - conf[idx].mean())
    return float(ece)


def main(path: str) -> None:
    df = pd.read_csv(path)

    # acc@1 y acc@3
    acc1 = float(df.apply(lambda r: hit_at_k(r, 1), axis=1).mean())
    acc3 = float(df.apply(lambda r: hit_at_k(r, 3), axis=1).mean())

    # Top1 pred label
    def _top1(s: Optional[str]) -> Optional[str]:
        if not isinstance(s, str) or s.strip() == "":
            return None
        try:
            lst = ast.literal_eval(s)
            return lst[0] if lst else None
        except Exception:
            return None

    df["pred_top1"] = df["pred_codes"].apply(_top1)

    # Macro/Micro-F1 (si sklearn disponible)
    macro_f1 = None
    micro_f1 = None
    if _SKLEARN:
        y_true = df["hs6_ref"].astype(str).values
        y_pred = df["pred_top1"].astype(str).values
        macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
        micro_f1 = float(f1_score(y_true, y_pred, average="micro", zero_division=0))

    # MRR@3
    mrr3 = float(df.apply(rr_at_k, axis=1).mean())

    # ECE opcional (si existe pred_scores con prob top1)
    ece_val = None
    if "pred_scores" in df.columns:
        def _top1_conf(s: Optional[str]) -> Optional[float]:
            if not isinstance(s, str) or s.strip() == "":
                return None
            try:
                lst = ast.literal_eval(s)
                if isinstance(lst, (list, tuple)) and lst:
                    return float(lst[0])
            except Exception:
                return None
            return None

        df["conf"] = df["pred_scores"].apply(_top1_conf)
        mask = df["conf"].notna() & df["pred_top1"].notna()
        if mask.any():
            y_true = df.loc[mask, "hs6_ref"].astype(str).values
            y_pred = df.loc[mask, "pred_top1"].astype(str).values
            conf = df.loc[mask, "conf"].astype(float).values
            ece_val = ece_score(y_true, y_pred, conf, M=10)

    out = {
        "acc@1": acc1,
        "acc@3": acc3,
        "macro_f1": macro_f1,
        "micro_f1": micro_f1,
        "mrr@3": mrr3,
        "ece@10": ece_val,
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Ruta al CSV de evaluación del clasificador")
    args = parser.parse_args()
    main(args.csv)
