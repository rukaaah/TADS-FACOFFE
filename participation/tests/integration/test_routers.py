from fastapi.testclient import TestClient
from src.main import app
from src.api.security import get_current_user_payload

client = TestClient(app)

def test_create_quota_endpoint_returns_201():
    app.dependency_overrides[get_current_user_payload] = lambda: {"sub": "usr_manager", "roles": ["MANAGER"]}
    
    payload = {"name": "Cota Café", "condition": "DAILY", "items": "ALL", "amount": 50.0, "active": True}
    # Adicionado o header falso para passar pelo HTTPBearer
    response = client.post("/api/participation/quotas", json=payload, headers={"Authorization": "Bearer test_token"})
    
    assert response.status_code == 201
    app.dependency_overrides.clear()

def test_create_quota_authorization_fails_for_non_manager():
    app.dependency_overrides[get_current_user_payload] = lambda: {"sub": "usr_comum", "roles": ["PARTICIPANT"]}
    
    payload = {"name": "Cota Hacker", "condition": "DAILY", "items": "ALL", "amount": 10.0, "active": True}
    response = client.post("/api/participation/quotas", json=payload, headers={"Authorization": "Bearer test_token"})
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado. Nível de privilégio insuficiente."
    app.dependency_overrides.clear()

def test_join_participation_endpoint_returns_201():
    app.dependency_overrides[get_current_user_payload] = lambda: {"sub": "usr_part", "roles": ["PARTICIPANT"]}
    
    payload = {"userId": "usr_part", "quotaId": "quota_123", "startCycle": "2026-05"}
    response = client.post("/api/participation/participations", json=payload, headers={"Authorization": "Bearer test_token"})
    
    assert response.status_code == 201
    app.dependency_overrides.clear()