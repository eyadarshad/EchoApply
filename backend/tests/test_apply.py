import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)

def test_draft_answers_success():
    """Verify that /apply/draft drafts answers to screening questions."""
    user_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "job_id": str(uuid.uuid4())
    }
    
    response = client.post("/apply/draft", json=payload, headers={"X-Dev-User-Id": user_id})
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "questions" in data
    assert len(data["questions"]) > 0
    
    # Assert fields are present
    for q in data["questions"]:
        assert "question_id" in q
        assert "question_text" in q
        assert "drafted_answer" in q
        assert "confidence" in q
        assert "needs_user_input" in q

def test_submit_application_success():
    """Verify that /apply/submit records applications successfully."""
    user_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    payload = {
        "user_id": user_id,
        "job_id": job_id,
        "answers": {
            "q1": "I have 2 years of experience.",
            "q2": "None required."
        },
        "opt_in_agent": False
    }
    
    response = client.post("/apply/submit", json=payload, headers={"X-Dev-User-Id": user_id})
    assert response.status_code == 200
    data = response.json()
    assert "application_id" in data
    assert data["status"] == "success"

@patch("psycopg.connect")
def test_submit_application_duplicate(mock_connect):
    """Verify duplicate applications are handled idempotently."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    # Mock check showing application already exists
    mock_cur.fetchone.return_value = ("existing-app-id",)
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_connect.return_value = mock_conn

    user_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    payload = {
        "user_id": user_id,
        "job_id": job_id,
        "answers": {
            "q1": "I have 2 years of experience."
        },
        "opt_in_agent": False
    }
    
    response = client.post("/apply/submit", json=payload, headers={"X-Dev-User-Id": user_id})
    assert response.status_code == 200
    data = response.json()
    assert "application_id" in data
    assert data["status"] == "success"
