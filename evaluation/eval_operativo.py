"""
Evaluación operativa: latencias percentiles, throughput y tasa de errores.

CSV esperado:
  ts, endpoint, status, lat_ms_retrieval, lat_ms_generation, lat_ms_total

Uso:
  python evaluation/eval_operativo.py --csv evaluation/templates/logs_operativos.csv
"""

import argparse
import json
import pandas as pd


def percentiles(series: pd.Series) -> dict:
    # Evita NaNs en cálculos
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"p50": None, "p95": None, "p99": None}
    qs = s.quantile([0.5, 0.95, 0.99])
    return {"p50": float(qs.loc[0.5]), "p95": float(qs.loc[0.95]), "p99": float(qs.loc[0.99])}


def main(path: str) -> None:
    df = pd.read_csv(path, parse_dates=["ts"], infer_datetime_format=True)
    # Filtrar filas con status OK (o 200)
    ok_mask = df["status"].astype(str).str.lower().isin(["ok", "200", "success"]) | (df["status"] == 200)
    df_ok = df[ok_mask]

    lat = {
        "retrieval": percentiles(df_ok.get("lat_ms_retrieval", pd.Series(dtype=float))),
        "generation": percentiles(df_ok.get("lat_ms_generation", pd.Series(dtype=float))),
        "total": percentiles(df_ok.get("lat_ms_total", pd.Series(dtype=float))),
    }

    # Throughput por minuto
    if not df.empty:
        by_min = df.set_index("ts").resample("1min").size()
        qpm_p50 = float(by_min.quantile(0.5)) if not by_min.empty else None
        qpm_p95 = float(by_min.quantile(0.95)) if not by_min.empty else None
    else:
        qpm_p50 = qpm_p95 = None

    error_rate = None
    if len(df) > 0:
        error_rate = float(1 - (len(df_ok) / len(df)))

    out = {
        "lat_ms_percentiles": lat,
        "qpm_p50": qpm_p50,
        "qpm_p95": qpm_p95,
        "error_rate": error_rate,
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Ruta al CSV de logs operativos")
    args = ap.parse_args()
    main(args.csv)
