import pytest
from fastapi.testclient import TestClient
from app.main import app

import psycopg
from app.config import settings

client = TestClient(app)

def get_db_connection():
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=1)
        return conn
    except Exception:
        return None

db_available = get_db_connection() is not None

@pytest.fixture(scope="module", autouse=True)
def setup_mock_user():
    if not db_available:
        yield
        return
    user_id = "00000000-0000-0000-0000-000000000001"
    conn = psycopg.connect(settings.DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (id, email, created_at) VALUES (%s, %s, NOW());",
                (user_id, "mock_test_user@example.com")
            )
            conn.commit()
    conn.close()
    
    yield
    
    conn = psycopg.connect(settings.DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
        conn.commit()
    conn.close()

@pytest.mark.skipif(not db_available, reason="PostgreSQL database is unreachable")
def test_billing_endpoints():
    user_id = "00000000-0000-0000-0000-000000000001"
    headers = {"X-Dev-User-Id": user_id}
    
    # 1. Get status
    res = client.get(f"/api/billing/status?user_id={user_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "tier" in data
    assert "status" in data

    # 2. Checkout
    res = client.post(
        "/api/billing/checkout",
        json={
            "user_id": user_id,
            "tier": "pro",
            "success_url": "http://localhost:3000/billing",
            "cancel_url": "http://localhost:3000/"
        },
        headers=headers
    )
    assert res.status_code == 200
    assert "checkout_url" in res.json()

@pytest.mark.skipif(not db_available, reason="PostgreSQL database is unreachable")
def test_job_alerts_endpoints():
    user_id = "00000000-0000-0000-0000-000000000001"
    headers = {"X-Dev-User-Id": user_id}
    
    # 1. Create alert
    res = client.post(
        "/api/jobs/alerts",
        json={
            "user_id": user_id,
            "keywords": "Software Engineer",
            "location": "Remote",
            "alert_interval": "weekly"
        },
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["keywords"] == "Software Engineer"
    alert_id = data["id"]

    # 2. List alerts
    res = client.get(f"/api/jobs/alerts?user_id={user_id}", headers=headers)
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) > 0

    # 3. Trigger alert check scan
    from unittest.mock import patch
    with patch("app.tasks.run_job_alerts_check") as mock_run:
        mock_run.return_value = {"status": "success", "processed_alerts": 1, "matches": []}
        res = client.post("/api/jobs/alerts/run-check")
        assert res.status_code == 200
        check_data = res.json()
        assert "processed_alerts" in check_data

    # 4. Delete alert
    res = client.delete(f"/api/jobs/alerts/{alert_id}", headers=headers)
    assert res.status_code == 200

@pytest.mark.skipif(not db_available, reason="PostgreSQL database is unreachable")
def test_analytics_endpoint():
    user_id = "00000000-0000-0000-0000-000000000001"
    headers = {"X-Dev-User-Id": user_id}
    res = client.get(f"/api/analytics/summary?user_id={user_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_applied" in data
    assert "conversion_funnel" in data
    assert "avg_ats_score" in data

@pytest.mark.skipif(not db_available, reason="PostgreSQL database is unreachable")
def test_interview_endpoints():
    user_id = "00000000-0000-0000-0000-000000000001"
    headers = {"X-Dev-User-Id": user_id}
    payload = {
        "user_id": user_id,
        "job_title": "React Developer",
        "jd_text": "Requirements: 3 years experience building frontends using React and Next.js."
    }
    
    # 1. Questions
    res = client.post("/api/interview/questions", json=payload, headers=headers)
    assert res.status_code == 200
    questions = res.json()["questions"]
    assert len(questions) == 5

    # 2. Grade
    grade_payload = {
        "question": questions[0],
        "answer": "In my previous project at Google, I migrated our landing page to React. This improved performance by 40%."
    }
    res = client.post("/api/interview/grade", json=grade_payload, headers=headers)
    assert res.status_code == 200
    grade_data = res.json()
    assert "score" in grade_data
    assert "star_compliance" in grade_data
