import os
import re
import logging
import hashlib
import json
import uuid
import datetime
import asyncio
import unicodedata
from typing import List, Optional, Dict, Any, Tuple
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.schemas import JobSearchRequest, JobSearchResponse, JobCard, ResumeParsedData, MatchBreakdown
from app.utils import clean_uuid

logger = logging.getLogger(__name__)

CLOSURE_PATTERNS = [
    r"no longer accepting applications",
    r"closed to new applications",
    r"position filled",
    r"this listing has expired",
    r"applications closed",
    r"job is no longer available",
    r"hiring has concluded",
]

def is_job_description_closed(jd_text: str) -> bool:
    if not jd_text:
        return False
    jd_lower = jd_text.lower()
    for pattern in CLOSURE_PATTERNS:
        if re.search(pattern, jd_lower):
            return True
    return False

def _is_within_date_range(posted_at_str: Optional[str], date_posted: str) -> bool:
    if not posted_at_str or date_posted == "any":
        return True
    try:
        # Clean timezone indicators
        clean_str = posted_at_str.replace("Z", "+00:00")
        if "t" in clean_str.lower():
            dt = datetime.datetime.fromisoformat(clean_str)
        else:
            dt = datetime.datetime.strptime(clean_str[:10], "%Y-%m-%d")
            dt = dt.replace(tzinfo=datetime.timezone.utc)
            
        now = datetime.datetime.now(datetime.timezone.utc)
        age = now - dt
        
        if date_posted == "today":
            return age.days <= 1
        elif date_posted == "3days":
            return age.days <= 3
        elif date_posted == "week":
            return age.days <= 7
        elif date_posted == "month":
            return age.days <= 30
    except Exception:
        pass
    return True

# Concurrency Semaphores to respect API limits
SEMAPHORES = {
    "JSearch": asyncio.Semaphore(2),
    "Jooble": asyncio.Semaphore(2),
    "Remotive": asyncio.Semaphore(1),
    "Arbeitnow": asyncio.Semaphore(2)
}

from cachetools import TTLCache
IN_MEMORY_JOB_CACHE = TTLCache(maxsize=500, ttl=3600)

def normalize_company_name(company: str) -> str:
    if not company:
        return ""
    comp = company.lower()
    comp = re.sub(r'\b(?:llc|inc|corp|corporation|co|company|ltd|limited)\b', '', comp)
    comp = re.sub(r'[^\w\s]', '', comp)
    return " ".join(comp.split())

def normalize_job_title(title: str) -> str:
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r'\b(?:sr\.?|senior)\b', 'senior', t)
    t = re.sub(r'\b(?:jr\.?|junior)\b', 'junior', t)
    t = re.sub(r'[^\w\s\+#]', '', t)
    return " ".join(t.split())

def normalize_location(location: Optional[str]) -> str:
    if not location:
        return ""
    loc = location.lower()
    loc = re.sub(r'[^\w\s]', '', loc)
    return " ".join(loc.split())

def compute_canonical_hash(title: str, company: str, location: Optional[str], jd_text: Optional[str] = None) -> str:
    """Multi-signal deduplication hash."""
    normalized_company = normalize_company_name(company)
    normalized_title = normalize_job_title(title)
    normalized_location = normalize_location(location)
    
    primary_hash = hashlib.sha256(
        f"{normalized_title}|{normalized_company}|{normalized_location}".encode()
    ).hexdigest()
    
    if jd_text:
        jd_fingerprint = hashlib.sha256(jd_text[:500].lower().encode()).hexdigest()[:16]
        return f"{primary_hash}_{jd_fingerprint}"
    return primary_hash

def calculate_job_hash(title: str, company: str, location: Optional[str], jd_text: Optional[str] = None) -> str:
    """Generate unique deterministic hash for deduplication based on job title, company, and location."""
    return compute_canonical_hash(title, company, location, jd_text)

def get_years_experience(profile: Optional[ResumeParsedData]) -> float:
    if not profile or not profile.experience:
        return 0.0
    total_months = 0
    for exp in profile.experience:
        start = getattr(exp, "start_date", None) or (exp.get("start_date") if isinstance(exp, dict) else None)
        end = getattr(exp, "end_date", None) or (exp.get("end_date") if isinstance(exp, dict) else None)
        if not start:
            continue
        try:
            s_parts = start.split("-")
            s_year = int(s_parts[0])
            s_month = int(s_parts[1]) if len(s_parts) > 1 else 1
            
            if not end or end.lower() in ["present", "current", "now"]:
                import datetime
                now = datetime.datetime.now()
                e_year = now.year
                e_month = now.month
            else:
                e_parts = end.split("-")
                e_year = int(e_parts[0])
                e_month = int(e_parts[1]) if len(e_parts) > 1 else 12
                
            months = (e_year - s_year) * 12 + (e_month - s_month)
            if months > 0:
                total_months += months
        except Exception:
            total_months += 12
    return round(total_months / 12.0, 1)

def extract_required_years(jd_text: str) -> float:
    if not jd_text:
        return 0.0
    patterns = [
        r'(\d+)\s*\+?\s*years?\s+(?:of\s+)?experience',
        r'experience\s+of\s+(\d+)\s*\+?\s*years?',
        r'(\d+)\s*-\s*(\d+)\s*years?',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, jd_text, re.IGNORECASE)
        if matches:
            val = matches[0]
            if isinstance(val, tuple):
                return float(val[0])
            return float(val)
    return 0.0

def calculate_match_score(
    job_title: str,
    jd_text: str,
    job_location: Optional[str],
    job_remote: bool,
    profile: Optional[ResumeParsedData],
    search_query: str
) -> Tuple[float, str]:
    """
    V1 Rule-based matching score: Keyword overlap (40%) + Title match (30%) + Location (20%) + Recency (10%)
    """
    score = 0.0
    explanations = []

    # 1. Title Match (up to 30 points)
    query_words = set(w.lower() for w in search_query.split() if len(w) > 2)
    title_lower = job_title.lower()

    matching_query_words = [w for w in query_words if w in title_lower]
    if matching_query_words:
        score += min(len(matching_query_words) * 15.0, 30.0)
        explanations.append(f"Title matches search query terms: {', '.join(matching_query_words)}.")
        
    if profile:
        profile_roles = [exp.role.lower() for exp in profile.experience if hasattr(exp, 'role') or isinstance(exp, dict)]
        matching_roles = [role for role in profile_roles if any(w in title_lower for w in role.split())]
        if matching_roles:
            score += 10.0
            explanations.append("Title aligns with your career trajectory.")

    # 2. Keyword Overlap (up to 40 points)
    if profile and profile.skills:
        skills_lower = [s.lower() for s in profile.skills]
        jd_lower = jd_text.lower()
        matched_skills = [skill for skill in skills_lower if skill in jd_lower]
        if skills_lower:
            overlap_ratio = len(matched_skills) / len(skills_lower)
            score += overlap_ratio * 40.0
            explanations.append(f"Matched {len(matched_skills)} of your skills: {', '.join(matched_skills[:5])}.")
    else:
        # Fallback if profile is missing
        jd_lower = jd_text.lower()
        matched_query = [w for w in query_words if w in jd_lower]
        if query_words:
            overlap_ratio = len(matched_query) / len(query_words)
            score += overlap_ratio * 40.0
            explanations.append(f"JD contains search terms: {', '.join(matched_query)}.")

    # 3. Location/Remote Match (up to 20 points)
    if job_remote:
        score += 20.0
        explanations.append("Role is fully remote (highly flexible).")
    elif job_location and "remote" in job_location.lower():
        score += 20.0
        explanations.append("Location notes remote/work-from-home options.")
    else:
        score += 10.0
        explanations.append("On-site / Hybrid role.")

    # 4. Recency (up to 10 points)
    score += 10.0

    final_score = round(min(score / 100.0, 1.0), 2)
    explanation_str = " ".join(explanations)
    return final_score, explanation_str

