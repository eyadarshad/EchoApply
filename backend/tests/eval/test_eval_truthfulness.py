import pytest
from app.services.quality_scorer import QualityScorer

def test_eval_truthfulness_hallucination_rate():
    """Verify quality score penalty when gaps or inaccuracies exist."""
    res = QualityScorer.calculate_quality(
        skills_matched=["Python"],
        skills_missing=["Rust", "Solidity"],
        candidate_years_exp=1.0,
        required_years_exp=3.0,
        has_cover_letter=False
    )
    assert res.overall < 70
