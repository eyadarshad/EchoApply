import os
import logging
import hashlib
import json
import uuid
import datetime
import asyncio
from typing import List, Optional, Dict, Any, Tuple
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.schemas import JobSearchRequest, JobSearchResponse, JobCard, ResumeParsedData

logger = logging.getLogger(__name__)

# Concurrency Semaphores to respect API limits
SEMAPHORES = {
    "JSearch": asyncio.Semaphore(2),
    "Jooble": asyncio.Semaphore(2),
    "Remotive": asyncio.Semaphore(1),
    "Arbeitnow": asyncio.Semaphore(2)
}

# In-memory query cache fallback if database is offline/unreachable
IN_MEMORY_JOB_CACHE: Dict[str, Tuple[List[Dict[str, Any]], datetime.datetime]] = {}

def calculate_job_hash(title: str, company: str, location: Optional[str]) -> str:
    """Generate unique deterministic hash for deduplication based on job title, company, and location."""
    loc = location or ""
    norm_title = " ".join(title.lower().split())
    norm_company = " ".join(company.lower().split())
    norm_location = " ".join(loc.lower().split())
    combined = f"{norm_title}|{norm_company}|{norm_location}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

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

# Rich local mock dataset for testing and fallback mode
MOCK_JOBS = [
    {
        "title": "Python Backend Engineer",
        "company": "TechSolutions Karachi",
        "location": "Karachi, Pakistan",
        "remote": False,
        "apply_url": "https://example.com/jobs/python-karachi",
        "jd_text": "We are seeking a Python Backend Developer with strong knowledge of FastAPI, PostgreSQL, and AWS. Responsible for building microservices, optimizing SQL queries, and configuring Docker containers."
    },
    {
        "title": "Senior React Developer",
        "company": "AppCraft Lahore",
        "location": "Lahore, Pakistan",
        "remote": True,
        "apply_url": "https://example.com/jobs/react-lahore",
        "jd_text": "Looking for a Frontend Developer experienced in React, Next.js, and TypeScript. Skills in CSS Tailwind, responsive layouts, and state management are required."
    },
    {
        "title": "Fullstack Software Developer",
        "company": "Remote LLC",
        "location": "Remote, Pakistan",
        "remote": True,
        "apply_url": "https://example.com/jobs/fullstack-remote",
        "jd_text": "Join our international team working on React, FastAPI, Node.js, and CI/CD pipelines. Build reliable software interfaces and backend endpoints in a fast-paced environment."
    },
    {
        "title": "Java Spring Boot Intern",
        "company": "Enterprise Software Islamabad",
        "location": "Islamabad, Pakistan",
        "remote": False,
        "apply_url": "https://example.com/jobs/java-islamabad",
        "jd_text": "Seeking a Software Engineering Intern/Fresher with knowledge of Java, Spring Boot, SQL, and Git. You will contribute to database migrations, API testing, and core application components."
    },
    {
        "title": "DevOps & Cloud Engineer",
        "company": "CloudScale Solutions",
        "location": "Karachi, Pakistan",
        "remote": True,
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

    def _get_applied_hashes(self, user_id: str) -> set[str]:
        """Fetch set of job hashes that the user has already applied to."""
        applied_hashes = set()
        if self.db_reachable and user_id:
            conn = None
            try:
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT job_hash FROM applications WHERE user_id = %s;",
                        (user_id,)
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
                    for job in jobs:
                        job_hash = job["job_hash"]
                        cursor.execute(
                            """
                            INSERT INTO jobs (source, title, company, location, remote, jd_text, apply_url, fetched_at, job_hash)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (job_hash) DO UPDATE
                            SET title = EXCLUDED.title, apply_url = EXCLUDED.apply_url
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

    def _fetch_profile(self, user_id: str) -> Optional[ResumeParsedData]:
        """Fetch candidate profile from DB if reachable."""
        if self.db_reachable and user_id:
            conn = None
            try:
                conn = self._get_db_connection()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT parsed_resume_json FROM profiles WHERE user_id = %s;",
                        (user_id,)
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

    async def _fetch_jsearch(self, query: str, location: Optional[str]) -> List[Dict[str, Any]]:
        """Fetch listings from JSearch Aggregator (RapidAPI)."""
        api_key = settings.JSEARCH_API_KEY
        if not api_key or api_key.startswith("mock-"):
            logger.info("Using JSearch Mock Data (mock API Key).")
            return []

        search_query = query
        if location:
            search_query += f" in {location}"
        else:
            search_query += " in Pakistan"

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
                    "date_posted": "all"
                }
                try:
                    response = await self._make_api_request(
                        client, "GET", "https://jsearch.p.rapidapi.com/search", headers=headers, params=params
                    )
                    data = response.json().get("data", [])
                    
                    jobs = []
                    for item in data:
                        title = item.get("job_title", "Software Developer")
                        company = item.get("employer_name", "Tech Company")
                        loc = item.get("job_city") or item.get("job_country") or location or "Pakistan"
                        remote = item.get("job_is_remote", False)
                        
                        jobs.append({
                            "source": "JSearch",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "remote": remote,
                            "apply_url": item.get("job_apply_link"),
                            "jd_text": item.get("job_description", "")
                        })
                    return jobs
                except Exception as e:
                    logger.error(f"JSearch API error: {e}")
                    return []

    async def _fetch_jooble(self, query: str, location: Optional[str]) -> List[Dict[str, Any]]:
        """Fetch listings from Jooble Aggregator."""
        api_key = settings.JOOBLE_API_KEY
        if not api_key or api_key.startswith("mock-"):
            logger.info("Using Jooble Mock Data (mock API Key).")
            return []

        loc_str = location or "Pakistan"
        async with SEMAPHORES["Jooble"]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://jooble.org/api/{api_key}"
                payload = {
                    "keywords": query,
                    "location": loc_str
                }
                try:
                    response = await self._make_api_request(client, "POST", url, json=payload)
                    data = response.json().get("jobs", [])
                    
                    jobs = []
                    for item in data:
                        title = item.get("title", "Software Developer")
                        company = item.get("company", "Tech Company")
                        loc = item.get("location") or loc_str
                        remote = "remote" in title.lower() or "remote" in loc.lower()
                        
                        jobs.append({
                            "source": "Jooble",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "remote": remote,
                            "apply_url": item.get("link"),
                            "jd_text": item.get("snippet", "")
                        })
                    return jobs
                except Exception as e:
                    logger.error(f"Jooble API error: {e}")
                    return []

    async def _fetch_remotive(self, query: str) -> List[Dict[str, Any]]:
        """Fetch listings from Remotive API."""
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
                        
                        jobs.append({
                            "source": "Remotive",
                            "title": title,
                            "company": company,
                            "location": loc,
                            "remote": True,
                            "apply_url": item.get("url"),
                            "jd_text": item.get("description", "")
                        })
                    return jobs
                except Exception as e:
                    logger.error(f"Remotive API error: {e}")
                    return []

    async def _fetch_arbeitnow(self, query: str) -> List[Dict[str, Any]]:
        """Fetch listings from Arbeitnow API."""
        async with SEMAPHORES["Arbeitnow"]:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://www.arbeitnow.com/api/job-board-api"
                try:
                    response = await self._make_api_request(client, "GET", url)
                    data = response.json().get("data", [])
                    
                    query_words = set(query.lower().split())
                    jobs = []
                    for item in data:
                        title = item.get("title", "Software Developer")
                        company = item.get("company_name", "Tech Company")
                        jd = item.get("description", "")
                        
                        # filter in-memory by query keywords
                        text_to_check = f"{title} {jd}".lower()
                        if any(w in text_to_check for w in query_words):
                            jobs.append({
                                "source": "Arbeitnow",
                                "title": title,
                                "company": company,
                                "location": item.get("location") or "Remote",
                                "remote": item.get("remote", False),
                                "apply_url": item.get("url"),
                                "jd_text": jd
                            })
                    return jobs
                except Exception as e:
                    logger.error(f"Arbeitnow API error: {e}")
                    return []

    def _get_mock_fallback_data(self, query: str, location: Optional[str], remote_only: bool) -> List[Dict[str, Any]]:
        """Generate relevant mock job listings matching the query criteria."""
        query_words = set(query.lower().split())
        loc_str = location.lower() if location else ""
        
        filtered = []
        for job in MOCK_JOBS:
            # Check query keyword alignment
            text_to_match = f"{job['title']} {job['jd_text']}".lower()
            if query_words and not any(w in text_to_match for w in query_words):
                continue
                
            # Check remote toggle
            if remote_only and not job["remote"]:
                continue
                
            # Check location alignment
            if loc_str and loc_str not in job["location"].lower():
                continue
                
            filtered.append(job)
            
        # If filters are too restrictive, yield all mock jobs that match query
        if not filtered and query_words:
            for job in MOCK_JOBS:
                text_to_match = f"{job['title']} {job['jd_text']}".lower()
                if any(w in text_to_match for w in query_words):
                    filtered.append(job)
                    
        return filtered if filtered else MOCK_JOBS

    async def search_and_rank_jobs(self, payload: JobSearchRequest) -> JobSearchResponse:
        """
        Coordinate concurrent job retrieval, deduplication, caching, rule-based matching, and ranking.
        """
        query_hash = hashlib.sha256(
            f"{payload.query}|{payload.location or ''}|{payload.remote_only}".encode('utf-8')
        ).hexdigest()
        
        # 1. Check cache
        cached_jobs = self._get_cached_results(query_hash)
        if cached_jobs:
            raw_jobs = cached_jobs
        else:
            # 2. Fetch live data concurrently
            tasks = [
                self._fetch_jsearch(payload.query, payload.location),
                self._fetch_jooble(payload.query, payload.location),
                self._fetch_remotive(payload.query),
                self._fetch_arbeitnow(payload.query)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            raw_jobs = []
            for r in results:
                if isinstance(r, list):
                    raw_jobs.extend(r)
                elif isinstance(r, Exception):
                    logger.error(f"Concurrent aggregator task failed: {r}")
                    
            # 3. Fallback to Mock Data if no results fetched (due to mock keys, rate limits, or network failures)
            if not raw_jobs:
                logger.warning("No results returned from aggregators. Falling back to local mock listings.")
                raw_jobs = self._get_mock_fallback_data(payload.query, payload.location, payload.remote_only)

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
            
            # Cache the raw aggregated list
            self._set_cached_results(query_hash, raw_jobs)

        # 4. Filter remote jobs if remote_only is enabled
        if payload.remote_only:
            raw_jobs = [j for j in raw_jobs if j.get("remote", False)]

        # 5. Store jobs in database and retrieve persistent UUID mappings
        uuid_mapping = self._store_jobs_in_db(raw_jobs)
        
        # 6. Retrieve User profile and applied status for personalized ranking
        profile = None
        applied_hashes = set()
        if payload.user_id:
            profile = self._fetch_profile(payload.user_id)
            applied_hashes = self._get_applied_hashes(payload.user_id)

        # 7. Match and Rank
        final_cards = []
        for j in raw_jobs:
            job_hash = j["job_hash"]
            score, explanation = calculate_match_score(
                j["title"],
                j["jd_text"],
                j.get("location"),
                j.get("remote", False),
                profile,
                payload.query
            )
            
            final_cards.append(JobCard(
                job_id=uuid_mapping.get(job_hash, str(uuid.uuid4())),
                source=j["source"],
                title=j["title"],
                company=j["company"],
                location=j.get("location"),
                remote=j.get("remote", False),
                apply_url=j.get("apply_url"),
                jd_text=j["jd_text"],
                fetched_at=datetime.datetime.now(datetime.timezone.utc),
                job_hash=job_hash,
                match_score=score,
                match_explanation=explanation,
                is_applied=job_hash in applied_hashes
            ))

        # Sort by Match Score descending
        final_cards.sort(key=lambda c: c.match_score or 0.0, reverse=True)
        
        # Apply slice limit
        final_cards = final_cards[:payload.limit]

        return JobSearchResponse(
            query_hash=query_hash,
            jobs=final_cards
        )