def calculate_match_score_v3(
    job_title: str,
    jd_text: str,
    job_location: Optional[str],
    job_remote: bool,
    profile: Optional[ResumeParsedData],
    search_query: str,
    profile_embedding: Optional[List[float]],
    job_embedding: Optional[List[float]],
    embedding_fallback: bool = False
) -> Tuple[float, str, MatchBreakdown, List[str], List[str], List[str]]:
    """
    V3 Multi-factor explainable matching engine.
    """
    from app.schemas import MatchBreakdown
    v1_score, v1_explanation = calculate_match_score(
        job_title, jd_text, job_location, job_remote, profile, search_query
    )
    
    skill_matches = []
    skill_gaps = []
    if profile and profile.skills:
        skills_lower = [s.lower() for s in profile.skills]
        jd_lower = jd_text.lower()
        for skill in profile.skills:
            if skill.lower() in jd_lower:
                skill_matches.append(skill)
                
        tech_words = {"python", "fastapi", "django", "react", "typescript", "kubernetes", "docker", "aws", "postgresql", "node.js", "java", "c++", "go", "rust", "terraform", "sql", "git", "ci/cd", "redis", "mongodb"}
        for word in tech_words:
            if word in jd_lower and word not in skills_lower:
                skill_gaps.append(word.capitalize())
                
    cand_exp = get_years_experience(profile)
    req_exp = extract_required_years(jd_text)
    
    if req_exp == 0:
        experience_fit = 1.0
    elif cand_exp >= req_exp:
        experience_fit = 1.0
    else:
        experience_fit = round(cand_exp / req_exp, 2)
        
    hard_blockers = []
    if req_exp > 0 and cand_exp < req_exp - 1.5:
        hard_blockers.append(f"Requires {int(req_exp)}+ years of experience (your profile shows {cand_exp} years)")
        
    if "us authorization required" in jd_text.lower() or "must be authorized to work in the us" in jd_text.lower() or "us citizen" in jd_text.lower():
        hard_blockers.append("Requires US work authorization")

    location_fit = 1.0
    if job_remote:
        location_fit = 1.0
    elif job_location and profile and getattr(profile, "location", None):
        cand_loc = profile.location.lower()
        if cand_loc in job_location.lower() or job_location.lower() in cand_loc:
            location_fit = 1.0
        else:
            location_fit = 0.5
            
    seniority_fit = 1.0
    title_lower = job_title.lower()
    if "senior" in title_lower or "lead" in title_lower or "principal" in title_lower:
        if cand_exp < 3.0:
            seniority_fit = 0.5
            hard_blockers.append(f"Seniority mismatch: role is senior level but your profile shows junior/mid-level experience ({cand_exp} years)")
    elif "intern" in title_lower or "junior" in title_lower or "entry" in title_lower:
        if cand_exp >= 4.0:
            seniority_fit = 0.7
            
    overall_score = v1_score
    if profile_embedding and job_embedding:
        from app.services.embedding_service import cosine_similarity
        similarity = cosine_similarity(profile_embedding, job_embedding)
        raw_val = (similarity - 0.3) / 0.45
        semantic_score = min(max(raw_val, 0.0), 1.0)
        overall_score = round(0.5 * semantic_score + 0.5 * v1_score, 2)
        
    if hard_blockers:
        overall_score = max(overall_score - 0.3, 0.0)
        
    if hard_blockers:
        recommendation = "Not eligible"
    elif overall_score >= 0.8:
        recommendation = "Strong match"
    elif overall_score >= 0.5:
        recommendation = "Partial match"
    else:
        recommendation = "Weak match"
        
    breakdown = MatchBreakdown(
        overall_score=overall_score,
        skill_match={
            "strong": skill_matches,
            "partial": [],
            "missing": skill_gaps
        },
        experience_fit=experience_fit,
        seniority_fit=seniority_fit,
        location_fit=location_fit,
        hard_blockers=hard_blockers,
        recommendation=recommendation
    )
    
    explanation_parts = [f"Overall Match: {int(overall_score * 100)}%."]
    if hard_blockers:
        explanation_parts.append(f"Potential Blocker: {', '.join(hard_blockers)}.")
    else:
        explanation_parts.append(recommendation + ".")
    explanation_parts.append(v1_explanation)
    
    return overall_score, " ".join(explanation_parts), breakdown, skill_matches, skill_gaps, hard_blockers

def calculate_match_score_v2(
    job_title: str,
    jd_text: str,
    job_location: Optional[str],
    job_remote: bool,
    profile: Optional[ResumeParsedData],
    search_query: str,
    profile_embedding: Optional[List[float]] = None,
    job_embedding: Optional[List[float]] = None,
    embedding_fallback: bool = False
) -> Tuple[float, str]:
    """
    V2 Hybrid matching score: 50% semantic similarity + 50% rule-based score (v1)
    """
    v1_score, v1_explanation = calculate_match_score(
        job_title, jd_text, job_location, job_remote, profile, search_query
    )
    
    if profile_embedding and job_embedding:
        from app.services.embedding_service import cosine_similarity
        similarity = cosine_similarity(profile_embedding, job_embedding)
        
        # Scale: similarity <= 0.3 -> 0.0, >= 0.75 -> 1.0. Linear interpolation in between.
        raw_val = (similarity - 0.3) / 0.45
        semantic_score = min(max(raw_val, 0.0), 1.0)
        
        final_score = round(0.5 * semantic_score + 0.5 * v1_score, 2)
        
        semantic_pct = int(semantic_score * 100)
        keyword_pct = int(v1_score * 100)
        final_pct = int(final_score * 100)
        
        if embedding_fallback:
            match_header = f"[Semantic Match (Degraded): {semantic_pct}% | Keyword Match: {keyword_pct}% | Blend: 0.5*{semantic_pct}% + 0.5*{keyword_pct}% = {final_pct}%]"
            explanation = f"{match_header} WARNING: Gemini API embedding generation failed. Utilizing approximate match - semantic scoring is temporarily degraded. {v1_explanation}"
        else:
            match_header = f"[Semantic Match: {semantic_pct}% | Keyword Match: {keyword_pct}% | Blend: 0.5*{semantic_pct}% + 0.5*{keyword_pct}% = {final_pct}%]"
            explanation = f"{match_header} {v1_explanation}"
            
        return final_score, explanation
    else:
        return v1_score, v1_explanation

# Rich local mock dataset for testing and fallback mode
MOCK_JOBS = [
    {
        "title": "Python Backend Engineer",
        "company": "TechSolutions Karachi",
        "location": "Karachi, Pakistan",
        "remote": False,
        "source": "LinkedIn",
        "apply_url": "https://example.com/jobs/python-karachi",
        "jd_text": "We are seeking a Python Backend Developer with strong knowledge of FastAPI, PostgreSQL, and AWS. Responsible for building microservices, optimizing SQL queries, and configuring Docker containers."
    },
    {
        "title": "Senior React Developer",
        "company": "AppCraft Lahore",
        "location": "Lahore, Pakistan",
        "remote": True,
        "source": "Indeed",
        "apply_url": "https://example.com/jobs/react-lahore",
        "jd_text": "Looking for a Frontend Developer experienced in React, Next.js, and TypeScript. Skills in CSS Tailwind, responsive layouts, and state management are required."
    },
    {
        "title": "Fullstack Software Developer",
        "company": "Remote LLC",
        "location": "Remote, Pakistan",
        "remote": True,
        "source": "Remotive",
        "apply_url": "https://example.com/jobs/fullstack-remote",
        "jd_text": "Join our international team working on React, FastAPI, Node.js, and CI/CD pipelines. Build reliable software interfaces and backend endpoints in a fast-paced environment."
    },
    {
        "title": "Java Spring Boot Intern",
        "company": "Enterprise Software Islamabad",
        "location": "Islamabad, Pakistan",
        "remote": False,
        "source": "Glassdoor",
        "apply_url": "https://example.com/jobs/java-islamabad",
        "jd_text": "Seeking a Software Engineering Intern/Fresher with knowledge of Java, Spring Boot, SQL, and Git. You will contribute to database migrations, API testing, and core application components."
    },
    {
        "title": "DevOps & Cloud Engineer",
        "company": "CloudScale Solutions",
        "location": "Karachi, Pakistan",
        "remote": True,
        "source": "Arbeitnow",
        "apply_url": "https://example.com/jobs/devops-pk",
        "jd_text": "Manage cloud resources and deployments on AWS. Experience with Docker, Kubernetes, GitHub Actions CI/CD, and Linux administration is mandatory."
    }
]

