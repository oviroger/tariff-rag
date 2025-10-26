from fastapi.testclient import TestClient
from app.api import app

def test_root():
    """Test endpoint raíz"""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data

def test_health_check():
    """Test health check con lifespan"""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "opensearch" in data["services"]
        assert "mysql" in data["services"]
        assert "gemini" in data["services"]

def test_classify_validation_min_length():
    """Test validación de longitud mínima"""
    with TestClient(app) as client:
        response = client.post("/classify", json={"text": "corto"})
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

def test_classify_validation_required():
    """Test campo text requerido"""
    with TestClient(app) as client:
        response = client.post("/classify", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

def test_classify_validation_max_length():
    """Test validación de longitud máxima"""
    with TestClient(app) as client:
        long_text = "a" * 5000  # Más de 4000 caracteres
        response = client.post("/classify", json={"text": long_text})
        assert response.status_code == 422

def test_classify_success_stub():
    """Test clasificación exitosa (con datos stub)"""
    with TestClient(app) as client:
        response = client.post("/classify", json={
            "text": "Resina epoxi líquida en bidones de 25kg para uso industrial en recubrimientos protectores",
            "top_k": 3,
            "debug": True
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de respuesta
        assert "top_candidates" in data
        assert "evidence" in data
        assert "warnings" in data
        assert "applied_rgi" in data
        assert "missing_fields" in data
        
        # Verificar tipos
        assert isinstance(data["top_candidates"], list)
        assert isinstance(data["evidence"], list)
        assert isinstance(data["warnings"], list)

def test_classify_with_versions():
    """Test con versión HS específica"""
    with TestClient(app) as client:
        response = client.post("/classify", json={
            "text": "Resina epoxi en escamas para uso industrial",
            "versions": {"hs_edition": "HS_2017"},
            "top_k": 5
        })
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data

def test_classify_boundary_conditions():
    """Test condiciones límite"""
    with TestClient(app) as client:
        # Texto mínimo válido
        response = client.post("/classify", json={
            "text": "Producto X"  # 10 caracteres exactos
        })
        assert response.status_code == 200
        
        # top_k mínimo
        response = client.post("/classify", json={
            "text": "Resina epoxi industrial",
            "top_k": 1
        })
        assert response.status_code == 200
        
        # top_k máximo
        response = client.post("/classify", json={
            "text": "Resina epoxi industrial",
            "top_k": 20
        })
        assert response.status_code == 200

def test_classify_invalid_top_k():
    """Test top_k fuera de rango"""
    with TestClient(app) as client:
        # top_k = 0 (menor que 1)
        response = client.post("/classify", json={
            "text": "Resina epoxi industrial",
            "top_k": 0
        })
        assert response.status_code == 422
        
        # top_k = 21 (mayor que 20)
        response = client.post("/classify", json={
            "text": "Resina epoxi industrial",
            "top_k": 21
        })
        assert response.status_code == 422
