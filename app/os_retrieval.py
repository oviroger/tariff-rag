from app.os_index import os_client
from app.config import SET
from app.metrics import RETRIEVAL_K
from heapq import nlargest

def bm25_search(query: str, size=20) -> list[dict]:
    client = os_client()
    resp = client.search(index=SET.os_index, body={
        "size": size,
        "query": {"match": {"text": query}},
        "_source": True
    })
    hits = resp["hits"]["hits"]
    return [{"_id":h["_id"], "score":h["_score"], **h["_source"]} for h in hits]

def knn_search(query_vec: list[float], size=20) -> list[dict]:
    client = os_client()
    resp = client.search(index=SET.os_index, body={
        "size": size,
        "query": {
          "knn": {
            "embedding": {
              "vector": query_vec,
              "k": size
            }
          }
        },
        "_source": True
    })
    hits = resp["hits"]["hits"]
    return [{"_id":h["_id"], "score":h["_score"], **h["_source"]} for h in hits]

def rrf_fusion(list_a: list[dict], list_b: list[dict], k=60, topn=24) -> list[dict]:
    """
    RRF clásico: score += 1/(k + rank)
    """
    pos_a = {d["_id"]:i for i,d in enumerate(list_a)}
    pos_b = {d["_id"]:i for i,d in enumerate(list_b)}
    ids = set(pos_a) | set(pos_b)
    fused = []
    for _id in ids:
        ra = pos_a.get(_id, 10**9)
        rb = pos_b.get(_id, 10**9)
        score = 1.0/(k+ra+1) + 1.0/(k+rb+1)
        fused.append((_id, score))
    top_ids = [t[0] for t in nlargest(topn, fused, key=lambda x: x[1])]
    # materializa docs
    idx = {d["_id"]:d for d in list_a + list_b}
    return [idx[i] for i in top_ids]

# ... dentro de tu función retrieve(...) después de obtener listas:
# bm = resultados BM25, kn = resultados kNN, fused = lista final fusionada (RRF)
RETRIEVAL_K.labels("bm25").set(len(bm) if 'bm' in locals() else 0)
RETRIEVAL_K.labels("knn").set(len(kn) if 'kn' in locals() else 0)
RETRIEVAL_K.labels("rrf").set(len(fused) if 'fused' in locals() else 0)
