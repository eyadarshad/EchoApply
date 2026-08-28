import pytest
import psycopg
import asyncio
from app.config import settings
from app.utils import get_platform_cookies
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_db_connection():
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=1)
        return conn
    except Exception:
        return None

db_available = get_db_connection() is not None

@pytest.mark.skipif(not db_available, reason="PostgreSQL database is unreachable")
@pytest.mark.asyncio
async def test_cookie_sync_and_retrieval():
    user_id = "00000000-0000-0000-0000-000000000099"
    
    # 1. Create a dummy user first to satisfy foreign key
    conn = psycopg.connect(settings.DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;",
            (user_id, "cookie_test@example.com")
        )
        conn.commit()
        
    try:
        # 2. Sync cookies via endpoint
        payload = {
            "user_id": user_id,
            "cookies": [
                {
                    "platform": "linkedin",
                    "name": "li_at",
                    "value": "dummy-session-cookie-value",
                    "domain": ".linkedin.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "expirationDate": 1893456000.0
                }
            ]
        }
        
        res = client.post("/api/auth/extension-sync", json=payload, headers={"X-Dev-User-Id": user_id})
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        
        # 3. Retrieve and decrypt cookies
        cookies = await get_platform_cookies(user_id, "linkedin")
        assert len(cookies) == 1
        assert cookies[0]["name"] == "li_at"
        assert cookies[0]["value"] == "dummy-session-cookie-value"
        assert cookies[0]["domain"] == ".linkedin.com"
        assert cookies[0]["expirationDate"] == 1893456000.0
        
    finally:
        # 4. Clean up test records
        with conn.cursor() as cur:
            cur.execute("DELETE FROM platform_credentials WHERE user_id = %s;", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
            conn.commit()
        conn.close()
