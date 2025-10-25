from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # CORS / App
    allow_origins: str = "*"
    app_port: int = 8000

    # OpenSearch
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

    # Parámetros de la app
    final_pasages: int = 6
    min_evidence: int = 2
    min_score: float = 0.35

    # lee .env fuera de Docker; en Docker vienen por env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
