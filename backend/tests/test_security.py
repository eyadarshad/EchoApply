import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

@pytest.fixture
def clean_test_user_id():
    return "00000000-0000-0000-0000-000000000001"

@pytest.fixture
def secondary_test_user_id():
    return "00000000-0000-0000-0000-000000000002"

def test_security_response_headers():
    """Verify that backend HTTP responses contain security headers."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("Strict-Transport-Security") == "max-age=63072000; includeSubDomains"
    assert "default-src 'none'" in response.headers.get("Content-Security-Policy", "")

def test_unauthorized_endpoints(clean_test_user_id):
    """Verify that protected endpoints reject requests with no authentication."""
    endpoints_to_test = [
        ("POST", "/profiles", {"user_id": clean_test_user_id, "parsed_resume": {"name": "Eyad", "email": "eyad@example.com"}}),
        ("POST", "/tailor", {"user_id": clean_test_user_id, "job_id": "job-123"}),
        ("POST", "/apply/draft", {"user_id": clean_test_user_id, "job_id": "job123"}),
        ("POST", "/apply/submit", {"user_id": clean_test_user_id, "job_id": "job123"}),
        ("GET", f"/api/applications/{clean_test_user_id}", None),
        ("POST", "/api/applications/update-status", {"application_id": str(uuid.uuid4()), "status": "applied"}),
        ("GET", f"/api/billing/status?user_id={clean_test_user_id}", None),
        ("POST", "/api/billing/checkout", {"user_id": clean_test_user_id, "tier": "premium", "success_url": "http://success", "cancel_url": "http://cancel"}),
        ("GET", f"/api/jobs/alerts?user_id={clean_test_user_id}", None),
        ("POST", "/api/jobs/alerts", {"user_id": clean_test_user_id, "keywords": "Python"}),
        ("DELETE", f"/api/jobs/alerts/{str(uuid.uuid4())}", None),
        ("GET", f"/api/analytics/summary?user_id={clean_test_user_id}", None),
        ("POST", "/api/interview/questions", {"user_id": clean_test_user_id, "job_title": "Engineer", "jd_text": "Developer"}),
        ("POST", "/api/interview/grade", {"question": "q", "answer": "a"}),
        ("POST", "/api/screening/save", {"user_id": clean_test_user_id, "question": "q", "answer": "a"}),
        ("POST", "/api/screening/search", {"user_id": clean_test_user_id, "question": "q"}),
        ("DELETE", f"/api/user/delete?user_id={clean_test_user_id}", None),
    ]
    
    for method, path, json_data in endpoints_to_test:
        if method == "POST":
            response = client.post(path, json=json_data)
        elif method == "GET":
            response = client.get(path)
        elif method == "DELETE":
            response = client.delete(path)
        assert response.status_code == 401, f"{method} {path} should be protected by auth"

def test_bola_mismatched_user(clean_test_user_id, secondary_test_user_id):
    """Verify that requests with mismatched authentication fail with 403 Forbidden."""
    endpoints_to_test = [
        ("POST", "/profiles", {"user_id": clean_test_user_id, "parsed_resume": {"name": "Eyad", "email": "eyad@example.com"}}),
        ("POST", "/tailor", {"user_id": clean_test_user_id, "job_id": "job-123"}),
        ("POST", "/apply/draft", {"user_id": clean_test_user_id, "job_id": "job123"}),
        ("POST", "/apply/submit", {"user_id": clean_test_user_id, "job_id": "job123"}),
        ("GET", f"/api/applications/{clean_test_user_id}", None),
        ("GET", f"/api/billing/status?user_id={clean_test_user_id}", None),
        ("POST", "/api/billing/checkout", {"user_id": clean_test_user_id, "tier": "premium", "success_url": "http://success", "cancel_url": "http://cancel"}),
        ("GET", f"/api/jobs/alerts?user_id={clean_test_user_id}", None),
        ("POST", "/api/jobs/alerts", {"user_id": clean_test_user_id, "keywords": "Python"}),
        ("GET", f"/api/analytics/summary?user_id={clean_test_user_id}", None),
        ("POST", "/api/interview/questions", {"user_id": clean_test_user_id, "job_title": "Engineer", "jd_text": "Developer"}),
        ("POST", "/api/screening/save", {"user_id": clean_test_user_id, "question": "q", "answer": "a"}),
        ("POST", "/api/screening/search", {"user_id": clean_test_user_id, "question": "q"}),
        ("DELETE", f"/api/user/delete?user_id={clean_test_user_id}", None),
    ]

    headers = {"X-Dev-User-Id": secondary_test_user_id}
    
    for method, path, json_data in endpoints_to_test:
        if method == "POST":
            response = client.post(path, json=json_data, headers=headers)
        elif method == "GET":
            response = client.get(path, headers=headers)
        elif method == "DELETE":
            response = client.delete(path, headers=headers)
        assert response.status_code == 403, f"{method} {path} should restrict BOLA access"

def test_invalid_uuid_sanitization(clean_test_user_id):
    """Verify that invalid UUID formats are rejected with 400 Bad Request."""
    headers = {"X-Dev-User-Id": "invalid-uuid-format"}
    payload = {
        "user_id": "invalid-uuid-format",
        "parsed_resume": {"name": "Eyad", "email": "eyad@example.com"}
    }
    
    # Check profile endpoint with invalid user_id format
    response = client.post("/profiles", json=payload, headers=headers)
    assert response.status_code == 400
    assert "Invalid user ID" in response.json()["detail"]

@patch("app.main.psycopg.connect")
def test_delete_alert_bola_ownership(mock_connect, clean_test_user_id, secondary_test_user_id):
    """Verify that user A cannot delete an alert owned by user B."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # Mocking that the alert belongs to secondary_test_user_id
    mock_cur.fetchone.return_value = (secondary_test_user_id,)
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_connect.return_value = mock_conn
    
    alert_id = str(uuid.uuid4())
    headers = {"X-Dev-User-Id": clean_test_user_id}
    
    response = client.delete(f"/api/jobs/alerts/{alert_id}", headers=headers)
    assert response.status_code == 403
    assert "permission to delete" in response.json()["detail"]
