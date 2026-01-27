from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # CORS / App
    allow_origins: str = "*"
    app_port: int = 8000

    # OpenSearch
    opensearch_host: str = "http://opensearch:9200"
    opensearch_index: str = "tariff_fragments_2025"
    opensearch_indices: str = "tariff_fragments_2025,tariff_fragments_2026"
    opensearch_knn_space: str = "cosinesimil"
    opensearch_emb_dim: int = 1536

    # MySQL
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_db: str = "corpusdb"
    mysql_user: str = "appuser"
    mysql_password: str = "apppass"

    # Gemini
    gemini_api_key: str | None = None
    gemini_embed_model: str = "text-embedding-004"
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.3
    gemini_top_p: float = 0.9
    gemini_top_k: int = 40
    gemini_max_output_tokens: int = 2048

    # Candidatos HS
    min_candidate_confidence: float = 0.70

    # Azure Form Recognizer
    azure_formrec_endpoint: str | None = None
    azure_formrec_key: str | None = None
    azure_fr_model: str = "prebuilt-layout"

    # Azure OpenAI (fallback/second option)
    azure_openai_endpoint: str = "https://kpofoundry.cognitiveservices.azure.com"
    azure_openai_key: str | None = None
    azure_openai_api_version: str = "2024-05-01-preview"
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_embed_deployment: str = "text-embedding-3-small"

    # Parámetros de la app
    final_pasages: int = 6
    min_evidence: int = 2
    min_score: float = 0.35
    enable_retrieval_fallback: bool = False

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # lee .env fuera de Docker; en Docker vienen por env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
