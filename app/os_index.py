from opensearchpy import OpenSearch
import os

def os_client() -> OpenSearch:
    host = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
    return OpenSearch(
        hosts=[host],
        use_ssl=host.startswith("https://"),
        verify_certs=False
    )