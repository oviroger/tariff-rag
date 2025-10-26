from prometheus_client import Counter, Histogram, Gauge

# Conteo de requests por endpoint/método/estado
REQUESTS = Counter(
    "api_requests_total", "Total de requests",
    labelnames=["endpoint", "method", "status"]
)

# Histograma de latencias por endpoint/método
LATENCY = Histogram(
    "api_request_seconds", "Latencia por endpoint",
    labelnames=["endpoint", "method"]
)

# Documentos recuperados por estrategia (bm25, knn, rrf)
RETRIEVAL_K = Gauge(
    "retriever_docs_returned", "Docs devueltos tras fusión",
    labelnames=["strategy"]
)