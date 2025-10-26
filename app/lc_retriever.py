from langchain.schema import Document
from app.embedder_gemini import embed_texts
from app.os_retrieval import bm25_search, knn_search, rrf_fusion

def retrieve_docs(query: str, k_bm25=12, k_knn=12, topn=24, final_k=6) -> list[Document]:
    qvec = embed_texts([query])[0]
    bm = bm25_search(query, size=k_bm25)
    kn = knn_search(qvec, size=k_knn)
    fused = rrf_fusion(bm, kn, k=60, topn=topn)
    fused = fused[:final_k]
    docs = []
    for f in fused:
        meta = {k:f[k] for k in ["fragment_id","source","doc_id","chapter","heading","subheading","unit","edition","validity_from","validity_to"] if k in f}
        docs.append(Document(page_content=f["text"], metadata=meta))
    return docs
