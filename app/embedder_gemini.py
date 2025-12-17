"""
app/embedder_gemini.py
Agrega fallback a Azure OpenAI embeddings si Gemini falla o no está disponible.
"""
import os
from typing import List, Any

import google.generativeai as genai
from openai import AzureOpenAI


class GeminiEmbedder:
    def __init__(self):
        gapi = os.getenv("GOOGLE_API_KEY")
        gkey = os.getenv("GEMINI_API_KEY")
        if gapi and gkey:
            print("Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.", flush=True)
        api_key = gapi or gkey
        if not api_key:
            raise ValueError("Missing GOOGLE_API_KEY or GEMINI_API_KEY")
        genai.configure(api_key=api_key)

        # Default model; allow override via env. 0.8.3 requires 'models/' prefix.
        model = os.getenv("GEMINI_EMBED_MODEL", "models/text-embedding-004")
        self.model_name = self._ensure_model_prefix(model)

        # Azure OpenAI (optional fallback)
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_key = os.getenv("AZURE_OPENAI_KEY")
        self.azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
        self.azure_embed_deployment = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
        self.azure_client = None
        if self.azure_endpoint and self.azure_key and self.azure_embed_deployment:
            try:
                self.azure_client = AzureOpenAI(
                    api_key=self.azure_key,
                    api_version=self.azure_api_version,
                    azure_endpoint=self.azure_endpoint,
                )
                print("Azure OpenAI embeddings enabled as fallback.", flush=True)
            except Exception as e:
                print(f"Azure OpenAI embeddings not configured ({e}). Continuing with Gemini only.", flush=True)

    def _ensure_model_prefix(self, name: str) -> str:
        if name.startswith("models/") or name.startswith("tunedModels/"):
            return name
        return f"models/{name}"

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

    def _extract_embedding(self, resp: dict) -> List[float]:
        # Handle common response shapes across versions:
        # - {'embedding': {'values': [...]}}  (google-generativeai 0.8.x)
        # - {'embedding': [...]}             (newer versions)
        # - {'data': [{'embedding': [...]}]} (rare legacy/batch shapes)
        if isinstance(resp, dict):
            emb = resp.get("embedding")
            if isinstance(emb, dict) and "values" in emb and isinstance(emb["values"], list):
                return emb["values"]
            if isinstance(emb, list):
                return emb
            if "data" in resp and isinstance(resp["data"], list) and resp["data"]:
                first = resp["data"][0]
                if isinstance(first, dict) and isinstance(first.get("embedding"), list):
                    return first["embedding"]
        # Last resort: safe zero vector
        return [0.0] * 768

    def _embed_one(self, text: str) -> List[float]:
        # Try Gemini first; fall back to Azure OpenAI if available.
        try:
            resp = genai.embed_content(model=self.model_name, content=text)
            return self._extract_embedding(resp)
        except Exception as e:
            # Try fallback Gemini model
            fallback = "models/embedding-001"
            if self.model_name != fallback:
                try:
                    resp = genai.embed_content(model=fallback, content=text)
                    return self._extract_embedding(resp)
                except Exception:
                    pass
            # Try Azure OpenAI if configured
            if self.azure_client and self.azure_embed_deployment:
                try:
                    resp = self.azure_client.embeddings.create(
                        model=self.azure_embed_deployment,
                        input=text,
                    )
                    data = getattr(resp, "data", None) or []
                    if data and hasattr(data[0], "embedding"):
                        return list(data[0].embedding)
                except Exception:
                    pass
            # If all fail, re-raise original error
            raise e

    def embed_texts(self, texts: List[Any]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for t in texts:
            clean = self._normalize_text(t)
            vectors.append(self._embed_one(clean))
        return vectors