class JobService:
    def __init__(self):
        self.db_reachable = False
        self._test_db_reachability()

    def _test_db_reachability(self):
        """Quick operational check on startup to determine database availability."""
        if not settings.DATABASE_URL:
            self.db_reachable = False
            return
        import psycopg
        conn = None
        try:
            conn = psycopg.connect(settings.DATABASE_URL, connect_timeout=2)
            self.db_reachable = True
        except Exception:
            self.db_reachable = False
        finally:
            if conn:
                conn.close()

    def _get_db_connection(self):
        import psycopg
        return psycopg.connect(settings.DATABASE_URL, connect_timeout=2)

    def _get_cached_results(self, query_hash: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch cached jobs from Database or In-Memory cache."""
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # 1. DB Cache Check
        if self.db_reachable:
            conn = None
            try:
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT results_json, expires_at FROM job_cache WHERE query_hash = %s;",
                        (query_hash,)
                    )
                    row = cursor.fetchone()
                    if row:
                        results_json, expires_at = row
                        # Check expiration
                        if expires_at > now:
                            logger.info("Serving job search results from DB cache.")
                            return results_json
            except Exception as e:
                logger.error(f"Error accessing DB job_cache: {e}")
            finally:
                if conn:
                    conn.close()
                    
        # 2. In-Memory Cache Check
        if query_hash in IN_MEMORY_JOB_CACHE:
            jobs, expires_at = IN_MEMORY_JOB_CACHE[query_hash]
            if expires_at > now:
                logger.info("Serving job search results from in-memory cache.")
                return jobs
                
        return None

    def _set_cached_results(self, query_hash: str, jobs: List[Dict[str, Any]], ttl_hours: int = 2):
        """Store job search results in Database or In-Memory cache."""
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(hours=ttl_hours)
        
        # 1. DB Cache Store
        if self.db_reachable:
            conn = None
            try:
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO job_cache (query_hash, results_json, expires_at)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (query_hash) DO UPDATE 
                        SET results_json = EXCLUDED.results_json, expires_at = EXCLUDED.expires_at;
                        """,
                        (query_hash, json.dumps(jobs), expires_at)
                    )
                    conn.commit()
                    logger.info("Saved job search results to DB cache.")
                    return
            except Exception as e:
                logger.error(f"Error saving to DB job_cache: {e}")
            finally:
                if conn:
                    conn.close()
                    
        # 2. In-Memory Cache Store (fallback)
        IN_MEMORY_JOB_CACHE[query_hash] = (jobs, expires_at)
        logger.info("Saved job search results to in-memory cache.")

    def _enrich_cache(self, query_hash: str, new_jobs: List[Dict[str, Any]]):
        """Merges new background-fetched jobs into the existing cache for query_hash."""
        existing = self._get_cached_results(query_hash) or []
        seen_hashes = {calculate_job_hash(j["title"], j["company"], j.get("location")) for j in existing}
        merged = list(existing)
        for nj in new_jobs:
            job_hash = calculate_job_hash(nj["title"], nj["company"], nj.get("location"))
            if job_hash not in seen_hashes:
                nj["job_hash"] = job_hash
                merged.append(nj)
                seen_hashes.add(job_hash)
        self._set_cached_results(query_hash, merged)
        logger.info(f"Enriched job cache for {query_hash} with {len(merged) - len(existing)} new jobs.")

    def _get_applied_hashes(self, user_id: str) -> set[str]:
        """Fetch set of job hashes that the user has already applied to."""
        applied_hashes = set()
        if self.db_reachable and user_id:
            conn = None
            try:
                clean_uid_str = clean_uuid(user_id)
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT job_hash FROM applications WHERE user_id = %s;",
                        (clean_uid_str,)
                    )
                    rows = cursor.fetchall()
                    applied_hashes = set(row[0] for row in rows)
            except Exception as e:
                logger.error(f"Error querying applications: {e}")
            finally:
                if conn:
                    conn.close()
        return applied_hashes

    def _store_jobs_in_db(self, jobs: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Store fetched jobs in the database and return a mapping of job_hash -> job_id (UUID).
        Generates in-memory random UUIDs for database-less fallback.
        """
        hash_to_uuid = {}
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if self.db_reachable:
            conn = None
            try:
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    # 1. Identify which job hashes already exist in the DB
                    job_hashes = [job["job_hash"] for job in jobs]
                    cursor.execute(
                        "SELECT job_hash, jd_embedding IS NOT NULL FROM jobs WHERE job_hash = ANY(%s);",
                        (job_hashes,)
                    )
                    existing = {row[0]: row[1] for row in cursor.fetchall()}
                    
                    # 2. Skip generating job embeddings during ingestion to speed up search (they are generated on-the-fly when tailoring if missing)
                    existing_embeddings = {}
                    # Try to fetch existing embeddings from DB if any
                    cursor.execute(
                        "SELECT job_hash, jd_embedding FROM jobs WHERE job_hash = ANY(%s);",
                        (job_hashes,)
                    )
                    for row in cursor.fetchall():
                        if row[1] is not None:
                            existing_embeddings[row[0]] = row[1]
                            
                    for job in jobs:
                        job_hash = job["job_hash"]
                        if job_hash in existing_embeddings:
                            job["jd_embedding"] = existing_embeddings[job_hash]
                    
                    # 4. Insert or update the jobs in the database
                    for job in jobs:
                        job_hash = job["job_hash"]
                        embedding = job.get("jd_embedding")
                        
                        if embedding:
                            cursor.execute(
                                """
                                INSERT INTO jobs (source, title, company, location, remote, jd_text, apply_url, fetched_at, job_hash, jd_embedding, first_seen_at, last_seen_at, last_verified_at, freshness_status)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW(), 'active')
                                ON CONFLICT (job_hash) DO UPDATE
                                SET title = EXCLUDED.title, apply_url = EXCLUDED.apply_url, jd_embedding = EXCLUDED.jd_embedding, last_seen_at = NOW(), last_verified_at = NOW(), freshness_status = 'active'
                                RETURNING id;
                                """,
                                (
                                    job["source"],
                                    job["title"],
                                    job["company"],
                                    job.get("location"),
                                    job.get("remote", False),
                                    job["jd_text"],
                                    job.get("apply_url"),
                                    now,
                                    job_hash,
                                    embedding
                                )
                            )
                        else:
                            cursor.execute(
                                """
                                INSERT INTO jobs (source, title, company, location, remote, jd_text, apply_url, fetched_at, job_hash, first_seen_at, last_seen_at, last_verified_at, freshness_status)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW(), 'active')
                                ON CONFLICT (job_hash) DO UPDATE
                                SET title = EXCLUDED.title, apply_url = EXCLUDED.apply_url, last_seen_at = NOW(), last_verified_at = NOW(), freshness_status = 'active'
                                RETURNING id;
                                """,
                                (
                                    job["source"],
                                    job["title"],
                                    job["company"],
                                    job.get("location"),
                                    job.get("remote", False),
                                    job["jd_text"],
                                    job.get("apply_url"),
                                    now,
                                    job_hash
                                )
                            )
                        inserted_id = cursor.fetchone()[0]
                        hash_to_uuid[job_hash] = str(inserted_id)
                    conn.commit()
                return hash_to_uuid
            except Exception as e:
                logger.error(f"Error storing jobs in DB: {e}")
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    conn.close()
                    
        # Fallback mapping
        for job in jobs:
            hash_to_uuid[job["job_hash"]] = str(uuid.uuid4())
        return hash_to_uuid

    def mark_stale_jobs(self):
        """Mark jobs as stale if last_verified_at is older than 14 days."""
        if not self.db_reachable:
            return
        conn = None
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE jobs
                    SET freshness_status = 'stale'
                    WHERE last_verified_at < NOW() - INTERVAL '14 days'
                      AND freshness_status = 'active';
                    """
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error marking stale jobs: {e}")
        finally:
            if conn:
                conn.close()

    def _fetch_profile(self, user_id: str) -> Optional[ResumeParsedData]:
        """Fetch candidate profile from DB if reachable."""
        if self.db_reachable and user_id:
            conn = None
            try:
                clean_uid_str = clean_uuid(user_id)
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT parsed_resume_json FROM profiles WHERE user_id = %s;",
                        (clean_uid_str,)
                    )
                    row = cursor.fetchone()
                    if row:
                        return ResumeParsedData.model_validate(row[0])
            except Exception as e:
                logger.error(f"Error fetching profile: {e}")
            finally:
                if conn:
                    conn.close()
        return None

    def _fetch_profile_and_embedding(self, user_id: str) -> Tuple[Optional[ResumeParsedData], Optional[List[float]]]:
        """Fetch candidate profile and embedding from DB if reachable, otherwise return None."""
        if self.db_reachable and user_id:
            conn = None
            try:
                clean_uid_str = clean_uuid(user_id)
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT parsed_resume_json, profile_embedding FROM profiles WHERE user_id = %s;",
                        (clean_uid_str,)
                    )
                    row = cursor.fetchone()
                    if row:
                        profile = ResumeParsedData.model_validate(row[0]) if row[0] else None
                        embedding = row[1]
                        return profile, embedding
            except Exception as e:
                logger.error(f"Error fetching profile and embedding: {e}")
            finally:
                if conn:
                    conn.close()

        # Database is down/unreachable or user not found. Return None instead of raising.
        logger.warning(f"Candidate profile not found in DB for user_id: {user_id}. Job search will use keyword-only matching.")
        return None, None

    def _update_profile_embedding(self, user_id: str, embedding: List[float]):
        """Saves generated profile embedding to DB."""
        if self.db_reachable and user_id:
            conn = None
            try:
                clean_uid_str = clean_uuid(user_id)
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE profiles SET profile_embedding = %s WHERE user_id = %s;",
                        (embedding, clean_uid_str)
                    )
                    conn.commit()
            except Exception as e:
                logger.error(f"Error saving profile embedding: {e}")
            finally:
                if conn:
                    conn.close()

    # Tenacity retrier for handling API rate limits and flakiness
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=True
    )
    async def _make_api_request(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
        """Helper to make HTTP calls with retry logic."""
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    @staticmethod
    def _normalize_source(raw_source: str) -> str:
        """Map known job publisher names to clean display-friendly labels."""
        source_map = {
            "linkedin": "LinkedIn",
            "indeed": "Indeed",
            "glassdoor": "Glassdoor",
            "ziprecruiter": "ZipRecruiter",
            "monster": "Monster",
            "dice": "Dice",
            "simplyhired": "SimplyHired",
            "jsearch": "Jobs",
            "arbeitnow": "Arbeitnow",
            "remotive": "Remotive",
            "jooble": "Jooble",
            "flexboard": "FlexBoard",
        }
        if not raw_source:
            return "Jobs"
        key = raw_source.lower().strip()
        return source_map.get(key, raw_source)

    async def _fetch_jsearch(self, query: str, location: Optional[str], date_posted: str = "week", exclude_closed: bool = True) -> List[Dict[str, Any]]:
        """Fetch listings from JSearch Aggregator (RapidAPI)."""
        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("jsearch_api", failure_threshold=3, recovery_timeout=60.0)
        if not breaker.allow_request():
            logger.warning("JSearch circuit breaker is OPEN. Skipping request.")
            return []

        api_key = settings.JSEARCH_API_KEY
        if not api_key or api_key.startswith("mock-"):
            logger.info("Using JSearch Mock Data (mock API Key).")
            return self._get_mock_fallback_data(query, location, remote_only=False)

        search_query = query
        if location:
            search_query += f" in {location}"
        else:
            search_query += " in Pakistan"

        jsearch_date_posted = "month"
        if date_posted == "today":
            jsearch_date_posted = "today"
        elif date_posted == "3days":
            jsearch_date_posted = "3days"
        elif date_posted == "week":
            jsearch_date_posted = "week"
        elif date_posted == "month":
            jsearch_date_posted = "month"
        elif date_posted == "any":
            jsearch_date_posted = "all"

        async with SEMAPHORES["JSearch"]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "X-RapidAPI-Key": api_key,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
                }
                params = {
                    "query": search_query,
                    "page": 1,
                    "num_pages": 1,
                    "date_posted": jsearch_date_posted
                }
                try:
                    response = await self._make_api_request(
                        client, "GET", "https://jsearch.p.rapidapi.com/search-v2", headers=headers, params=params
                    )
                    data_obj = response.json().get("data", {})
                    data = data_obj.get("jobs", []) if isinstance(data_obj, dict) else []
                    
                    jobs = []
                    for item in data:
                        title = item.get("job_title", "Software Developer")
                        company = item.get("employer_name", "Tech Company")
                        loc = item.get("job_city") or item.get("job_country") or location or "Pakistan"
                        remote = item.get("job_is_remote", False)
                        jd_text = item.get("job_description", "")
                        
                        posted_at = item.get("job_posted_at_datetime_utc")
                        is_closed = not item.get("job_is_active", True) or not item.get("job_apply_is_active", True) or is_job_description_closed(jd_text)
                        
                        if exclude_closed and is_closed:
                            continue
                        
                        jobs.append({
                            "source": self._normalize_source(item.get("job_publisher", "JSearch")),
                            "title": title,
                            "company": company,
                            "location": loc,
                            "remote": remote,
                            "apply_url": item.get("job_apply_link"),
                            "jd_text": jd_text,
                            "posted_at": posted_at,
                            "is_closed": is_closed
                        })
                    breaker.record_success()
                    return jobs
                except Exception as e:
                    breaker.record_failure()
                    logger.error(f"JSearch API error: {e}")
                    return []

    async def _fetch_jooble(self, query: str, location: Optional[str], date_posted: str = "week", exclude_closed: bool = True) -> List[Dict[str, Any]]:
        """Fetch listings from Jooble Aggregator."""
        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("jooble_api", failure_threshold=3, recovery_timeout=60.0)
        if not breaker.allow_request():
            logger.warning("Jooble circuit breaker is OPEN. Skipping request.")
            return []

        api_key = settings.JOOBLE_API_KEY
        if not api_key or api_key.startswith("mock-"):
            logger.info("Using Jooble Mock Data (mock API Key).")
            return self._get_mock_fallback_data(query, location, remote_only=False)

        import datetime
        datecreatedfrom = None
        now = datetime.datetime.now(datetime.timezone.utc)
        if date_posted == "today":
            datecreatedfrom = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_posted == "3days":
            datecreatedfrom = (now - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
        elif date_posted == "week":
            datecreatedfrom = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        elif date_posted == "month":
            datecreatedfrom = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

        loc_str = location or "Pakistan"
        async with SEMAPHORES["Jooble"]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://jooble.org/api/{api_key}"
                payload = {
                    "keywords": query,
                    "location": loc_str
                }
                if datecreatedfrom:
                    payload["datecreatedfrom"] = datecreatedfrom
                try:
                    response = await self._make_api_request(client, "POST", url, json=payload)
                    data = response.json().get("jobs", [])
                    
                    jobs = []
                    for item in data:
                        title = item.get("title", "Software Developer")
                        company = item.get("company", "Tech Company")
                        loc = item.get("location") or loc_str
                        remote = "remote" in title.lower() or "remote" in loc.lower()
                        jd_snippet = item.get("snippet", "")
                        
                        posted_at = item.get("updated")
                        is_closed = is_job_description_closed(jd_snippet)
                        
                        if exclude_closed and is_closed:
                            continue
                        
                        jobs.append({
                            "source": "Jooble",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "remote": remote,
                            "apply_url": item.get("link"),
                            "jd_text": jd_snippet,
                            "posted_at": posted_at,
                            "is_closed": is_closed
                        })
                    breaker.record_success()
                    return jobs
                except Exception as e:
                    breaker.record_failure()
                    logger.error(f"Jooble API error: {e}")
                    return []

    async def _fetch_remotive(self, query: str, date_posted: str = "week", exclude_closed: bool = True) -> List[Dict[str, Any]]:
        """Fetch listings from Remotive API."""
        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("remotive_api", failure_threshold=3, recovery_timeout=60.0)
        if not breaker.allow_request():
            logger.warning("Remotive circuit breaker is OPEN. Skipping request.")
            return []

        async with SEMAPHORES["Remotive"]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://remotive.com/api/remote-jobs"
                params = {
                    "search": query,
                    "limit": 20
                }
                try:
                    response = await self._make_api_request(client, "GET", url, params=params)
                    data = response.json().get("jobs", [])
                    
                    jobs = []
                    for item in data:
                        title = item.get("title", "Software Developer")
                        company = item.get("company_name", "Tech Company")
                        loc = item.get("candidate_required_location") or "Remote"
                        jd_text = item.get("description", "")
                        
                        posted_at = item.get("publication_date")
                        is_closed = is_job_description_closed(jd_text)
                        
                        if exclude_closed and is_closed:
                            continue
                        if not _is_within_date_range(posted_at, date_posted):
                            continue
                        
                        jobs.append({
                            "source": "Remotive",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "remote": True,
                            "apply_url": item.get("url"),
                            "jd_text": jd_text,
                            "posted_at": posted_at,
                            "is_closed": is_closed
                        })
                    breaker.record_success()
                    return jobs
                except Exception as e:
                    breaker.record_failure()
                    logger.error(f"Remotive API error: {e}")
                    return []

    async def _fetch_arbeitnow(self, query: str, date_posted: str = "week", exclude_closed: bool = True) -> List[Dict[str, Any]]:
        """Fetch listings from Arbeitnow API."""
        from app.services.circuit_breaker import get_circuit_breaker
        breaker = get_circuit_breaker("arbeitnow_api", failure_threshold=3, recovery_timeout=60.0)
        if not breaker.allow_request():
            logger.warning("Arbeitnow circuit breaker is OPEN. Skipping request.")
            return []

        async with SEMAPHORES["Arbeitnow"]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://www.arbeitnow.com/api/job-board-api"
                try:
                    response = await self._make_api_request(client, "GET", url)
                    data = response.json().get("data", [])
                    
                    query_words = set(query.lower().split())
                    stopwords = {"in", "and", "with", "the", "for", "at", "on", "to", "of", "or", "a", "an", "is", "are", "from", "by", "pakistan"}
                    query_keywords = query_words - stopwords
                    if not query_keywords:
                        query_keywords = query_words
                    
                    jobs = []
                    for item in data:
                        title = item.get("title", "Software Developer")
                        company = item.get("company_name", "Tech Company")
                        jd = item.get("description", "")
                        
                        posted_at = item.get("created_at")
                        is_closed = is_job_description_closed(jd)
                        
                        if exclude_closed and is_closed:
                            continue
                        if not _is_within_date_range(posted_at, date_posted):
                            continue
                        
                        text_to_check = title.lower()
                        match_found = False
                        for w in query_keywords:
                            if len(w) <= 3:
                                if re.search(r'\b' + re.escape(w) + r'\b', text_to_check):
                                    match_found = True
                                    break
                            else:
                                if w in text_to_check:
                                    match_found = True
                                    break
                        
                        if match_found:
                            jobs.append({
                                "source": "Arbeitnow",
                                "title": title,
                                "company": company,
                                "location": item.get("location") or "Remote",
                                "remote": item.get("remote", False),
                                "apply_url": item.get("url"),
                                "jd_text": jd,
                                "posted_at": posted_at,
                                "is_closed": is_closed
                            })
                    breaker.record_success()
                    return jobs
                except Exception as e:
                    breaker.record_failure()
                    logger.error(f"Arbeitnow API error: {e}")
                    return []

    def _get_mock_fallback_data(self, query: str, location: Optional[str], remote_only: bool) -> List[Dict[str, Any]]:
        """Generate relevant mock job listings matching the query criteria."""
        query_words = set(query.lower().split())
        stopwords = {"in", "and", "with", "the", "for", "at", "on", "to", "of", "or", "a", "an", "is", "are", "from", "by", "pakistan"}
        query_keywords = query_words - stopwords
        if not query_keywords:
            query_keywords = query_words
            
        loc_str = location.lower() if location else ""
        
        filtered = []
        for job in MOCK_JOBS:
            text_to_match = f"{job['title']} {job['jd_text']}".lower()
            match_found = False
            for w in query_keywords:
                if len(w) <= 3:
                    if re.search(r'\b' + re.escape(w) + r'\b', text_to_match):
                        match_found = True
                        break
                else:
                    if w in text_to_match:
                        match_found = True
                        break
            if query_keywords and not match_found:
                continue
                
            if remote_only and not job["remote"]:
                continue
                
            if loc_str and loc_str not in job["location"].lower():
                continue
                
            filtered.append(job)
            
        if not filtered and query_keywords:
            for job in MOCK_JOBS:
                text_to_match = f"{job['title']} {job['jd_text']}".lower()
                match_found = False
                for w in query_keywords:
                    if len(w) <= 3:
                        if re.search(r'\b' + re.escape(w) + r'\b', text_to_match):
                            match_found = True
                            break
                    else:
                        if w in text_to_match:
                            match_found = True
                            break
                if match_found:
                    filtered.append(job)
                    
        return filtered

    def _search_db_jobs(self, query: str, location: Optional[str], remote_only: bool, profile_embedding: Optional[List[float]] = None, date_posted: str = "week", exclude_closed: bool = True) -> List[Dict[str, Any]]:
        """Query previously ingested/crawled jobs in the local database matching keywords or semantic profile."""
        jobs = []
        if not self.db_reachable:
            return jobs
            
        conn = None
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cursor:
                conditions = ["freshness_status = 'active'"]
                params = []
                
                query_words = [w.strip().lower() for w in query.split() if len(w) >= 2]
                stopwords = {"in", "and", "with", "the", "for", "at", "on", "to", "of", "or", "a", "an", "is", "are", "from", "by", "pakistan"}
                query_keywords = [w for w in query_words if w not in stopwords]
                if not query_keywords and query_words:
                    query_keywords = query_words
                
                if query_keywords:
                    kw_conditions = []
                    for kw in query_keywords:
                        kw_conditions.append("(title ILIKE %s OR jd_text ILIKE %s)")
                        params.extend([f"%{kw}%", f"%{kw}%"])
                    conditions.append(f"({' OR '.join(kw_conditions)})")
                
                if location:
                    conditions.append("location ILIKE %s")
                    params.append(f"%{location}%")
                    
                if remote_only:
                    conditions.append("remote = TRUE")
                    
                if date_posted and date_posted != "any":
                    interval_map = {
                        "today": "1 day",
                        "3days": "3 days",
                        "week": "7 days",
                        "month": "30 days"
                    }
                    interval = interval_map.get(date_posted)
                    if interval:
                        conditions.append(f"fetched_at >= NOW() - INTERVAL '{interval}'")
                
                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                
                if profile_embedding:
                    vector_str = "[" + ",".join(map(str, profile_embedding)) + "]"
                    sql = f"""
                        SELECT source, title, company, location, remote, jd_text, apply_url, job_hash, jd_embedding, fetched_at
                        FROM jobs
                        {where_clause}
                        ORDER BY jd_embedding <=> %s ASC
                        LIMIT 30;
                    """
                    cursor.execute(sql, tuple(params) + (vector_str,))
                else:
                    sql = f"""
                        SELECT source, title, company, location, remote, jd_text, apply_url, job_hash, jd_embedding, fetched_at
                        FROM jobs
                        {where_clause}
                        ORDER BY fetched_at DESC
                        LIMIT 30;
                    """
                    cursor.execute(sql, tuple(params))
                
                rows = cursor.fetchall()
                for row in rows:
                    source, title, company, loc, remote, jd_text, apply_url, job_hash, jd_embedding, fetched_at = row
                    emb_list = None
                    if jd_embedding is not None:
                        if isinstance(jd_embedding, str):
                            try:
                                emb_list = [float(x) for x in jd_embedding.strip("[]").split(",")]
                            except Exception:
                                pass
                        elif isinstance(jd_embedding, list):
                            emb_list = [float(x) for x in jd_embedding]
                    
                    is_closed = is_job_description_closed(jd_text)
                    if exclude_closed and is_closed:
                        continue
                        
                    jobs.append({
                        "source": source,
                        "title": title,
                        "company": company,
                        "location": loc,
                        "remote": remote,
                        "apply_url": apply_url,
                        "jd_text": jd_text,
                        "job_hash": job_hash,
                        "jd_embedding": emb_list,
                        "posted_at": fetched_at.isoformat() if fetched_at else None,
                        "is_closed": is_closed
                    })
                    
        except Exception as e:
            logger.error(f"Error querying jobs from database: {e}")
        finally:
            if conn:
                conn.close()
                
        return jobs

    async def _scrape_linkedin_playwright(self, query: str, location: Optional[str], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        import sys
        if sys.platform == "win32":
            try:
                loop = asyncio.get_running_loop()
                if not isinstance(loop, getattr(asyncio, "ProactorEventLoop", ())):
                    def _run(q, l, u):
                        p_loop = asyncio.ProactorEventLoop()
                        asyncio.set_event_loop(p_loop)
                        try:
                            return p_loop.run_until_complete(self._scrape_linkedin_playwright_impl(q, l, u))
                        finally:
                            p_loop.close()
                    return await asyncio.to_thread(_run, query, location, user_id)
            except Exception:
                pass
        return await self._scrape_linkedin_playwright_impl(query, location, user_id)

    async def _scrape_linkedin_playwright_impl(self, query: str, location: Optional[str], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info(f"Starting Playwright LinkedIn scraper for query: {query}")
        jobs = []
        try:
            from playwright.async_api import async_playwright
            from app.utils import get_platform_cookies
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--blink-settings=imagesEnabled=false"]
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                
                # Check for synced cookies
                if user_id:
                    try:
                        cookies = await get_platform_cookies(user_id, "linkedin")
                        if cookies:
                            logger.info("Injecting synced LinkedIn cookies for scraper...")
                            playwright_cookies = []
                            for c in cookies:
                                expires = c.get("expirationDate") or c.get("expires")
                                pc = {
                                    "name": c["name"],
                                    "value": c["value"],
                                    "domain": c["domain"],
                                    "path": c.get("path", "/"),
                                    "secure": c.get("secure", True),
                                    "httpOnly": c.get("httpOnly", False),
                                }
                                if expires is not None:
                                    try:
                                        pc["expires"] = float(expires)
                                    except (ValueError, TypeError):
                                        pass
                                playwright_cookies.append(pc)
                            await context.add_cookies(playwright_cookies)
                    except Exception as e:
                        logger.warning(f"Failed to load synced LinkedIn cookies: {e}")
                
                page = await context.new_page()
                await page.add_init_script("delete navigator.__proto__.webdriver;")
                
                # Construct search URL
                loc_str = location or ""
                url = f"https://www.linkedin.com/jobs/search?keywords={query}&location={loc_str}"
                
                logger.info(f"Navigating to LinkedIn URL: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                
                # Extract jobs
                card_selectors = ["li.jobs-search-results__list-item", "ul.jobs-search__results-list li", "div.base-card"]
                cards = []
                for selector in card_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=2500)
                        cards = await page.locator(selector).all()
                        if len(cards) > 0:
                            logger.info(f"LinkedIn scraper matched selector '{selector}' with {len(cards)} cards.")
                            break
                    except Exception:
                        continue
                
                if not cards:
                    cards = await page.locator("li").all()
                    
                logger.info(f"LinkedIn scraper found {len(cards)} job cards on page.")
                
                for card in cards[:15]:
                    try:
                        title, company, loc, job_url = "", "", "", ""
                        
                        # Dynamic parsing fallback based on login status and DOM variations
                        title_el = card.locator("h3.base-search-card__title, a.job-card-list__title, a.base-card__full-link")
                        if await title_el.count() > 0:
                            title = (await title_el.first.inner_text()).strip()
                            job_url = await title_el.first.get_attribute("href")
                            
                        comp_el = card.locator("h4.base-search-card__subtitle, span.job-card-container__primary-description, a.hidden-nested-link")
                        if await comp_el.count() > 0:
                            company = (await comp_el.first.inner_text()).strip()
                            
                        loc_el = card.locator("span.job-search-card__location, li.job-card-container__metadata-item")
                        if await loc_el.count() > 0:
                            loc = (await loc_el.first.inner_text()).strip()
                            
                        if not job_url:
                            link_el = card.locator("a.base-card__full-link, a.base-search-card--link")
                            if await link_el.count() > 0:
                                job_url = await link_el.first.get_attribute("href")
                        
                        if job_url and not job_url.startswith("http"):
                            job_url = "https://www.linkedin.com" + job_url
                            
                        # Strip query parameters from job URL
                        if job_url:
                            job_url = job_url.split("?")[0]
                            
                        # Normalize unicode accents for cross-platform robustness
                        title = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').decode('utf-8').strip()
                        company = unicodedata.normalize('NFKD', company).encode('ASCII', 'ignore').decode('utf-8').strip()
                        loc = unicodedata.normalize('NFKD', loc).encode('ASCII', 'ignore').decode('utf-8').strip()
                            
                        # Set description snippet enriched with query terms
                        jd_text = f"Apply directly on LinkedIn to explore this opportunity as a {title} at {company} in {loc or loc_str or 'Remote'}. Key requirements align with {query}."
                        
                        if title and company:
                            jobs.append({
                                "source": "LinkedIn",
                                "title": title,
                                "company": company,
                                "location": loc or loc_str or "Remote",
                                "remote": "remote" in title.lower() or "remote" in (loc or "").lower(),
                                "apply_url": job_url or "https://www.linkedin.com/jobs",
                                "jd_text": jd_text,
                                "is_closed": False
                            })
                    except Exception as card_err:
                        logger.error(f"Error parsing LinkedIn job card: {card_err}")
                await browser.close()
        except Exception as e:
            logger.error(f"LinkedIn Playwright scraper failed: {e}")
        return jobs

    async def _scrape_indeed_playwright(self, query: str, location: Optional[str], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        import sys
        if sys.platform == "win32":
            try:
                loop = asyncio.get_running_loop()
                if not isinstance(loop, getattr(asyncio, "ProactorEventLoop", ())):
                    def _run(q, l, u):
                        p_loop = asyncio.ProactorEventLoop()
                        asyncio.set_event_loop(p_loop)
                        try:
                            return p_loop.run_until_complete(self._scrape_indeed_playwright_impl(q, l, u))
                        finally:
                            p_loop.close()
                    return await asyncio.to_thread(_run, query, location, user_id)
            except Exception:
                pass
        return await self._scrape_indeed_playwright_impl(query, location, user_id)

    async def _scrape_indeed_playwright_impl(self, query: str, location: Optional[str], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info(f"Starting Playwright Indeed scraper for query: {query}")
        jobs = []
        try:
            from playwright.async_api import async_playwright
            from app.utils import get_platform_cookies
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--blink-settings=imagesEnabled=false"]
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                
                # Check for synced cookies
                if user_id:
                    try:
                        cookies = await get_platform_cookies(user_id, "indeed")
                        if cookies:
                            logger.info("Injecting synced Indeed cookies for scraper...")
                            playwright_cookies = []
                            for c in cookies:
                                expires = c.get("expirationDate") or c.get("expires")
                                pc = {
                                    "name": c["name"],
                                    "value": c["value"],
                                    "domain": c["domain"],
                                    "path": c.get("path", "/"),
                                    "secure": c.get("secure", True),
                                    "httpOnly": c.get("httpOnly", False),
                                }
                                if expires is not None:
                                    try:
                                        pc["expires"] = float(expires)
                                    except (ValueError, TypeError):
                                        pass
                                playwright_cookies.append(pc)
                            await context.add_cookies(playwright_cookies)
                    except Exception as e:
                        logger.warning(f"Failed to load synced Indeed cookies: {e}")
                
                page = await context.new_page()
                await page.add_init_script("delete navigator.__proto__.webdriver;")
                
                loc_str = location or ""
                url = f"https://www.indeed.com/jobs?q={query}&l={loc_str}"
                logger.info(f"Navigating to Indeed URL: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                
                # Wait for job cards with multiple selectors
                card_selectors = ["div.job_seen_beacon", "td.result", "div[class*='jobCard']", "div.cardOutline", "li.css-5lfssm"]
                cards = []
                for selector in card_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=2500)
                        cards = await page.locator(selector).all()
                        if len(cards) > 0:
                            logger.info(f"Indeed scraper matched selector '{selector}' with {len(cards)} cards.")
                            break
                    except Exception:
                        continue
                        
                if not cards:
                    cards = await page.locator("div.job_seen_beacon").all()
                    
                logger.info(f"Indeed scraper found {len(cards)} job cards on page.")
                
                for card in cards[:15]:
                    try:
                        title, company, loc, job_url, jd_text = "", "", "", "", ""
                        
                        title_el = card.locator("h2.jobTitle span, a.jcs-JobTitle, h2.jobTitle a")
                        if await title_el.count() > 0:
                            title = (await title_el.first.inner_text()).strip()
                            
                        link_el = card.locator("h2.jobTitle a, a.jcs-JobTitle")
                        if await link_el.count() > 0:
                            job_url = await link_el.first.get_attribute("href")
                            if job_url and not job_url.startswith("http"):
                                job_url = "https://www.indeed.com" + job_url
                                
                        comp_el = card.locator("[data-testid='company-name'], span.companyName")
                        if await comp_el.count() > 0:
                            company = (await comp_el.first.inner_text()).strip()
                            
                        loc_el = card.locator("[data-testid='text-location'], div.companyLocation")
                        if await loc_el.count() > 0:
                            loc = (await loc_el.first.inner_text()).strip()
                            
                        snippet_el = card.locator("div.metadata, div.job-snippet")
                        if await snippet_el.count() > 0:
                            jd_text = (await snippet_el.first.inner_text()).strip()
                        if not jd_text:
                            jd_text = f"Apply directly on Indeed to explore this opportunity as a {title} at {company} in {loc or loc_str or 'Remote'}. Key requirements align with {query}."
                        
                        if job_url:
                            job_url = job_url.split("?")[0]
                            
                        # Normalize unicode accents for cross-platform robustness
                        title = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').decode('utf-8').strip()
                        company = unicodedata.normalize('NFKD', company).encode('ASCII', 'ignore').decode('utf-8').strip()
                        loc = unicodedata.normalize('NFKD', loc).encode('ASCII', 'ignore').decode('utf-8').strip()
                            
                        if title and company:
                            jobs.append({
                                "source": "Indeed",
                                "title": title,
                                "company": company,
                                "location": loc or loc_str or "Remote",
                                "remote": "remote" in title.lower() or "remote" in (loc or "").lower(),
                                "apply_url": job_url or "https://www.indeed.com",
                                "jd_text": jd_text,
                                "is_closed": False
                            })
                    except Exception as card_err:
                        logger.error(f"Error parsing Indeed job card: {card_err}")
                await browser.close()
        except Exception as e:
            logger.error(f"Indeed Playwright scraper failed: {e}")
        return jobs

    async def _scrape_glassdoor_playwright(self, query: str, location: Optional[str], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        import sys
        if sys.platform == "win32":
            try:
                loop = asyncio.get_running_loop()
                if not isinstance(loop, getattr(asyncio, "ProactorEventLoop", ())):
                    def _run(q, l, u):
                        p_loop = asyncio.ProactorEventLoop()
                        asyncio.set_event_loop(p_loop)
                        try:
                            return p_loop.run_until_complete(self._scrape_glassdoor_playwright_impl(q, l, u))
                        finally:
                            p_loop.close()
                    return await asyncio.to_thread(_run, query, location, user_id)
            except Exception:
                pass
        return await self._scrape_glassdoor_playwright_impl(query, location, user_id)

    async def _scrape_glassdoor_playwright_impl(self, query: str, location: Optional[str], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info(f"Starting Playwright Glassdoor scraper for query: {query}")
        jobs = []
        try:
            from playwright.async_api import async_playwright
            from app.utils import get_platform_cookies
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--blink-settings=imagesEnabled=false"]
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                
                # Check for synced cookies
                if user_id:
                    try:
                        cookies = await get_platform_cookies(user_id, "glassdoor")
                        if cookies:
                            logger.info("Injecting synced Glassdoor cookies for scraper...")
                            playwright_cookies = []
                            for c in cookies:
                                expires = c.get("expirationDate") or c.get("expires")
                                pc = {
                                    "name": c["name"],
                                    "value": c["value"],
                                    "domain": c["domain"],
                                    "path": c.get("path", "/"),
                                    "secure": c.get("secure", True),
                                    "httpOnly": c.get("httpOnly", False),
                                }
                                if expires is not None:
                                    try:
                                        pc["expires"] = float(expires)
                                    except (ValueError, TypeError):
                                        pass
                                playwright_cookies.append(pc)
                            await context.add_cookies(playwright_cookies)
                    except Exception as e:
                        logger.warning(f"Failed to load synced Glassdoor cookies: {e}")
                
                page = await context.new_page()
                await page.add_init_script("delete navigator.__proto__.webdriver;")
                
                loc_str = location or ""
                url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query}&locKeyword={loc_str}" if loc_str else f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query}"
                logger.info(f"Navigating to Glassdoor URL: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                
                # Wait for job listing elements with multiple selectors
                card_selectors = ["li[data-test='jobListing']", "li[class*='jobListItem']", "div[class*='jobCard']", "article"]
                cards = []
                for selector in card_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=2500)
                        cards = await page.locator(selector).all()
                        if len(cards) > 0:
                            logger.info(f"Glassdoor scraper matched selector '{selector}' with {len(cards)} cards.")
                            break
                    except Exception:
                        continue
                        
                if not cards:
                    cards = await page.locator("li[data-test='jobListing']").all()
                    
                logger.info(f"Glassdoor scraper found {len(cards)} job cards on page.")
                
                for card in cards[:15]:
                    try:
                        title, company, loc, job_url, jd_text = "", "", "", "", ""
                        
                        title_el = card.locator("a[data-test='job-title'], a[class*='jobTitle'], a[class*='job-title']")
                        if await title_el.count() > 0:
                            title = (await title_el.first.inner_text()).strip()
                            job_url = await title_el.first.get_attribute("href")
                            if job_url and not job_url.startswith("http"):
                                job_url = "https://www.glassdoor.com" + job_url
                                
                        comp_el = card.locator("span[class*='EmployerName'], div[class*='employerName'], [data-test='employer-name']")
                        if await comp_el.count() > 0:
                            company = (await comp_el.first.inner_text()).strip()
                            if "\n" in company:
                                company = company.split("\n")[0]
                            
                        loc_el = card.locator("div[data-test='emp-location'], [class*='location']")
                        if await loc_el.count() > 0:
                            loc = (await loc_el.first.inner_text()).strip()
                            
                        if job_url:
                            job_url = job_url.split("?")[0]
                            
                        # Normalize unicode accents for cross-platform robustness
                        title = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').decode('utf-8').strip()
                        company = unicodedata.normalize('NFKD', company).encode('ASCII', 'ignore').decode('utf-8').strip()
                        loc = unicodedata.normalize('NFKD', loc).encode('ASCII', 'ignore').decode('utf-8').strip()
                            
                        jd_text = f"Apply directly on Glassdoor to explore this opportunity as a {title} at {company} in {loc or loc_str or 'Remote'}. Key requirements align with {query}."
                        
                        if title and company:
                            jobs.append({
                                "source": "Glassdoor",
                                "title": title,
                                "company": company,
                                "location": loc or loc_str or "Remote",
                                "remote": "remote" in title.lower() or "remote" in (loc or "").lower(),
                                "apply_url": job_url or "https://www.glassdoor.com",
                                "jd_text": jd_text,
                                "is_closed": False
                            })
                    except Exception as card_err:
                        logger.error(f"Error parsing Glassdoor job card: {card_err}")
                await browser.close()
        except Exception as e:
            logger.error(f"Glassdoor Playwright scraper failed: {e}")
        return jobs

    async def search_and_rank_jobs(self, payload: JobSearchRequest) -> JobSearchResponse:
        """
        Coordinate concurrent job retrieval, deduplication, caching, RAG/vector matching, and ranking.
        """
        # Query expansion for short/ambiguous queries
        original_query = payload.query.strip() if payload.query else ""
        query_lower = original_query.lower()
        expansion_map = {
            # Abbreviations
            "ai": "artificial intelligence machine learning AI engineer",
            "ml": "machine learning data science ML engineer",
            "ds": "data science data analyst data engineer",
            "qa": "quality assurance QA test engineer",
            "dev": "software developer engineer programmer",
            "pm": "product manager project manager",
            "sre": "site reliability engineer DevOps infrastructure",
            "sde": "software development engineer backend",
            "dba": "database administrator SQL PostgreSQL",
            "ui": "UI designer user interface frontend",
            "ux": "UX designer user experience researcher",
            # Common role searches
            "frontend": "frontend developer react angular vue javascript",
            "front-end": "frontend developer react angular vue javascript",
            "backend": "backend developer python java node.js API server",
            "back-end": "backend developer python java node.js API server",
            "fullstack": "fullstack developer frontend backend react node python",
            "full-stack": "fullstack developer frontend backend react node python",
            "devops": "DevOps engineer cloud infrastructure CI/CD kubernetes docker",
            "mobile": "mobile developer iOS android react native flutter",
            "data": "data engineer data scientist data analyst",
            "cloud": "cloud engineer AWS Azure GCP infrastructure",
            "security": "cybersecurity security engineer information security",
            "infosec": "cybersecurity information security analyst",
        }
        if query_lower in expansion_map:
            payload.query = expansion_map[query_lower]
            logger.info(f"Expanded short query '{original_query}' to '{payload.query}'")

        query_hash = hashlib.sha256(
            f"{payload.query}|{payload.location or ''}|{payload.remote_only}".encode('utf-8')
        ).hexdigest()
        
        # 1. Load User profile and embedding beforehand to perform local RAG semantic database query
        profile = None
        profile_embedding = None
        applied_hashes = set()
        
        from app.services.llm_client import llm_client_search as llm_client
        
        if payload.user_id:
            profile, profile_embedding = await asyncio.to_thread(self._fetch_profile_and_embedding, payload.user_id)
            applied_hashes = await asyncio.to_thread(self._get_applied_hashes, payload.user_id)
            
            if profile and not profile_embedding:
                from app.services.embedding_service import serialize_profile
                try:
                    serialized_text = serialize_profile(profile)
                    profile_embedding = llm_client.generate_embedding(serialized_text)
                    await asyncio.to_thread(self._update_profile_embedding, payload.user_id, profile_embedding)
                except Exception as e:
                    logger.warning(f"Could not generate profile embedding on the fly: {e}")

        # 2. Check cache
        cached_jobs = await asyncio.to_thread(self._get_cached_results, query_hash)
        if cached_jobs:
            raw_jobs = cached_jobs
        else:
            # 3. Fetch live data concurrently with a responsive timeout (up to 9.0s) to include fast scrapers
            async def fetch_all_live():
                live_tasks = {
                    "jsearch": self._fetch_jsearch(payload.query, payload.location, payload.date_posted, payload.exclude_closed),
                    "jooble": self._fetch_jooble(payload.query, payload.location, payload.date_posted, payload.exclude_closed),
                    "remotive": self._fetch_remotive(payload.query, payload.date_posted, payload.exclude_closed),
                    "arbeitnow": self._fetch_arbeitnow(payload.query, payload.date_posted, payload.exclude_closed),
                    "linkedin": self._scrape_linkedin_playwright(payload.query, payload.location, payload.user_id),
                    "indeed": self._scrape_indeed_playwright(payload.query, payload.location, payload.user_id),
                    "glassdoor": self._scrape_glassdoor_playwright(payload.query, payload.location, payload.user_id),
                }
                
                pending = {name: asyncio.create_task(coro) for name, coro in live_tasks.items()}
                done_results = []
                
                # Stage 1: 0 to 3.0 seconds (Fastest APIs)
                done, pending_set = await asyncio.wait(pending.values(), timeout=3.0)
                for task in done:
                    try:
                        done_results.extend(task.result())
                    except Exception as e:
                        logger.error(f"Fast API fetch failed: {e}")
                        
                still_pending = {name: task for name, task in pending.items() if task not in done}
                
                if still_pending:
                    # Stage 2: 3.0 to 12.0 seconds (Allow fast scrapers like LinkedIn, Glassdoor, Indeed to complete)
                    done_slow, pending_set_slow = await asyncio.wait(still_pending.values(), timeout=9.0)
                    for task in done_slow:
                        try:
                            done_results.extend(task.result())
                        except Exception as e:
                            logger.error(f"Slow API/scraper fetch failed: {e}")
                            
                    # Stage 3: 12+ seconds (Background enrichment and update cache for any trailing requests)
                    final_pending = [t for t in still_pending.values() if t not in done_slow]
                    if final_pending:
                        logger.info(f"Backgrounding {len(final_pending)} slow API tasks for cache enrichment...")
                        async def background_enrich():
                            try:
                                done_bg, _ = await asyncio.wait(final_pending, timeout=15.0)
                                bg_jobs = []
                                for t in done_bg:
                                    try:
                                        bg_jobs.extend(t.result())
                                    except Exception:
                                        pass
                                if bg_jobs:
                                    await asyncio.to_thread(self._enrich_cache, query_hash, bg_jobs)
                            except Exception as ex:
                                logger.error(f"Background cache enrichment failed: {ex}")
                                
                        def _bg_task_done(t):
                            if t.cancelled():
                                return
                            exc = t.exception()
                            if exc:
                                logger.error(f"Background enrichment task raised: {exc}")

                        bg_task = asyncio.create_task(background_enrich())
                        bg_task.add_done_callback(_bg_task_done)
                        
                return done_results

            # Gather db_jobs (local RAG) and live_jobs concurrently
            db_jobs_task = asyncio.to_thread(self._search_db_jobs, payload.query, payload.location, payload.remote_only, profile_embedding, payload.date_posted, payload.exclude_closed)
            db_jobs, live_jobs = await asyncio.gather(db_jobs_task, fetch_all_live())
            
            raw_jobs = db_jobs + live_jobs
            
            if payload.location:
                # Split multi-city input into individual location tokens
                # e.g. "Karachi, Lahore, Pakistan" -> ["karachi", "lahore", "pakistan"]
                loc_tokens = [t.strip().lower() for t in re.split(r'[,;/]+', payload.location) if t.strip()]
                if not loc_tokens:
                    loc_tokens = [payload.location.lower().strip()]
                
                # Expand country keywords to major metropolitan cities
                country_cities_map = {
                    "pakistan": {"karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "peshawar", "multan", "quetta", "sialkot", "gujranwala", "hyderabad", "pakistan", "pk"},
                    "pk": {"karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "peshawar", "multan", "quetta", "sialkot", "gujranwala", "hyderabad", "pakistan", "pk"},
                    "us": {"new york", "san francisco", "austin", "seattle", "chicago", "los angeles", "boston", "denver", "atlanta", "remote", "united states", "usa", "us"},
                    "usa": {"new york", "san francisco", "austin", "seattle", "chicago", "los angeles", "boston", "denver", "atlanta", "remote", "united states", "usa", "us"},
                    "united states": {"new york", "san francisco", "austin", "seattle", "chicago", "los angeles", "boston", "denver", "atlanta", "remote", "united states", "usa", "us"},
                    "uk": {"london", "manchester", "birmingham", "edinburgh", "bristol", "leeds", "united kingdom", "uk"},
                    "united kingdom": {"london", "manchester", "birmingham", "edinburgh", "bristol", "leeds", "united kingdom", "uk"},
                    "canada": {"toronto", "vancouver", "montreal", "ottawa", "calgary", "edmonton", "canada", "ca"},
                    "germany": {"berlin", "munich", "frankfurt", "hamburg", "cologne", "germany", "de"},
                }
                expanded_tokens = set(loc_tokens)
                for lt in loc_tokens:
                    if lt in country_cities_map:
                        expanded_tokens.update(country_cities_map[lt])
                
                live_filtered = []
                for j in raw_jobs:
                    # Normalize unicode accents for clean string matching (e.g. Islāmābād -> Islamabad)
                    raw_loc = unicodedata.normalize('NFKD', j.get("location", "")).encode('ASCII', 'ignore').decode('utf-8')
                    job_loc = raw_loc.lower()
                    
                    # Match if ANY location token appears in the job's location
                    location_match = any(token in job_loc for token in expanded_tokens)
                    # Also match if the job location contains any of the user's tokens
                    reverse_match = any(job_loc in token for token in expanded_tokens if len(token) > 3)
                    # Scraped jobs from platforms queried with location are targeted by definition
                    is_live_targeted = j.get("source") in ["LinkedIn", "Indeed", "Glassdoor"]
                    
                    if location_match or reverse_match or is_live_targeted:
                        live_filtered.append(j)
                    elif j.get("remote", False) and ("worldwide" in job_loc or "anywhere" in job_loc or "remote" in job_loc):
                        # Only include remote jobs that are explicitly worldwide/anywhere
                        live_filtered.append(j)
                raw_jobs = live_filtered

            if payload.query:
                filtered_by_query = []
                query_words = [w.lower().strip() for w in payload.query.split() if len(w) >= 2]
                stopwords = {"in", "and", "with", "the", "for", "at", "on", "to", "of", "or", "a", "an", "is", "are", "from", "by", "pakistan"}
                keywords = [w for w in query_words if w not in stopwords]
                if not keywords and query_words:
                    keywords = query_words
                if not keywords:
                    keywords = [w.lower().strip() for w in payload.query.split()]
                
                for j in raw_jobs:
                    raw_title = unicodedata.normalize('NFKD', j.get("title", "")).encode('ASCII', 'ignore').decode('utf-8')
                    raw_jd = unicodedata.normalize('NFKD', j.get("jd_text", "")).encode('ASCII', 'ignore').decode('utf-8')
                    title_lower = raw_title.lower()
                    jd_lower = raw_jd.lower()
                    match_found = False
                    for k in keywords:
                        pattern = r'\b' + re.escape(k) + r'\b' if len(k) <= 3 else re.escape(k)
                        if re.search(pattern, title_lower) or re.search(pattern, jd_lower):
                            match_found = True
                            break
                    if match_found:
                        filtered_by_query.append(j)
                raw_jobs = filtered_by_query
            if payload.remote_only:
                raw_jobs = [j for j in raw_jobs if j.get("remote", False)]

            if not raw_jobs:
                if payload.location:
                    logger.info("Backup Plan: No local results. Retrying with explicitly worldwide/anywhere remote jobs matching query.")
                    all_fetched = db_jobs + live_jobs
                    # Only include remote jobs that are explicitly worldwide/anywhere — NOT just any remote job
                    remote_jobs = []
                    for j in all_fetched:
                        if j.get("remote", False):
                            jloc = j.get("location", "").lower()
                            if "worldwide" in jloc or "anywhere" in jloc or any(token in jloc for token in loc_tokens):
                                remote_jobs.append(j)
                    
                    if payload.query:
                        filtered_by_query = []
                        for j in remote_jobs:
                            title_lower = j.get("title", "").lower()
                            jd_lower = j.get("jd_text", "").lower()
                            match_found = False
                            for k in keywords:
                                pattern = r'\b' + re.escape(k) + r'\b' if len(k) <= 3 else re.escape(k)
                                if re.search(pattern, title_lower) or re.search(pattern, jd_lower):
                                    match_found = True
                                    break
                            if match_found:
                                filtered_by_query.append(j)
                        raw_jobs = filtered_by_query
                    else:
                        raw_jobs = remote_jobs
                        
                    if payload.remote_only:
                        raw_jobs = [j for j in raw_jobs if j.get("remote", False)]

            if not raw_jobs:
                logger.warning("No matching job listings found in database or live feeds. Falling back to mock dataset.")
                raw_jobs = self._get_mock_fallback_data(payload.query, payload.location, payload.remote_only)

            if not raw_jobs:
                logger.warning("No matching job listings found in database or live feeds, and mock fallback was empty. Returning empty results.")
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No matching job listings found in database or live feeds. Try broadening your keywords or location."
                )

            # Deduplicate by job_hash
            deduped_jobs = []
            seen_hashes = set()
            for rj in raw_jobs:
                job_hash = calculate_job_hash(rj["title"], rj["company"], rj.get("location"))
                if job_hash not in seen_hashes:
                    seen_hashes.add(job_hash)
                    rj["job_hash"] = job_hash
                    deduped_jobs.append(rj)
            
            raw_jobs = deduped_jobs

        # 5. Fast local check of existing job_hash -> id mapping from DB, pre-assigning random UUIDs for new jobs to avoid blocking main thread.
        uuid_mapping = {}
        if self.db_reachable:
            conn = None
            try:
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    job_hashes = [j["job_hash"] for j in raw_jobs]
                    cursor.execute(
                        "SELECT job_hash, id FROM jobs WHERE job_hash = ANY(%s);",
                        (job_hashes,)
                    )
                    for row in cursor.fetchall():
                        uuid_mapping[row[0]] = str(row[1])
            except Exception as e:
                logger.error(f"Error checking existing job UUIDs: {e}")
            finally:
                if conn:
                    conn.close()

        # Pre-assign UUIDs for any jobs not already mapped
        for j in raw_jobs:
            job_hash = j["job_hash"]
            if job_hash not in uuid_mapping:
                uuid_mapping[job_hash] = str(uuid.uuid4())

        # Cache the deduplicated list with resolved embeddings
        if not cached_jobs:
            await asyncio.to_thread(self._set_cached_results, query_hash, raw_jobs)

        # 6. Spawn Background Task for embedding generation & writing to DB
        async def background_store_and_embed(jobs_to_store, mapping):
            try:
                # Batch generate missing embeddings in background
                if profile_embedding:
                    missing_embeddings_jobs = [j for j in jobs_to_store if j.get("jd_embedding") is None]
                    if missing_embeddings_jobs:
                        from app.services.embedding_service import serialize_job
                        texts_to_embed = [serialize_job(j["title"], j["company"], j["jd_text"]) for j in missing_embeddings_jobs]
                        try:
                            embeddings = await llm_client.generate_embeddings_batch_async(texts_to_embed)
                            for j, emb in zip(missing_embeddings_jobs, embeddings):
                                j["jd_embedding"] = emb
                        except Exception as emb_err:
                            logger.warning(f"Background embedding generation failed: {emb_err}")

                # Write to DB using mapping to preserve pre-assigned IDs for new jobs
                if self.db_reachable:
                    conn = None
                    try:
                        conn = self._get_db_connection()
                        with conn.cursor() as cursor:
                            now = datetime.datetime.now(datetime.timezone.utc)
                            for job in jobs_to_store:
                                job_hash = job["job_hash"]
                                job_id = mapping.get(job_hash)
                                embedding = job.get("jd_embedding")
                                
                                if embedding:
                                    cursor.execute(
                                        """
                                        INSERT INTO jobs (id, source, title, company, location, remote, jd_text, apply_url, fetched_at, job_hash, jd_embedding, first_seen_at, last_seen_at, last_verified_at, freshness_status)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW(), 'active')
                                        ON CONFLICT (job_hash) DO UPDATE
                                        SET title = EXCLUDED.title, apply_url = EXCLUDED.apply_url, jd_embedding = EXCLUDED.jd_embedding, last_seen_at = NOW(), last_verified_at = NOW(), freshness_status = 'active';
                                        """,
                                        (
                                            job_id,
                                            job["source"],
                                            job["title"],
                                            job["company"],
                                            job.get("location"),
                                            job.get("remote", False),
                                            job["jd_text"],
                                            job.get("apply_url"),
                                            now,
                                            job_hash,
                                            embedding
                                        )
                                    )
                                else:
                                    cursor.execute(
                                        """
                                        INSERT INTO jobs (id, source, title, company, location, remote, jd_text, apply_url, fetched_at, job_hash, first_seen_at, last_seen_at, last_verified_at, freshness_status)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW(), 'active')
                                        ON CONFLICT (job_hash) DO UPDATE
                                        SET title = EXCLUDED.title, apply_url = EXCLUDED.apply_url, last_seen_at = NOW(), last_verified_at = NOW(), freshness_status = 'active';
                                        """,
                                        (
                                            job_id,
                                            job["source"],
                                            job["title"],
                                            job["company"],
                                            job.get("location"),
                                            job.get("remote", False),
                                            job["jd_text"],
                                            job.get("apply_url"),
                                            now,
                                            job_hash
                                        )
                                    )
                            conn.commit()
                            logger.info(f"Background saved/updated {len(jobs_to_store)} jobs in DB.")
                    except Exception as e:
                        logger.error(f"Failed to background save jobs to DB: {e}")
                        if conn:
                            conn.rollback()
                    finally:
                        if conn:
                            conn.close()
            except Exception as e:
                logger.error(f"Error in background_store_and_embed: {e}")

        asyncio.create_task(background_store_and_embed(raw_jobs, uuid_mapping))

        # 7. Match and Rank
        final_cards = []
        for j in raw_jobs:
            job_hash = j["job_hash"]
            score, explanation, breakdown, matches, gaps, blockers = calculate_match_score_v3(
                j["title"],
                j["jd_text"],
                j.get("location"),
                j.get("remote", False),
                profile,
                payload.query,
                profile_embedding,
                j.get("jd_embedding"),
                llm_client.fallback_occurred
            )
            
            # Calculate freshness score based on age
            first_seen = j.get("first_seen_at") or j.get("fetched_at")
            if isinstance(first_seen, str):
                try:
                    first_seen = datetime.datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
                except Exception:
                    first_seen = datetime.datetime.now(datetime.timezone.utc)
            elif not isinstance(first_seen, datetime.datetime):
                first_seen = datetime.datetime.now(datetime.timezone.utc)
                
            age_days = (datetime.datetime.now(datetime.timezone.utc) - first_seen).days
            fresh_score = max(1.0 - (age_days / 30.0), 0.0)
            
            from app.services.scam_detector import ScamDetector
            safety_score = ScamDetector.analyze_job_safety(
                j["title"],
                j["company"],
                j.get("jd_text") or "",
                j.get("apply_url") or ""
            )

            card_title = unicodedata.normalize('NFKD', str(j.get("title", ""))).encode('ASCII', 'ignore').decode('utf-8').strip()
            card_company = unicodedata.normalize('NFKD', str(j.get("company", ""))).encode('ASCII', 'ignore').decode('utf-8').strip()
            card_location = unicodedata.normalize('NFKD', str(j.get("location") or "")).encode('ASCII', 'ignore').decode('utf-8').strip() if j.get("location") else None
            card_jd = unicodedata.normalize('NFKD', str(j.get("jd_text") or "")).encode('ASCII', 'ignore').decode('utf-8').strip()

            posted_at_raw = j.get("posted_at")
            posted_at_str = None
            if posted_at_raw is not None:
                if isinstance(posted_at_raw, (int, float)):
                    try:
                        posted_at_str = datetime.datetime.fromtimestamp(posted_at_raw, datetime.timezone.utc).isoformat()
                    except Exception:
                        posted_at_str = str(posted_at_raw)
                elif isinstance(posted_at_raw, datetime.datetime):
                    posted_at_str = posted_at_raw.isoformat()
                else:
                    posted_at_str = str(posted_at_raw)

            final_cards.append(JobCard(
                job_id=uuid_mapping.get(job_hash, str(uuid.uuid4())),
                source=j.get("source", "Direct Apply"),
                title=card_title,
                company=card_company,
                location=card_location,
                remote=j.get("remote", False),
                apply_url=j.get("apply_url"),
                jd_text=card_jd,
                fetched_at=datetime.datetime.now(datetime.timezone.utc),
                job_hash=job_hash,
                match_score=score,
                match_explanation=explanation,
                is_applied=job_hash in applied_hashes,
                match_breakdown=breakdown,
                skill_matches=matches,
                skill_gaps=gaps,
                hard_blockers=blockers,
                freshness_score=fresh_score,
                safety_score=safety_score,
                posted_at=posted_at_str,
                is_closed=j.get("is_closed", False)
            ))

        # Apply post-fetch relevance filtering: require meaningful keyword overlap
        if payload.query:
            query_words = [w.lower().strip() for w in payload.query.split() if len(w) >= 2]
            stopwords = {"in", "and", "with", "the", "for", "at", "on", "to", "of", "or", "a", "an", "is", "are", "from", "by", "pakistan"}
            keywords = [w for w in query_words if w not in stopwords]
            if not keywords:
                keywords = query_words
            
            # Require at least 1 keyword in title AND at least 40% keyword coverage in title+JD
            min_coverage = 0.4 if len(keywords) > 2 else 0.5
            
            filtered_cards = []
            for card in final_cards:
                title_lower = card.title.lower()
                jd_lower = (card.jd_text or "").lower()
                combined = title_lower + " " + jd_lower
                
                # Count how many keywords appear in title
                title_hits = 0
                combined_hits = 0
                for k in keywords:
                    pattern = r'\b' + re.escape(k) + r'\b' if len(k) <= 3 else re.escape(k)
                    if re.search(pattern, title_lower):
                        title_hits += 1
                    if re.search(pattern, combined):
                        combined_hits += 1
                
                coverage = combined_hits / len(keywords) if keywords else 0
                
                # Must have at least 1 title hit AND meet minimum coverage threshold, or be from a live scraper with matching keywords
                is_live_scraper = card.source in ["LinkedIn", "Indeed", "Glassdoor"]
                if (title_hits >= 1 and coverage >= min_coverage) or (is_live_scraper and (title_hits >= 1 or combined_hits >= 1)):
                    # Store hit count for sorting
                    card._relevance_hits = combined_hits
                    filtered_cards.append(card)
            
            if filtered_cards:
                final_cards = filtered_cards

        # Sort by relevance hits (desc), then match score (desc)
        def sort_key(card: JobCard) -> Tuple[int, float]:
            hits = getattr(card, '_relevance_hits', 0)
            return (hits, card.match_score or 0.0)

        final_cards.sort(key=sort_key, reverse=True)

        # Apply slice limit
        final_cards = final_cards[:payload.limit]

        return JobSearchResponse(
            query_hash=query_hash,
            jobs=final_cards
        )
