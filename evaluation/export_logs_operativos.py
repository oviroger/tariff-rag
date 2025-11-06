"""
Script para exportar logs_operativos.csv desde /metrics de Prometheus
Requiere: requests
Uso: python export_logs_operativos.py --url http://localhost:9090/metrics --output logs_operativos.csv
"""
import requests
import csv
import re
import argparse
import os
from datetime import datetime

def _parse_labels(lbl: str) -> dict:
    """Convierte key="value" pares en un dict."""
    return {k: v for k, v in re.findall(r'(\w+)=\"([^\"]*)\"', lbl)}


def parse_metrics(text: str, endpoint: str | None = None, method: str | None = None, status: str | None = None):
    # Extrae latencia (histograma), throughput y errores; agrega sobre etiquetas si existen
    metrics = {
        'latency': [],  # lista de (le, count_cumulative)
        'throughput': 0.0,
        'error_rate': 0.0
    }

    # 1) Latencia: histogram buckets con etiquetas variables
    # Ejemplo: api_request_seconds_bucket{endpoint="/classify",method="POST",le="0.1"} 3
    lat_re = re.compile(r'^api_request_seconds_bucket\{([^}]*)\}\s+([0-9eE\+\.-]+)$', re.M)
    bucket_map: dict[float, float] = {}
    for labels_str, val_str in lat_re.findall(text):
        labels = _parse_labels(labels_str)
        if endpoint and labels.get('endpoint') != endpoint:
            continue
        if method and labels.get('method') != method:
            continue
        le_s = labels.get('le')
        if not le_s:
            continue
        le = float('inf') if le_s == '+Inf' else float(le_s)
        val = float(val_str)
        bucket_map[le] = bucket_map.get(le, 0.0) + val
    if bucket_map:
        metrics['latency'] = sorted(bucket_map.items(), key=lambda x: (float('inf') if x[0] == float('inf') else x[0]))
    else:
        # Fallback: si se pasó filtro pero no hay series etiquetadas, intenta sin etiquetas (solo le)
        if endpoint or method or status:
            unlabeled_re = re.compile(r'^api_request_seconds_bucket\{le="([0-9eE\+\.-]+|\+Inf)"\}\s+([0-9eE\+\.-]+)$', re.M)
            for le_s, val_s in unlabeled_re.findall(text):
                le = float('inf') if le_s == '+Inf' else float(le_s)
                val = float(val_s)
                bucket_map[le] = bucket_map.get(le, 0.0) + val
            if bucket_map:
                metrics['latency'] = sorted(bucket_map.items(), key=lambda x: (float('inf') if x[0] == float('inf') else x[0]))

    # 2) Throughput: api_requests_total con o sin etiquetas
    tp_re = re.compile(r'^api_requests_total(?:\{([^}]*)\})?\s+([0-9eE\+\.-]+)$', re.M)
    total_tp = 0.0
    total_err_from_status = 0.0
    for labels_str, val_str in tp_re.findall(text):
        if labels_str:
            labels = _parse_labels(labels_str)
            if endpoint and labels.get('endpoint') != endpoint:
                continue
            if method and labels.get('method') != method:
                continue
            if status and labels.get('status') != status:
                continue
            st = labels.get('status')
        else:
            st = None
        val = float(val_str)
        total_tp += val
        if st and not st.startswith('2'):
            total_err_from_status += val
    metrics['throughput'] = total_tp

    # 3) Error rate: api_requests_errors_returned con o sin etiquetas
    err_re = re.compile(r'^api_requests_errors_returned(?:\{([^}]*)\})?\s+([0-9eE\+\.-]+)$', re.M)
    total_err = 0.0
    for labels_str, val_str in err_re.findall(text):
        if labels_str:
            labels = _parse_labels(labels_str)
            if endpoint and labels.get('endpoint') != endpoint:
                continue
            if method and labels.get('method') != method:
                continue
        total_err += float(val_str)
    # Si tenemos breakdown por status en api_requests_total, preferimos ese para tasa de error
    if total_tp > 0:
        metrics['error_rate'] = total_err_from_status / total_tp
    else:
        metrics['error_rate'] = total_err

    return metrics

def export_logs(metrics, output_file):
    # Encabezados: timestamp, latency_p50, latency_p95, latency_p99, throughput, error_rate
    now = datetime.now().isoformat()
    latency_buckets = [le for le, _ in metrics['latency']]
    counts = [count for _, count in metrics['latency']]
    total = counts[-1] if counts else 0.0
    def percentile(p):
        if not counts or total == 0.0:
            return 0.0
        threshold = total * p / 100
        for le, count in zip(latency_buckets, counts):
            if count >= threshold:
                return le
        return latency_buckets[-1] if latency_buckets else 0.0
    def safe_zero(val):
        return val if val is not None else 0.0
    row = {
        'timestamp': now,
        'latency_p50': safe_zero(percentile(50)),
        'latency_p95': safe_zero(percentile(95)),
        'latency_p99': safe_zero(percentile(99)),
        'throughput': safe_zero(metrics['throughput']),
        'error_rate': safe_zero(metrics['error_rate'])
    }
    # Asegurar directorio
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    write_header = not os.path.exists(output_file) or os.path.getsize(output_file) == 0
    with open(output_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description='Exporta logs_operativos.csv desde Prometheus /metrics')
    parser.add_argument('--url', type=str, required=True, help='URL de /metrics de Prometheus')
    parser.add_argument('--endpoint', type=str, default=None, help='Filtra por etiqueta endpoint (opcional)')
    parser.add_argument('--method', type=str, default=None, help='Filtra por etiqueta method (opcional)')
    parser.add_argument('--status', type=str, default=None, help='Filtra por etiqueta status (opcional)')
    parser.add_argument('--output', type=str, default='logs_operativos.csv', help='Archivo de salida CSV')
    args = parser.parse_args()
    resp = requests.get(args.url)
    if resp.status_code != 200:
        print(f'Error al consultar {args.url}: {resp.status_code}')
        return
    metrics = parse_metrics(resp.text, endpoint=args.endpoint, method=args.method, status=args.status)
    export_logs(metrics, args.output)
    print(f'Exportado a {args.output}')

if __name__ == '__main__':
    main()
