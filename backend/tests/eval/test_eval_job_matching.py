import pytest
from app.services.job_service import calculate_match_score_v2
from app.schemas import ResumeParsedData

def test_eval_job_matching_accuracy():
    """Verify alignment classification accuracy on representative job-resume pairs."""
    profile = ResumeParsedData(
        name="John Doe",
        email="john@example.com",
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience=[],
        projects=[]
    )
    
    # 1. Perfect match scenario
    score, explanation = calculate_match_score_v2(
        job_title="Python FastAPI Developer",
        jd_text="Looking for a Python developer experienced with FastAPI and PostgreSQL.",
        job_location=None,
        job_remote=True,
        profile=profile,
        search_query="Python FastAPI"
    )
    assert score >= 0.7
    
    # 2. Complete mismatch scenario
    score_bad, explanation_bad = calculate_match_score_v2(
        job_title="Senior Nurse",
        jd_text="Registered nurse with nursing license and patient care skills.",
        job_location=None,
        job_remote=False,
        profile=profile,
        search_query="Nurse"
    )
    assert score_bad < 0.4
