import os
import pytest
import psycopg
from app.config import settings
from app.schemas import ResumeParsedData, JobSearchRequest
from app.services.embedding_service import serialize_profile, serialize_job, cosine_similarity
from app.services.llm_client import llm_client
from app.services.job_service import calculate_match_score_v2, JobService

# Check database availability
def get_db_connection():
    if not settings.DATABASE_URL:
        return None
    try:
        conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
        return conn
    except Exception:
        return None

db_conn_available = get_db_connection() is not None

def test_text_serialization():
    """Verify profile and job serialization format."""
    profile = ResumeParsedData(
        name="Test Candidate",
        email="candidate@test.com",
        skills=["Python", "FastAPI"],
        experience=[],
        projects=[]
    )
    serialized = serialize_profile(profile)
    assert "Candidate Name: Test Candidate" in serialized
    assert "Skills: Python, FastAPI" in serialized
    
    serialized_job = serialize_job("Backend Engineer", "TechCorp", "FastAPI description")
    assert "Job Title: Backend Engineer" in serialized_job
    assert "Company: TechCorp" in serialized_job
    assert "FastAPI description" in serialized_job

def test_cosine_similarity_math():
    """Verify cosine similarity mathematical boundaries."""
    # Identical vectors -> 1.0
    v1 = [1.0, 2.0, 3.0]
    assert pytest.approx(cosine_similarity(v1, v1)) == 1.0
    
    # Orthogonal vectors -> 0.0
    v2 = [1.0, 0.0]
    v3 = [0.0, 1.0]
    assert pytest.approx(cosine_similarity(v2, v3)) == 0.0
    
    # Empty or mismatched -> 0.0
    assert cosine_similarity([], v1) == 0.0
    assert cosine_similarity(v1, [1.0, 2.0]) == 0.0

def test_embedding_generation_fallback():
    """Verify that generate_embedding returns a 768-dimensional float list."""
    emb = llm_client.generate_embedding("Backend Developer")
    assert isinstance(emb, list)
    assert len(emb) == 768
    assert all(isinstance(val, float) for val in emb)

def test_blended_score_scaling():
    """Verify blended match score interpolation and boundaries."""
    profile = ResumeParsedData(
        name="Eyad Ahmed",
        email="eyad@example.com",
        skills=["Python", "FastAPI"],
        experience=[],
        projects=[]
    )
    
    # 1. No embeddings -> fallback to pure rule score
    score, explanation = calculate_match_score_v2(
        job_title="FastAPI Engineer",
        jd_text="FastAPI development role in Karachi.",
        job_location="Karachi",
        job_remote=False,
        profile=profile,
        search_query="FastAPI",
        profile_embedding=None,
        job_embedding=None
    )
    assert 0.0 <= score <= 1.0
    assert "Semantic Match" not in explanation
    
    # 2. Perfect similarity (1.0) and high rule score
    # Cosine similarity is 1.0, which scales to semantic_score = 1.0.
    # Blended score = 0.5 * 1.0 + 0.5 * rule_score
    profile_emb = [0.1] * 768
    job_emb = [0.1] * 768
    score, explanation = calculate_match_score_v2(
        job_title="FastAPI Engineer",
        jd_text="FastAPI development role in Karachi.",
        job_location="Karachi",
        job_remote=False,
        profile=profile,
        search_query="FastAPI",
        profile_embedding=profile_emb,
        job_embedding=job_emb,
        embedding_fallback=False
    )
    assert 0.0 <= score <= 1.0
    assert "Semantic Match: 100%" in explanation
    assert "Blend: 0.5*100%" in explanation

    # 3. Degraded fallback active
    score, explanation = calculate_match_score_v2(
        job_title="FastAPI Engineer",
        jd_text="FastAPI development role in Karachi.",
        job_location="Karachi",
        job_remote=False,
        profile=profile,
        search_query="FastAPI",
        profile_embedding=profile_emb,
        job_embedding=job_emb,
        embedding_fallback=True
    )
    assert "Semantic Match (Degraded): 100%" in explanation
    assert "WARNING: Gemini API embedding generation failed" in explanation

@pytest.mark.skipif(not db_conn_available, reason="PostgreSQL database is offline or unreachable")
def test_pgvector_similarity_query():
    """Verify pgvector similarity queries against a running PostgreSQL database."""
    conn = psycopg.connect(settings.DATABASE_URL)
    cursor = conn.cursor()
    try:
        # Create vectors
        v1 = [0.1] * 768
        v2 = [0.15] * 768
        
        # Test inserting and reading job with vector
        cursor.execute("DELETE FROM jobs WHERE job_hash = 'test_matching_hash';")
        cursor.execute(
            """
            INSERT INTO jobs (source, title, company, jd_text, job_hash, jd_embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            ("JSearch", "ML Engineer", "VectorCorp", "Need Machine Learning experts", "test_matching_hash", v1)
        )
        job_id = cursor.fetchone()[0]
        conn.commit()
        
        # Verify query with <=> operator
        cursor.execute(
            """
            SELECT id, (1 - (jd_embedding <=> %s::vector)) as similarity
            FROM jobs
            WHERE id = %s;
            """,
            (v2, job_id)
        )
        row = cursor.fetchone()
        assert row is not None
        similarity = row[1]
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        
        # Clean up
        cursor.execute("DELETE FROM jobs WHERE id = %s;", (job_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
