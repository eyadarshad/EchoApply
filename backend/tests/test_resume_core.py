import pytest
import fitz
import io
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ResumeParsedData
from app.parsers.pdf_parser import extract_text_from_pdf, extract_blocks_from_pdf, ScannedPDFError
from app.services.github_enricher import extract_github_username, enrich_profile_with_github
from app.services.resume_generator import generate_resume_pdf, generate_resume_docx

client = TestClient(app)

# Helper to build a real, simple PDF in-memory using fitz
def create_mock_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_extract_text_from_pdf_success():
    # Make sure text is longer than 100 characters to prevent ScannedPDFError
    test_text = "John Doe\nSoftware Engineer\nExperience at Google. " + ("Some additional placeholder text to ensure length limit of 100 characters is exceeded. " * 3)
    pdf_bytes = create_mock_pdf_bytes(test_text)
    
    extracted = extract_text_from_pdf(pdf_bytes)
    assert "John Doe" in extracted
    assert "Software Engineer" in extracted

def test_extract_blocks_from_pdf():
    test_text = "Paragraph one of text block. " + ("Some additional placeholder text to ensure length limit of 100 characters is exceeded. " * 3)
    pdf_bytes = create_mock_pdf_bytes(test_text)
    
    blocks = extract_blocks_from_pdf(pdf_bytes)
    assert len(blocks) > 0
    assert "Paragraph" in blocks[0]["text"]
    assert "x0" in blocks[0]
    assert "y0" in blocks[0]

def test_extract_github_username():
    links = [
        "https://linkedin.com/in/johndoe",
        "https://github.com/johndoe-developer",
        "https://github.com/johndoe-developer/project-repo"
    ]
    username = extract_github_username(links)
    assert username == "johndoe-developer"

    # Edge cases
    assert extract_github_username([]) is None
    assert extract_github_username(["github.com"]) is None
    # Ignore github standard paths
    assert extract_github_username(["https://github.com/pricing"]) is None

@pytest.mark.asyncio
async def test_enrich_profile_with_github_success():
    # Mock httpx response
    mock_repos = [
        {
            "name": "project1",
            "description": "My first repo",
            "fork": False,
            "stargazers_count": 5,
            "language": "Python",
            "html_url": "https://github.com/johndoe/project1"
        },
        {
            "name": "forked-project",
            "fork": True,
            "stargazers_count": 100,
            "language": "Javascript"
        }
    ]
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_repos
        mock_get.return_value = mock_response
        
        enriched = await enrich_profile_with_github("johndoe")
        assert enriched["username"] == "johndoe"
        assert enriched["total_stars"] == 5  # forks are ignored
        assert enriched["languages"] == {"Python": 1}
        assert len(enriched["top_repositories"]) == 1
        assert enriched["top_repositories"][0]["name"] == "project1"

@pytest.mark.asyncio
async def test_enrich_profile_with_github_rate_limited():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        enriched = await enrich_profile_with_github("johndoe")
        # should degrade gracefully and not crash
        assert enriched["username"] == "johndoe"
        assert enriched["total_stars"] == 0
        assert enriched["top_repositories"] == []

# Sample structured profile fixture
@pytest.fixture
def sample_profile() -> ResumeParsedData:
    return ResumeParsedData(
        name="Jane Developer",
        email="jane@example.com",
        phone="555-0199",
        links=["github.com/jane-dev", "linkedin.com/in/jane"],
        skills=["Python", "FastAPI", "TypeScript", "Next.js"],
        education=[{
            "degree": "B.S.",
            "major": "Computer Science",
            "school": "State University",
            "date": "2024"
        }],
        experience=[{
            "role": "Software Engineer Intern",
            "company": "Tech Corp",
            "start_date": "2023-06",
            "end_date": "2023-09",
            "location": "Remote",
            "bullets": [
                "Developed REST APIs using FastAPI.",
                "Optimized database queries decreasing latency by 20%."
            ]
        }],
        projects=[{
            "name": "Portfolio Website",
            "link": "jane.dev",
            "bullets": ["Built responsive portfolio using React."]
        }]
    )

def test_generate_resume_pdf(sample_profile):
    # This will check if weasyprint compiles without throwing exceptions
    try:
        pdf_bytes = generate_resume_pdf(sample_profile)
        assert len(pdf_bytes) > 0
    except (ImportError, OSError):
        # If WeasyPrint cannot load GTK+ on this system, we expect it to raise ImportError or OSError,
        # which is handled and allowed during headless CI environments.
        pass

def test_generate_resume_docx(sample_profile):
    docx_bytes = generate_resume_docx(sample_profile)
    assert len(docx_bytes) > 0
    # Ensure it's a valid zip file structure (which docx is)
    assert docx_bytes.startswith(b"PK\x03\x04")

@patch("app.parsers.llm_extractor.llm_client.generate_structured")
@patch("app.main.enrich_profile_with_github", new_callable=AsyncMock)
def test_intake_api_endpoint(mock_enrich, mock_llm, sample_profile):
    mock_llm.return_value = sample_profile
    mock_enrich.return_value = {
        "username": "jane-dev",
        "total_stars": 12,
        "languages": {"Python": 1},
        "top_repositories": []
    }
    
    pdf_bytes = create_mock_pdf_bytes("Jane Developer Resume Text. " + ("Some additional placeholder text to ensure length limit of 100 characters is exceeded. " * 3))
    
    response = client.post(
        "/intake",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert data["parsed_resume"]["name"] == "Jane Developer"
    assert data["github_enriched"]["total_stars"] == 12

def test_render_api_endpoint(sample_profile):
    payload = sample_profile.model_dump()
    
    # Test docx render
    response = client.post("/render?format=docx", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert response.content.startswith(b"PK\x03\x04")

    # Test pdf render (allow pass if WeasyPrint has GTK missing)
    response_pdf = client.post("/render?format=pdf", json=payload)
    if response_pdf.status_code == 500 and "rendering libraries missing" in response_pdf.json().get("detail", ""):
        pass
    else:
        assert response_pdf.status_code == 200
        assert response_pdf.headers["content-type"] == "application/pdf"
