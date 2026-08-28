from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ApplicationQuality(BaseModel):
    overall: int           # 0-100
    resume_match: int      # 0-100
    required_skills: int   # 0-100
    experience_fit: int    # 0-100
    keyword_coverage: int  # 0-100
    factual_confidence: int # 0-100
    cover_letter: int      # 0-100
    missing_requirements: List[str]
    fix_suggestions: List[str]

class QualityScorer:
    @staticmethod
    def calculate_quality(
        skills_matched: List[str],
        skills_missing: List[str],
        candidate_years_exp: float,
        required_years_exp: float,
        has_cover_letter: bool = False,
        cl_text: str = "",
        truthfulness_failures: int = 0
    ) -> ApplicationQuality:
        """
        Calculates a pre-submission application quality rating.
        Highlights missing criteria and provides action items to improve.
        """
        fix_suggestions = []
        missing_requirements = []

        # 1. Skills Calculation (40% weight)
        total_skills = len(skills_matched) + len(skills_missing)
        skill_score = 100
        if total_skills > 0:
            skill_score = int((len(skills_matched) / total_skills) * 100)
            
        if skills_missing:
            fix_suggestions.append(f"Add key missing skills to your profile if you have experience with them: {', '.join(skills_missing[:3])}")
            missing_requirements.extend(skills_missing[:3])

        # 2. Experience Fit (30% weight)
        exp_score = 100
        if required_years_exp > 0:
            if candidate_years_exp >= required_years_exp:
                exp_score = 100
            else:
                deficit = required_years_exp - candidate_years_exp
                exp_score = max(int((candidate_years_exp / required_years_exp) * 100), 0)
                fix_suggestions.append(f"Highlight projects or internship experiences to offset the {deficit:.1f}-year experience gap.")
                missing_requirements.append(f"Required {required_years_exp} years (Profile shows {candidate_years_exp})")

        # 3. Keyword Coverage (15% weight)
        keyword_score = skill_score

        # 4. Factual Confidence (15% weight)
        factual_score = max(100 - (truthfulness_failures * 25), 0)
        if truthfulness_failures > 0:
            fix_suggestions.append("Address the metrics/skills marked as fabricated in your tailored bullets to ensure credibility.")

        # 5. Cover Letter Quality
        cl_score = 0
        if has_cover_letter:
            cl_score = 80
            if cl_text:
                cl_lower = cl_text.lower()
                clichés = ["perfect fit", "addition to your team", "write to express my interest"]
                flagged_clichés = [c for c in clichés if c in cl_lower]
                if flagged_clichés:
                    cl_score -= len(flagged_clichés) * 10
                    fix_suggestions.append(f"Remove generic clichés from your cover letter: {', '.join(flagged_clichés)}")
        else:
            fix_suggestions.append("Generate a tailored cover letter to boost application relevance by up to 25%.")

        # Overall Score
        overall = int(
            (skill_score * 0.40) +
            (exp_score * 0.30) +
            (keyword_score * 0.15) +
            (factual_score * 0.15)
        )
        # Apply a small bonus/penalty based on cover letter
        if has_cover_letter:
            overall = min(overall + 5, 100)
        else:
            overall = max(overall - 5, 0)

        return ApplicationQuality(
            overall=overall,
            resume_match=skill_score,
            required_skills=skill_score,
            experience_fit=exp_score,
            keyword_coverage=keyword_score,
            factual_confidence=factual_score,
            cover_letter=cl_score,
            missing_requirements=missing_requirements,
            fix_suggestions=fix_suggestions
        )
