#!/usr/bin/env python
"""
Quick visualization for retrieval metrics.

Reads evaluation/results/retrieval_asgard_metrics.json (or a path provided via --metrics)
and renders:
- A small text table
- Optional bar charts for Recall/Precision/nDCG at K if matplotlib is installed.

Usage:
  python evaluation/tools/plot_retrieval_metrics.py \
    --metrics evaluation/results/retrieval_asgard_metrics.json \
    --save evaluation/results/retrieval_asgard_metrics.png
"""

import argparse
import json
from pathlib import Path


def load_metrics(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def print_table(m: dict) -> None:
    def fmt(x):
        return f"{x:.3f}" if isinstance(x, (float, int)) else str(x)

    print("\nRetrieval metrics:\n")
    print("  Recall  : @1=" + fmt(m.get("recall@1")) +
          "  @3=" + fmt(m.get("recall@3")) +
          "  @5=" + fmt(m.get("recall@5")))
    print("  Precision: @1=" + fmt(m.get("precision@1")) +
          "  @3=" + fmt(m.get("precision@3")) +
          "  @5=" + fmt(m.get("precision@5")))
    print("  nDCG    : @1=" + fmt(m.get("ndcg@1")) +
          "  @3=" + fmt(m.get("ndcg@3")) +
          "  @5=" + fmt(m.get("ndcg@5")))
    print("  MAP     :     " + fmt(m.get("map")))
    print(f"\n  Queries: {m.get('num_queries')}  Annotated: {m.get('num_annotated')}" )


def plot_bars(m: dict, save_path: Path | None):
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        print("\n(matplotlib no está instalado; omitiendo gráficos. Puede instalarlo con: pip install matplotlib)")
        return

    ks = [1, 3, 5]
    recall = [m.get(f"recall@{k}", 0.0) for k in ks]
    precision = [m.get(f"precision@{k}", 0.0) for k in ks]
    ndcg = [m.get(f"ndcg@{k}", 0.0) for k in ks]

    fig, axes = plt.subplots(1, 3, figsize=(12, 3))
    for ax, vals, title in zip(
        axes,
        [recall, precision, ndcg],
        ["Recall", "Precision", "nDCG"],
    ):
        ax.bar([str(k) for k in ks], vals, color="#4C78A8")
        ax.set_ylim(0, 1)
        ax.set_title(title)
        ax.set_xlabel("@K")
        ax.grid(True, axis="y", linestyle=":", alpha=0.4)
        for i, v in enumerate(vals):
            ax.text(i, v + 0.02, f"{v:.3f}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    if save_path:
        fig.savefig(str(save_path), dpi=150)
        print(f"\nGráfico guardado en: {save_path}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=str, default="evaluation/results/retrieval_asgard_metrics.json")
    parser.add_argument("--save", type=str, default="")
    args = parser.parse_args()

    metrics_path = Path(args.metrics)
    if not metrics_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de métricas: {metrics_path}")

    m = load_metrics(metrics_path)
    print_table(m)
    save_path = Path(args.save) if args.save else None
    plot_bars(m, save_path)


if __name__ == "__main__":
    main()
