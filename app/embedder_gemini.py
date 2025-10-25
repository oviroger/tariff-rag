from typing import List
import google.genai as genai
from .config import get_settings

class GeminiEmbedder:
    def __init__(self):
        s = get_settings()
        if not s.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada.")
        self.client = genai.Client(api_key=s.gemini_api_key)
        self.model_name = s.gemini_embed_model  # "text-embedding-004"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        out: List[List[float]] = []
        for t in texts:
            resp = self.client.models.embed_content(model=self.model_name, content=t)
            out.append(resp.embedding.values)
        return out

    def embed_query(self, text: str) -> List[float]:
        resp = self.client.models.embed_content(model=self.model_name, content=text)
        return resp.embedding.values