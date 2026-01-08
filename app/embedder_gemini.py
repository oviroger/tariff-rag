"""
app/embedder_gemini.py
Azure-only embedding wrapper (previously Gemini).
"""
import os
from typing import List, Any

from openai import AzureOpenAI


class GeminiEmbedder:
    def __init__(self):
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_key = os.getenv("AZURE_OPENAI_KEY")
        self.azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
        self.azure_embed_deployment = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
        if not (self.azure_endpoint and self.azure_key and self.azure_embed_deployment):
            raise ValueError("Missing AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_KEY/AZURE_OPENAI_EMBED_DEPLOYMENT")
        self.azure_client = AzureOpenAI(
            api_key=self.azure_key,
            api_version=self.azure_api_version,
            azure_endpoint=self.azure_endpoint,
        )

    def _normalize_text(self, x: Any) -> str:
        # Ensure we always pass a non-empty string to the embeddings endpoint
        if x is None:
            return " "
        if isinstance(x, str):
            return x if x.strip() else " "
        if isinstance(x, dict):
            for k in ("text", "content", "body"):
                v = x.get(k)
                if isinstance(v, str) and v.strip():
                    return v
        s = str(x)
        return s if s.strip() else " "

    def _embed_one(self, text: str) -> List[float]:
        resp = self.azure_client.embeddings.create(
            model=self.azure_embed_deployment,
            input=text,
        )
        data = getattr(resp, "data", None) or []
        if data and hasattr(data[0], "embedding"):
            return list(data[0].embedding)
        # Last resort: safe zero vector to avoid crashes
        return [0.0] * 768

    def embed_texts(self, texts: List[Any]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for t in texts:
            clean = self._normalize_text(t)
            vectors.append(self._embed_one(clean))
        return vectors