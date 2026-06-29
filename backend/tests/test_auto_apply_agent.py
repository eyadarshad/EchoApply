import os
import time
import pytest
import threading
import uvicorn
from app.main import app
from app.schemas import ResumeParsedData
from app.services.browser_agent import run_auto_apply_agent

# Run the test server in a background thread
@pytest.fixture(scope="module", autouse=True)
def test_server():
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error"),
        daemon=True
    )
    server_thread.start()
    time.sleep(1.5)  # Wait for server to start
    yield

@pytest.mark.asyncio
async def test_auto_apply_success():
    """Test successful auto-fill and submission on the standard mock form."""
    profile = ResumeParsedData(
        name="Eyad Ahmed Test",
        email="eyad.test@example.com",
        phone="+1234567890",
        links=["https://github.com/eyadtest"],
        skills=["Python", "FastAPI"],
        education=[],
        experience=[],
        projects=[]
    )
    
    answers = {
        "How many years of experience do you have with FastAPI?": "I have 3 years of FastAPI experience.",
        "What is your expected salary?": "$120,000",
        "Do you agree to the terms of service?": "yes"
    }
    
    # Path for files to clean up
    filled_screenshot = "d:/Project 101/auto_apply_filled.png"
    if os.path.exists(filled_screenshot):
        os.remove(filled_screenshot)
        
    url = "http://127.0.0.1:8001/mock-apply-form"
    res = await run_auto_apply_agent(url, profile, answers)
    
    assert res["status"] == "success"
    assert "application_id" in res
    assert os.path.exists(filled_screenshot)

@pytest.mark.asyncio
async def test_auto_apply_login_block():
    """Test that a login page triggers the login_required blocker."""
    profile = ResumeParsedData(
        name="Eyad Ahmed Test",
        email="eyad.test@example.com",
        phone="+1234567890",
        links=[]
    )
    
    blocked_screenshot = "d:/Project 101/auto_apply_blocked.png"
    if os.path.exists(blocked_screenshot):
        os.remove(blocked_screenshot)
        
    url = "http://127.0.0.1:8001/mock-apply-form?login=true"
    res = await run_auto_apply_agent(url, profile, {})
    
    assert res["status"] == "needs_action"
    assert res["action_required"]["type"] == "login_required"
    assert "login screen" in res["action_required"]["message"].lower()
    assert os.path.exists(blocked_screenshot)

@pytest.mark.asyncio
async def test_auto_apply_captcha_block():
    """Test that a CAPTCHA page triggers the captcha_detected blocker."""
    profile = ResumeParsedData(
        name="Eyad Ahmed Test",
        email="eyad.test@example.com",
        phone="+1234567890",
        links=[]
    )
    
    blocked_screenshot = "d:/Project 101/auto_apply_blocked.png"
    if os.path.exists(blocked_screenshot):
        os.remove(blocked_screenshot)
        
    url = "http://127.0.0.1:8001/mock-apply-form?captcha=true"
    res = await run_auto_apply_agent(url, profile, {})
    
    assert res["status"] == "needs_action"
    assert res["action_required"]["type"] == "captcha_detected"
    assert "captcha" in res["action_required"]["message"].lower()
    assert os.path.exists(blocked_screenshot)

@pytest.mark.asyncio
async def test_auto_apply_unmapped_required_field_block():
    """Test that missing required fields trigger the unmapped_fields blocker."""
    profile = ResumeParsedData(
        name="Eyad Ahmed Test",
        email="eyad.test@example.com",
        phone="+1234567890",
        links=[]
    )
    
    # We do not provide the answer for the "favorite_language" field which is required when unmapped=true
    answers = {
        "How many years of experience do you have with FastAPI?": "I have 3 years of FastAPI experience.",
        "What is your expected salary?": "$120,000"
    }
    
    blocked_screenshot = "d:/Project 101/auto_apply_blocked.png"
    if os.path.exists(blocked_screenshot):
        os.remove(blocked_screenshot)
        
    url = "http://127.0.0.1:8001/mock-apply-form?unmapped=true"
    res = await run_auto_apply_agent(url, profile, answers)
    
    assert res["status"] == "needs_action"
    assert res["action_required"]["type"] == "unmapped_fields"
    assert "favorite coding language" in res["action_required"]["message"].lower()
    assert os.path.exists(blocked_screenshot)
