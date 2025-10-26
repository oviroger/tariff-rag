from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Fragment schema para OCR/ingesta ---
class Fragment(BaseModel):
    fragment_id: str
    source: str  # "DOC" | "DB" | etc.
    doc_id: str
    chapter: Optional[str] = None
    heading: Optional[str] = None
    subheading: Optional[str] = None
    unit: Optional[str] = None  # "ARTICLE", "SECTION", "DB_ROW", etc.
    text: str
    edition: Optional[str] = None
    validity_from: Optional[str] = None
    validity_to: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ClassifyRequest(BaseModel):
    text: Optional[str] = None
    file_url: Optional[HttpUrl] = None
    top_k: int = Field(default=5, ge=1, le=20)
    debug: bool = False

class Citation(BaseModel):
    id: str
    score: float
    snippet: str

class ClassifyResponse(BaseModel):
    label: str
    score: float
    reasons: List[str] = []
    citations: List[Citation] = []
    debug: Optional[dict] = None

class HealthResponse(BaseModel):
    status: str = "ok"

class Settings(BaseSettings):
    # CORS / App
    allow_origins: str = "*"
    app_port: int = 8000

    # OpenSearch (alineado con .env / docker-compose)
    opensearch_host: str = "http://opensearch:9200"
    opensearch_index: str = "tariff_fragments"
    opensearch_knn_space: str = "cosinesimil"
    opensearch_emb_dim: int = 768

    # MySQL
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_db: str = "corpusdb"
    mysql_user: str = "appuser"
    mysql_password: str = "apppass"

    # Gemini
    gemini_api_key: str | None = None
    gemini_embed_model: str = "text-embedding-004"
    gemini_model: str = "gemini-1.5-pro"

    # Azure Form Recognizer
    azure_formrec_endpoint: str | None = None
    azure_formrec_key: str | None = None
    azure_fr_model: str = "prebuilt-layout"

    # Parámetros de la app (si los usas en tu lógica)
    final_pasages: int = 6
    min_evidence: int = 2
    min_score: float = 0.35

    # Lee variables desde .env cuando corre fuera de Docker;
    # en Docker vendrán por environment del servicio 'api'
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
