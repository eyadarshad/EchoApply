from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data

def test_echo_endpoint_success():
    payload = {"message": "Testing the connection"}
    response = client.post("/echo", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Testing the connection"
    assert data["status"] == "success"
    assert "timestamp" in data

def test_echo_endpoint_validation_error():
    # Empty payload or wrong schema format
    payload = {"wrong_key": "Should fail"}
    response = client.post("/echo", json=payload)
    assert response.status_code == 422  # Unprocessable Entity
