import pytest
from app.services.job_service import JobService

@pytest.mark.asyncio
async def test_scrape_linkedin_playwright():
    service = JobService()
    # Query with a generic term and location
    jobs = await service._scrape_linkedin_playwright("Python", "United States")
    assert isinstance(jobs, list)
    # The scraper should run and return a list of results (may be empty if rate-limited or blocked, but must not throw)
    if jobs:
        for job in jobs:
            assert "title" in job
            assert "company" in job
            assert "apply_url" in job
            assert job["source"] == "LinkedIn"

@pytest.mark.asyncio
async def test_scrape_indeed_playwright():
    service = JobService()
    jobs = await service._scrape_indeed_playwright("Python", "United States")
    assert isinstance(jobs, list)
    if jobs:
        for job in jobs:
            assert "title" in job
            assert "company" in job
            assert "apply_url" in job
            assert job["source"] == "Indeed"

@pytest.mark.asyncio
async def test_scrape_glassdoor_playwright():
    service = JobService()
    jobs = await service._scrape_glassdoor_playwright("Python", "United States")
    assert isinstance(jobs, list)
    if jobs:
        for job in jobs:
            assert "title" in job
            assert "company" in job
            assert "apply_url" in job
            assert job["source"] == "Glassdoor"
