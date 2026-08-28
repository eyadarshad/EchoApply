import pytest
from app.services.resume_generator import generate_resume_pdf

def test_eval_ats_compatibility_rendering():
    """Verify WeasyPrint engine compiles and produces valid PDF documents for ATS scanning."""
    try:
        from app.schemas import ResumeParsedData
        profile = ResumeParsedData(
            name="John Doe",
            email="john@example.com",
            skills=["Python", "FastAPI"],
            experience=[],
            projects=[]
        )
        pdf_bytes = generate_resume_pdf(profile, "classic")
        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF")
    except ImportError:
        pytest.skip("WeasyPrint library not installed on local environment.")
