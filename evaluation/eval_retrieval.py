"""
Evaluación del componente de recuperación (RAG).

CSV esperado:
  id, gold_doc_ids, retrieved_doc_ids, retrieved_scores

Calcula:
  - recall@k
  - nDCG@k (relevancia binaria)

Uso:
  python evaluation/eval_retrieval.py --csv evaluation/templates/eval_retrieval.csv --k 5
"""

import ast
import argparse
import json
import numpy as np
import pandas as pd


def recall_at_k(row: pd.Series, k: int = 5) -> int:
    gold = set(ast.literal_eval(row["gold_doc_ids"])) if isinstance(row.get("gold_doc_ids"), str) else set()
    ret = ast.literal_eval(row["retrieved_doc_ids"])[:k] if isinstance(row.get("retrieved_doc_ids"), str) else []
    return 1 if gold.intersection(ret) else 0


def ndcg_at_k(row: pd.Series, k: int = 5) -> float:
    gold = set(ast.literal_eval(row["gold_doc_ids"])) if isinstance(row.get("gold_doc_ids"), str) else set()
    ret = ast.literal_eval(row["retrieved_doc_ids"])[:k] if isinstance(row.get("retrieved_doc_ids"), str) else []
    gains = [1 if d in gold else 0 for d in ret]
    if not gains:
        return 0.0
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted(gains, reverse=True)
    idcg = sum(g / np.log2(i + 2) for i, g in enumerate(ideal))
    return float(dcg / idcg) if idcg > 0 else 0.0


def main(path: str, k: int) -> None:
    df = pd.read_csv(path)
    rec = float(df.apply(lambda r: recall_at_k(r, k), axis=1).mean())
    ndcg = float(df.apply(lambda r: ndcg_at_k(r, k), axis=1).mean())
    out = {f"recall@{k}": rec, f"ndcg@{k}": ndcg}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Ruta al CSV de evaluación de retrieval")
    ap.add_argument("--k", type=int, default=5, help="k para recall y nDCG")
    args = ap.parse_args()
    main(args.csv, args.k)
