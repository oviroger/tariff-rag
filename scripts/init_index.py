# scripts/init_index.py
from opensearchpy import OpenSearch
import os

def main():
    host = os.environ.get("OPENSEARCH_HOST", "http://localhost:9200")
    index = os.environ.get("OPENSEARCH_INDEX", "tariff_fragments")
    dim   = int(os.environ.get("OPENSEARCH_EMB_DIM", "768"))
    space = os.environ.get("OPENSEARCH_KNN_SPACE", "cosinesimil")

    print(f"[init_index] OPENSEARCH_HOST={host} INDEX={index} DIM={dim} SPACE={space}")

    client = OpenSearch(hosts=[host], verify_certs=False)

    if client.indices.exists(index):
        print(f"Índice '{index}' ya existe.")
        return

    body = {
        "settings": { "index": { "knn": True } },
        "mappings": {
            "properties": {
                "fragment_id": {"type":"keyword"},
                "source": {"type":"keyword"},
                "doc_id": {"type":"keyword"},
                "chapter": {"type":"keyword"},
                "heading": {"type":"keyword"},
                "subheading": {"type":"keyword"},
                "unit": {"type":"keyword"},
                "text": {"type":"text"},
                "edition": {"type":"keyword"},
                "validity_from": {
                    "type":"date",
                    "format":"strict_date_optional_time||epoch_millis"
                },
                "validity_to": {
                    "type":"date",
                    "format":"strict_date_optional_time||epoch_millis"
                },
                "metadata": {"type":"object","enabled": True},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name":"hnsw",
                        "space_type": space,
                        "engine":"nmslib"
                    }
                }
            }
        }
    }
    client.indices.create(index=index, body=body)
    print(f"Índice '{index}' creado.")

if __name__ == "__main__":
    main()