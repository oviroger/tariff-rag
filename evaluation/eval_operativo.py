"""
Evaluación operativa: latencias percentiles, throughput y tasa de errores.

CSV esperado (formato 1 - por request):
  ts, endpoint, status, lat_ms_retrieval, lat_ms_generation, lat_ms_total

CSV esperado (formato 2 - agregado de Prometheus):
  timestamp, latency_p50, latency_p95, latency_p99, throughput, error_rate

Uso:
  python evaluation/eval_operativo.py --csv evaluation/templates/logs_operativos.csv
"""

import argparse
import json
import pandas as pd
import numpy as np


def percentiles(series: pd.Series) -> dict:
    # Evita NaNs en cálculos
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"p50": None, "p95": None, "p99": None}
    qs = s.quantile([0.5, 0.95, 0.99])
    return {"p50": float(qs.loc[0.5]), "p95": float(qs.loc[0.95]), "p99": float(qs.loc[0.99])}


def process_aggregated_format(df: pd.DataFrame) -> dict:
    """
    Procesa formato agregado de Prometheus (ya tiene percentiles calculados).
    Convertimos de segundos a milisegundos y tomamos medianas de los percentiles.
    """
    # Convertir de segundos a milisegundos (los valores en el CSV están en segundos)
    df_clean = df.copy()
    df_clean['latency_p50'] = pd.to_numeric(df_clean['latency_p50'], errors='coerce') * 1000
    df_clean['latency_p95'] = pd.to_numeric(df_clean['latency_p95'], errors='coerce') * 1000
    df_clean['latency_p99'] = pd.to_numeric(df_clean['latency_p99'], errors='coerce') * 1000
    
    # Filtrar filas válidas (sin inf o valores no numéricos)
    df_clean = df_clean.replace([np.inf, -np.inf], np.nan)
    
    # Calcular medianas de los percentiles reportados
    p50_values = df_clean['latency_p50'].dropna()
    p95_values = df_clean['latency_p95'].dropna()
    p99_values = df_clean['latency_p99'].dropna()
    
    lat = {
        "total": {
            "p50": float(p50_values.median()) if not p50_values.empty else None,
            "p95": float(p95_values.median()) if not p95_values.empty else None,
            "p99": float(p99_values.median()) if not p99_values.empty else None,
        }
    }
    
    # Throughput: promedio de throughput reportado
    throughput_values = pd.to_numeric(df_clean['throughput'], errors='coerce').dropna()
    qpm_avg = float(throughput_values.mean()) if not throughput_values.empty else None
    
    # Error rate: promedio de error_rate reportado
    error_values = pd.to_numeric(df_clean['error_rate'], errors='coerce').dropna()
    error_rate = float(error_values.mean()) if not error_values.empty else None
    
    return {
        "lat_ms_percentiles": lat,
        "qpm_avg": qpm_avg,
        "qpm_p50": None,
        "qpm_p95": None,
        "error_rate": error_rate,
        "format": "aggregated_prometheus"
    }


def process_per_request_format(df: pd.DataFrame) -> dict:
    """
    Procesa formato por-request (calcula percentiles desde datos individuales).
    """
    # Filtrar filas con status OK (o 200)
    ok_mask = df["status"].astype(str).str.lower().isin(["ok", "200", "success"]) | (df["status"] == 200)
    df_ok = df[ok_mask]

    lat = {
        "retrieval": percentiles(df_ok.get("lat_ms_retrieval", pd.Series(dtype=float))),
        "generation": percentiles(df_ok.get("lat_ms_generation", pd.Series(dtype=float))),
        "total": percentiles(df_ok.get("lat_ms_total", pd.Series(dtype=float))),
    }

    # Throughput por minuto
    if not df.empty and 'ts' in df.columns:
        by_min = df.set_index("ts").resample("1min").size()
        qpm_p50 = float(by_min.quantile(0.5)) if not by_min.empty else None
        qpm_p95 = float(by_min.quantile(0.95)) if not by_min.empty else None
    else:
        qpm_p50 = qpm_p95 = None

    error_rate = None
    if len(df) > 0:
        error_rate = float(1 - (len(df_ok) / len(df)))

    return {
        "lat_ms_percentiles": lat,
        "qpm_p50": qpm_p50,
        "qpm_p95": qpm_p95,
        "error_rate": error_rate,
        "format": "per_request"
    }


def main(path: str) -> None:
    df = pd.read_csv(path)
    
    # Auto-detectar formato
    columns = set(df.columns)
    
    if 'latency_p50' in columns and 'throughput' in columns:
        # Formato agregado de Prometheus
        out = process_aggregated_format(df)
    elif 'ts' in columns and 'status' in columns:
        # Formato por-request
        df['ts'] = pd.to_datetime(df['ts'], errors='coerce')
        out = process_per_request_format(df)
    else:
        raise ValueError(f"Formato CSV no reconocido. Columnas encontradas: {columns}")
    
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Ruta al CSV de logs operativos")
    args = ap.parse_args()
    main(args.csv)
