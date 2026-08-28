import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.llm_client import llm_client
from app.services.llm_prompts import CHATBOT_SYSTEM

client = TestClient(app)

def test_central_prompts_and_chatbot_system():
    # Verify prompt registry loads properly
    assert CHATBOT_SYSTEM is not None
    assert "echo apply" in CHATBOT_SYSTEM.lower()

@patch("app.services.llm_client.genai.Client")
@patch("httpx.Client")
def test_llm_fallback_chain_gemini_failure(mock_httpx_client_class, mock_genai_client_class):
    from app.services.circuit_breaker import CIRCUIT_REGISTRY
    CIRCUIT_REGISTRY.clear()
    
    # Mock Gemini client to throw exception on generate_content
    mock_gemini_instance = MagicMock()
    mock_genai_client_class.return_value = mock_gemini_instance
    mock_gemini_instance.models.generate_content.side_effect = Exception("Gemini API is offline")

    # Mock httpx.Client post method for OpenRouter fallback
    mock_client_instance = MagicMock()
    mock_httpx_client_class.return_value.__enter__.return_value = mock_client_instance
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "OpenRouter Fallback Response Text"
                }
            }
        ]
    }
    mock_client_instance.post.return_value = mock_response

    # Call generate_text
    res = llm_client.generate_text("Hello Test", "flash", "System Instruction")
    
    # Assert fallback worked and called OpenRouter API via httpx client instance
    assert res == "OpenRouter Fallback Response Text"
    assert mock_client_instance.post.called

def test_security_middleware_request_size_limit():
    # Body larger than 10MB should trigger 413
    large_payload = "A" * (11 * 1024 * 1024)  # 11MB
    response = client.post("/echo", content=large_payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert "too large" in response.json().get("detail", "").lower()

def test_security_middleware_content_type_validation():
    # POST with unsupported media type should trigger 415
    response = client.post("/echo", content="{}", headers={"Content-Type": "text/html", "Content-Length": "2"})
    assert response.status_code == 415
    assert "unsupported media type" in response.json().get("detail", "").lower()

def test_dev_bypass_disabled_in_production():
    with patch("os.getenv", side_effect=lambda key, default=None: "production" if key == "ENVIRONMENT" else default):
        payload = {
            "user_id": "12345678-1234-1234-1234-123456789012",
            "parsed_resume": {"name": "Test User", "email": "test@example.com"}
        }
        response = client.post("/profiles", json=payload, headers={"X-Dev-User-Id": "12345678-1234-1234-1234-123456789012"})
        # Should reject bypass and return 401 Unauthorized since Dev Bypass is disabled in prod
        assert response.status_code == 401

@patch("app.services.llm_client.genai.Client")
@patch("httpx.Client")
def test_llm_fallback_chain_tertiary_fallback(mock_httpx_client_class, mock_genai_client_class):
    from app.services.circuit_breaker import CIRCUIT_REGISTRY
    CIRCUIT_REGISTRY.clear()

    # Mock Gemini client to throw exception
    mock_gemini_instance = MagicMock()
    mock_genai_client_class.return_value = mock_gemini_instance
    mock_gemini_instance.models.generate_content.side_effect = Exception("Gemini API is offline")

    # Mock httpx.Client post method
    mock_client_instance = MagicMock()
    mock_httpx_client_class.return_value.__enter__.return_value = mock_client_instance
    
    # We want post() to raise Exception for primary and secondary, but succeed for tertiary!
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Rate limit reached on OpenRouter model")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Tertiary Fallback Content"
                    }
                }
            ]
        }
        return mock_response
        
    mock_client_instance.post.side_effect = side_effect

    # Call generate_text
    res = llm_client.generate_text("Hello Test", "flash", "System Instruction")
    
    # Assert tertiary fallback was called and returned correct text
    assert res == "Tertiary Fallback Content"
    assert call_count == 3

