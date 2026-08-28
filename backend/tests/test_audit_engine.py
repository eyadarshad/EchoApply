import pytest
from app.services.audit_engine import (
    analyze_cv_heuristics,
    audit_cv_comprehensive,
    audit_linkedin_comprehensive
)

SAMPLE_RESUME_TEXT = """
Eyad Qureshi
Email: eyad@example.com | Phone: +1-555-0199 | Location: San Francisco, CA
LinkedIn: https://linkedin.com/in/eyadqureshi | GitHub: https://github.com/eyadqureshi

Professional Summary
Passionate AI / ML Software Engineer with 2+ years of experience developing deep learning systems, computer vision models, and production LLM applications.

Technical Skills
Languages: Python, C++, TypeScript, SQL
Frameworks & Libraries: PyTorch, TensorFlow, FastAPI, OpenCV, Hugging Face, React
Tools: Docker, Git, AWS, Linux, ONNX Runtime

Experience
AI Engineer | TechCorp Inc. (2023 - Present)
- Engineered an automated document extraction pipeline using PyTorch and FastAPI, reducing inference latency by 42%.
- Architected a real-time object detection model with 99.4% precision, serving over 500,000 monthly requests.
- Streamlined training pipelines by automating dataset curation, saving 15 engineering hours weekly.

Projects
Neural Search Engine | GitHub: https://github.com/eyadqureshi/neural-search (2024)
- Built a vector search engine using FastAPI and Qdrant, achieving sub-20ms semantic query retrieval across 1M records.
- Deployed fullstack demo on AWS with automated CI/CD pipelines.

Education
B.S. in Computer Science | University of Technology (2019 - 2023)
- GPA: 3.8 / 4.0 | Dean's Honor List
"""

SAMPLE_LINKEDIN_TEXT = """
Eyad Qureshi
AI Engineer & Machine Learning Specialist | Python, PyTorch, LLMs & Real-time Systems
San Francisco Bay Area | 500+ connections

About
I am an AI / ML Engineer passionate about turning advanced neural network architectures into ultra-fast production systems.
I have engineered vision and NLP models serving over 500k monthly requests with 99.4% precision.
Core Stack: Python, PyTorch, FastAPI, Hugging Face, Docker, Next.js.
Always looking to connect with builders in AI systems and intelligent agents.

Experience
AI Engineer @ TechCorp Inc.
- Engineered automated document extraction pipelines.
- Deployed real-time object detection models with 99.4% precision.

Skills
Python (Top skill), PyTorch (Top skill), Machine Learning (Top skill), Deep Learning, FastAPI, Docker, Computer Vision.
"""

@pytest.mark.asyncio
async def test_cv_heuristics_analyzer():
    results = analyze_cv_heuristics(SAMPLE_RESUME_TEXT)
    assert "A1" in results
    assert "A2" in results
    assert "B1" in results
    assert "B2" in results
    assert results["A1"].awarded_points >= 2
    assert results["B1"].status == "looks_good"

@pytest.mark.asyncio
async def test_cv_comprehensive_audit():
    report = await audit_cv_comprehensive(
        raw_text=SAMPLE_RESUME_TEXT,
        target_role="AI Engineer"
    )
    assert report.audit_type == "cv"
    assert report.total_score >= 50
    assert len(report.dimensions) == 6
    assert len(report.top_3_changes) > 0
    assert report.quality_label in ["Exceptional", "Competitive & Strong", "Good Foundation", "Needs Attention"]

@pytest.mark.asyncio
async def test_linkedin_comprehensive_audit():
    report = await audit_linkedin_comprehensive(
        profile_text=SAMPLE_LINKEDIN_TEXT,
        target_role="AI Engineer"
    )
    assert report.audit_type == "linkedin"
    assert report.total_score >= 50
    assert len(report.dimensions) == 6
    assert report.suggested_wording is not None
    assert len(report.suggested_wording.headline_ideas) >= 2
