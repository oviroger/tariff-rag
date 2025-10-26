import json
import sys

try:
    import ir_measures as ir
    from ir_measures import nDCG, R, RR  # nDCG@k, Recall@k, Reciprocal Rank
    IR_AVAILABLE = True
except Exception:
    IR_AVAILABLE = False

def load_qrels(path="data/gold/qrels.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_run(path="storage/runs/run.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def simple_mrr_at_k(qrels, run, k=10):
    # Fallback simple si ir_measures no está disponible
    mrr_sum, count = 0.0, 0
    for qid, rels in qrels.items():
        ranked = sorted(run.get(qid, {}).items(), key=lambda kv: kv[1], reverse=True)[:k]
        rr = 0.0
        for i, (docid, _) in enumerate(ranked, start=1):
            if rels.get(docid, 0) > 0:
                rr = 1.0 / i
                break
        mrr_sum += rr
        count += 1
    return (mrr_sum / max(count, 1)) if count else 0.0

def main():
    qrels = load_qrels()
    run   = load_run()

    if IR_AVAILABLE:
        measures = [nDCG@10, R@10, RR@10]
        results = ir.calc_aggregate(measures, qrels, run)
        out = {str(m): float(results[m]) for m in measures}
        print(json.dumps(out, ensure_ascii=False))
    else:
        # Solo un fallback mínimo (MRR@10)
        out = {"RR@10": simple_mrr_at_k(qrels, run, k=10)}
        print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()