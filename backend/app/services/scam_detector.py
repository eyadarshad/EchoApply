import re
from typing import Dict, Any, List
from pydantic import BaseModel

class JobSafetyScore(BaseModel):
    score: str          # "SAFE", "LOW_RISK", "UNCERTAIN", "HIGH_RISK"
    explanation: str
    risk_factors: List[str]

class ScamDetector:
    @staticmethod
    def analyze_job_safety(
        title: str,
        company: str,
        jd_text: str,
        apply_url: str = ""
    ) -> JobSafetyScore:
        """
        Analyzes a job listing for potential recruitment scam/fraud indicators.
        Returns safety score category and detailed explanation of flags found.
        """
        risk_factors = []
        text_lower = f"{title} {company} {jd_text}".lower()
        
        # 1. Payment Required
        payment_triggers = [
            "recruitment fee", "application fee", "training fee", "deposit", 
            "pay to start", "buy equipment", "wire transfer", "send money"
        ]
        for trigger in payment_triggers:
            if trigger in text_lower:
                risk_factors.append(f"Payment requested: contains '{trigger}'")

        # 2. Cryptocurrency / Unrealistic Compensation
        if "crypto" in text_lower or "bitcoin" in text_lower or "usdt" in text_lower:
            risk_factors.append("Mentions cryptocurrency or digital assets for payment")
            
        # 3. WhatsApp or Telegram only contact
        im_triggers = [
            "whatsapp only", "message on whatsapp", "contact via telegram", 
            "telegram chat", "whatsapp chat"
        ]
        for trigger in im_triggers:
            if trigger in text_lower:
                risk_factors.append(f"Redirects communications: contains '{trigger}'")

        # 4. Vague Company Identity
        vague_companies = ["confidential", "private recruiter", "anonymous", "stealth startup"]
        for vc in vague_companies:
            if vc in company.lower():
                risk_factors.append(f"Vague employer identity: '{company}'")

        # 5. Suspicious Domains in Apply URL
        if apply_url:
            suspicious_domains = [".xyz", ".top", ".club", ".info", ".win", ".bid", ".click"]
            for dom in suspicious_domains:
                if dom in apply_url.lower():
                    risk_factors.append(f"Suspicious top-level domain in apply link: '{dom}'")
            if "@" in apply_url or "mailto" in apply_url:
                if any(x in apply_url.lower() for x in ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]):
                    risk_factors.append("Directs application to a public email address instead of corporate domain")

        # Determine Score Category
        if len(risk_factors) >= 3:
            score = "HIGH_RISK"
            explanation = "Highly suspicious job listing with multiple active fraud indicators. Extreme caution recommended."
        elif len(risk_factors) == 2:
            score = "HIGH_RISK"
            explanation = "Multiple risk indicators found. High probability of scam or high-pressure recruitment scheme."
        elif len(risk_factors) == 1:
            score = "UNCERTAIN"
            explanation = "Contains a potential risk factor. Proceed with standard caution."
        else:
            score = "SAFE"
            explanation = "No standard recruitment fraud indicators detected."

        return JobSafetyScore(
            score=score,
            explanation=explanation,
            risk_factors=risk_factors
        )
