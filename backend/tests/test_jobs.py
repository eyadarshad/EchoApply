import pytest
import datetime
import uuid
from typing import List, Dict, Any
from app.services.job_service import JobService, calculate_job_hash, calculate_match_score
from app.schemas import JobSearchRequest, ResumeParsedData, ExperienceEntry

@pytest.fixture
def mock_profile() -> ResumeParsedData:
    return ResumeParsedData(
        name="Eyad Ahmed",
        email="eyad@example.com",
        phone="+92-300-1234567",
        links=["github.com/eyad"],
        skills=["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
        education=[],
        experience=[
            ExperienceEntry(
                role="Python Backend Developer",
                company="TechCorp",
                start_date="2023-01",
                end_date="2023-12",
                bullets=["Developed APIs in FastAPI", "Optimized SQL queries in PostgreSQL"]
            )
        ],
        projects=[]
    )

def test_calculate_job_hash():
    """Verify job hashing is deterministic and normalized."""
    hash1 = calculate_job_hash("Software Engineer  ", "TechCorp", "Karachi")
    hash2 = calculate_job_hash("software engineer", "techcorp", "karachi ")
    hash3 = calculate_job_hash("Different Role", "TechCorp", "Karachi")
    
    assert hash1 == hash2
    assert hash1 != hash3

def test_calculate_match_score_full_match(mock_profile):
    """Assert match score matches all criteria: title, skills, remote."""
    score, explanation = calculate_match_score(
        job_title="Python Backend Developer",
        jd_text="Looking for a Backend Developer with skills in FastAPI, React, and PostgreSQL.",
        job_location="Remote",
        job_remote=True,
        profile=mock_profile,
        search_query="Python Backend Developer"
    )
    # Title match query (30) + Align past roles (10) + Skill matches (FastAPI, React, PostgreSQL => 3/5 => 24) + Remote (20) + Recency (10) = 94 => 0.94
    assert score >= 0.9
    assert "fastapi" in explanation.lower()
    assert "remote" in explanation.lower()

def test_calculate_match_score_no_profile():
    """Assert fallback match score calculation works without a candidate profile."""
    score, explanation = calculate_match_score(
        job_title="Python Developer",
        jd_text="Looking for a Python Developer experienced in FastAPI.",
        job_location="Karachi",
        job_remote=False,
        profile=None,
        search_query="Python Developer"
    )
    assert score > 0.0
    assert "fastapi" in explanation.lower() or "python" in explanation.lower() or "developer" in explanation.lower()

@pytest.mark.asyncio
async def test_job_service_aggregation_and_deduplication():
    """Verify search_and_rank_jobs aggregates and dedupes mock results."""
    service = JobService()
    # Force DB offline for unit testing
    service.db_reachable = False
    
    request = JobSearchRequest(
        query="Python",
        location="Karachi",
        remote_only=False,
        limit=5
    )
    
    response = await service.search_and_rank_jobs(request)
    assert len(response.jobs) > 0
    
    # Assert deduplication
    seen_hashes = set()
    for job in response.jobs:
        assert job.job_hash not in seen_hashes
        seen_hashes.add(job.job_hash)

@pytest.mark.asyncio
async def test_job_service_remote_filter():
    """Verify remote-only filtering works on aggregated results."""
    service = JobService()
    service.db_reachable = False
    
    request = JobSearchRequest(
        query="Developer",
        remote_only=True,
        limit=5
    )
    
    response = await service.search_and_rank_jobs(request)
    for job in response.jobs:
        assert job.remote is True

@pytest.mark.asyncio
async def test_playwright_scrapers_graceful():
    """Verify that calling the playwright scrapers behaves correctly and handles errors or execution gracefully."""
    service = JobService()
    # Test that we can call them without crashing
    results = await service._scrape_linkedin_playwright(query="Python Developer", location="Karachi")
    assert isinstance(results, list)
    
    results = await service._scrape_indeed_playwright(query="React Developer", location="Lahore")
    assert isinstance(results, list)
    
    results = await service._scrape_glassdoor_playwright(query="Product Manager", location="Islamabad")
    assert isinstance(results, list)

