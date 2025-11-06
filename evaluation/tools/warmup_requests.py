"""
Warm up API by sending concurrent requests to generate Prometheus metrics.

Usage (PowerShell):
  python evaluation/tools/warmup_requests.py --base-url http://localhost:8000 \
      --health 20 --classify 20 --workers 5 --query "Necesito importar plátanos"

This will hit:
  - GET  {base}/health  (N times)
  - POST {base}/classify with JSON {"query": <query>} (M times)

Then you can export metrics:
  python evaluation/export_logs_operativos.py --url http://localhost:8000/metrics \
      --endpoint /classify --method POST --output evaluation/templates/logs_operativos.csv
"""
from __future__ import annotations
import argparse
import concurrent.futures as futures
import json
import time
from typing import Tuple

import requests


def do_get(session: requests.Session, url: str, timeout: float) -> Tuple[bool, int]:
    try:
        r = session.get(url, timeout=timeout)
        return (200 <= r.status_code < 400, r.status_code)
    except Exception:
        return (False, 0)


def do_post(session: requests.Session, url: str, payload: dict, timeout: float) -> Tuple[bool, int]:
    try:
        r = session.post(url, json=payload, timeout=timeout)
        return (200 <= r.status_code < 400, r.status_code)
    except Exception:
        return (False, 0)


def main():
    ap = argparse.ArgumentParser(description="Generate traffic to warm up API metrics")
    ap.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    ap.add_argument("--health", type=int, default=10, help="Number of GET /health calls")
    ap.add_argument("--classify", type=int, default=10, help="Number of POST /classify calls")
    ap.add_argument("--endpoint", default="/classify", help="Endpoint path for classification")
    ap.add_argument("--query", default="Smartphone OLED 128GB", help="Query text for classification")
    ap.add_argument("--workers", type=int, default=5, help="Concurrent worker threads")
    ap.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    health_url = f"{base}/health"
    classify_url = f"{base}{args.endpoint}"

    ok = 0
    err = 0

    with requests.Session() as session:
        tasks = []
        with futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            # Queue health GETs
            for _ in range(max(0, args.health)):
                tasks.append(ex.submit(do_get, session, health_url, args.timeout))
            # Queue classify POSTs
            payload = {"query": args.query}
            for _ in range(max(0, args.classify)):
                tasks.append(ex.submit(do_post, session, classify_url, payload, args.timeout))

            for t in futures.as_completed(tasks):
                ok_i, _ = t.result()
                if ok_i:
                    ok += 1
                else:
                    err += 1

    total = ok + err
    print(json.dumps({
        "health": args.health,
        "classify": args.classify,
        "ok": ok,
        "err": err,
        "total": total
    }))


if __name__ == "__main__":
    main()
