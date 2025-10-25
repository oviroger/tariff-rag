from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .schemas import ClassifyRequest, ClassifyResponse, HealthResponse, Citation
from .config import get_settings
from .chain_rag import classify

app = FastAPI(title="tariff-rag", version="0.1.0")
s = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in s.allow_origins.split(",")] if getattr(s, "allow_origins", "*") else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()

@app.post("/classify", response_model=ClassifyResponse)
def classify_endpoint(req: ClassifyRequest):
    result = classify(req.text, req.file_url, top_k=req.top_k, debug=req.debug)
    return ClassifyResponse(
        label=result["label"],
        score=result["score"],
        reasons=result.get("reasons", []),
        citations=[Citation(**c) for c in result.get("citations", [])],
        debug=result.get("debug"),
    )