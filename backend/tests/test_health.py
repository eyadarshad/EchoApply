from unittest.mock import patch
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

@patch("app.main.tailor_resume_flow")
def test_tailor_stub_endpoint(mock_tailor):
    # Setup mock return to avoid LLM & DB calls
    mock_tailor.return_value = {
        "content_json": {
            "name": "Eyad Ahmed",
            "email": "eyad.ahmed@example.com",
            "phone": "+92-300-1234567",
            "links": ["github.com/eyad-dev"],
            "skills": ["Python", "FastAPI"],
            "education": [],
            "experience": [],
            "projects": [],
            "anchor_line": "Backend Engineer specializing in FastAPI",
            "highlights_strip": []
        },
        "gap_analysis": {
            "matched_skills": ["Python", "FastAPI"],
            "missing_skills": [],
            "partial_matches": []
        },
        "truthfulness_report": {
            "is_fabricated": False,
            "verification_report": []
        },
        "ats_score": 90
    }
    payload = {
        "user_id": "user-123",
        "job_id": "job-456",
        "jd_text": "We want a FastAPI developer",
        "parsed_resume": {
            "name": "Eyad Ahmed",
            "email": "eyad.ahmed@example.com",
            "skills": ["Python", "FastAPI"]
        }
    }
    response = client.post("/tailor", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user-123"
    assert data["job_id"] == "job-456"
    assert "resume_id" in data
    assert "content_json" in data
    assert data["ats_score"] == 90

def test_jobs_search_stub_endpoint():
    payload = {
        "query": "FastAPI Developer",
        "location": "Remote",
        "remote_only": True,
        "limit": 10
    }
    response = client.post("/jobs/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "query_hash" in data
    assert len(data["jobs"]) > 0
    assert data["jobs"][0]["title"] == "Backend Developer"
    assert data["jobs"][0]["remote"] is True

def test_apply_draft_stub_endpoint():
    payload = {
        "user_id": "user-123",
        "job_id": "job-456"
    }
    response = client.post("/apply/draft", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job-456"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question_id"] == "q1"

def test_apply_submit_stub_endpoint():
    payload = {
        "user_id": "user-123",
        "job_id": "job-456",
        "answers": {"q1": "I have 2 years of experience"},
        "opt_in_agent": False
    }
    response = client.post("/apply/submit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "application_id" in data
    assert data["status"] == "success"
