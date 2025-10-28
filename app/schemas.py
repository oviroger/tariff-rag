from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Fragment schema para OCR/ingesta ---
class Fragment(BaseModel):
    """Fragmento de texto para ingesta en OpenSearch"""
    fragment_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None

class Citation(BaseModel):
    """Evidencia recuperada del retriever"""
    fragment_id: str = Field(..., description="ID del fragmento recuperado")
    score: float = Field(..., ge=0.0, description="Score de similaridad")
    text: Optional[str] = Field(None, description="Texto del fragmento (opcional)")
    reason: Optional[str] = Field(None, description="Razón de relevancia")

class EvidenceFragment(BaseModel):
    """Fragmento de evidencia para clasificación"""
    fragment_id: Optional[str] = None
    score: Optional[float] = None
    text: Optional[str] = None
    bucket: Optional[str] = None
    unit: Optional[str] = None
    doc_id: Optional[str] = None
    reason: Optional[str] = None

class Candidate(BaseModel):
    """Candidato de clasificación arancelaria"""
    code: str = Field(..., description="Código arancelario (ej: 3907.30.00)")
    description: Optional[str] = Field(None, description="Descripción del código")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confianza [0-1]")
    level: Optional[str] = Field(None, description="Nivel: heading/subheading/item")

class ClassifyResponse(BaseModel):
    """Respuesta del endpoint /classify"""
    top_candidates: List[Candidate] = Field(default_factory=list)
    evidence: List[EvidenceFragment] = Field(default_factory=list)
    support_evidence: List[EvidenceFragment] = Field(default_factory=list)
    applied_rgi: List[str] = Field(default_factory=list, description="RGI aplicadas")
    inclusions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    versions: Dict[str, str] = Field(default_factory=dict)
    debug_info: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    """Respuesta del health check"""
    status: str = Field(..., description="ok | degraded | fail")
    services: Dict[str, Any] = Field(default_factory=dict)

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
