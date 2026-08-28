import logging
import asyncio
import uuid
import os
import json
import time
from typing import Dict, Any
from app.config import settings
from app.services.browser_agent import run_auto_apply_agent
from app.database import get_db

logger = logging.getLogger(__name__)

# Try to initialize Celery
try:
    from celery import Celery
    redis_broker = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_app = Celery("antigravity_tasks", broker=redis_broker, backend=redis_broker)
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )
    redis_available = True
    logger.info("Celery task queue initialized successfully.")
except Exception as e:
    celery_app = None
    redis_available = False
    logger.warning(f"Celery initialization skipped (Redis/Celery package not running): {e}")

# In-memory task registry for tracking FastAPI background tasks
FASTAPI_TASK_REGISTRY = {}

def clean_registry():
    """Removes tasks older than 1 hour or enforces a max limit of 1000 tasks."""
    now = time.time()
    # 1. Evict expired
    expired_keys = [k for k, v in FASTAPI_TASK_REGISTRY.items() if v.get("_created_at", 0) < now - 3600]
    for k in expired_keys:
        del FASTAPI_TASK_REGISTRY[k]
    
    # 2. Enforce max limit of 1000 entries (LRU-ish eviction by timestamp)
    if len(FASTAPI_TASK_REGISTRY) > 1000:
        sorted_tasks = sorted(FASTAPI_TASK_REGISTRY.items(), key=lambda x: x[1].get("_created_at", 0))
        to_evict_count = len(FASTAPI_TASK_REGISTRY) - 1000
        for i in range(to_evict_count):
            del FASTAPI_TASK_REGISTRY[sorted_tasks[i][0]]

from app.utils import clean_uuid

TASK_QUEUE = asyncio.PriorityQueue()

async def update_task_db_status(task_id: str, status: str, result: dict = None, logs: list = None, error: str = None):
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    if logs:
                        await cur.execute(
                            """
                            UPDATE background_tasks
                            SET status = %s, result = %s, logs = logs || %s::text[], error = %s, updated_at = NOW()
                            WHERE id = %s;
                            """,
                            (status, json.dumps(result or {}), logs, error, clean_uuid(task_id))
                        )
                    else:
                        await cur.execute(
                            """
                            UPDATE background_tasks
                            SET status = %s, result = %s, error = %s, updated_at = NOW()
                            WHERE id = %s;
                            """,
                            (status, json.dumps(result or {}), error, clean_uuid(task_id))
                        )
                    await conn.commit()
    except Exception as e:
        logger.error(f"Failed to update task DB status: {e}")

async def add_persistent_task(user_id: str, task_type: str, payload: dict, priority: int = 0) -> str:
    """Creates a background task record in PostgreSQL and registers it in the local queue."""
    task_id = str(uuid.uuid4())
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO background_tasks (id, user_id, task_type, status, payload, priority, logs)
                        VALUES (%s, %s, %s, 'pending', %s, %s, %s);
                        """,
                        (task_id, clean_uuid(user_id), task_type, json.dumps(payload), priority, ["Task registered in persistent queue."])
                    )
                    await conn.commit()
    except Exception as e:
        logger.error(f"Failed to save background task to DB: {e}")
        
    await TASK_QUEUE.put((priority, task_id))
    return task_id

async def run_apply_pipeline(task_id: str, user_id: str, job_id: str, job_hash: str, apply_url: str, profile_dict: dict, answers: dict):
    """Execution wrapper to run Playwright auto-apply, saving results and broadcasting states."""
    logger.info(f"Starting auto-apply pipeline for task {task_id}")
    FASTAPI_TASK_REGISTRY[task_id] = {
        "status": "running",
        "user_id": user_id,
        "logs": ["Starting browser agent..."],
        "_created_at": time.time()
    }
    clean_registry()
    await update_task_db_status(task_id, "running", logs=["Starting browser agent..."])
    
    # Broadcast log helper
    async def log_event(message: str):
        logger.info(f"[{task_id}] {message}")
        if task_id in FASTAPI_TASK_REGISTRY:
            FASTAPI_TASK_REGISTRY[task_id]["logs"].append(message)
        await update_task_db_status(task_id, "running", logs=[message])
            
    try:
        from app.schemas import ResumeParsedData
        profile = ResumeParsedData.model_validate(profile_dict)
        
        target_url = apply_url or f"http://localhost:{settings.BACKEND_PORT}/mock-apply-form"
        await log_event(f"Navigating browser context to: {target_url}")
        
        from app.utils import get_platform_cookies
        platform = "linkedin" if "linkedin" in target_url else "indeed" if "indeed" in target_url else "glassdoor" if "glassdoor" in target_url else "jooble"
        cookies = await get_platform_cookies(user_id, platform)
        if cookies:
            await log_event(f"Injecting active session cookies ({len(cookies)} cookies) for {platform}...")
            
        agent_res = await run_auto_apply_agent(target_url, profile, answers, user_id=user_id, task_id=task_id)
        
        status_res = agent_res.get("status", "success")
        if status_res == "needs_action":
            action_req = agent_res.get("action_required", {})
            FASTAPI_TASK_REGISTRY[task_id] = {
                "status": "needs_action",
                "user_id": user_id,
                "action_required": action_req,
                "logs": FASTAPI_TASK_REGISTRY[task_id]["logs"] + [f"Task paused: {action_req.get('message')}"],
                "_created_at": FASTAPI_TASK_REGISTRY[task_id]["_created_at"]
            }
            await update_task_db_status(task_id, "needs_action", result={"action_required": action_req}, logs=[f"Task paused: {action_req.get('message')}"])
            logger.warning(f"Task {task_id} requires manual action.")
        else:
            # Save application to DB
            application_id = str(uuid.uuid4())
            db_saved = False
            try:
                async with get_db() as conn:
                    if conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                """
                                INSERT INTO applications (id, user_id, job_id, job_hash, status)
                                VALUES (%s, %s, %s, %s, 'ready_to_apply');
                                """,
                                (application_id, user_id, job_id, job_hash)
                            )
                            await cur.execute(
                                """
                                INSERT INTO application_events (application_id, event_type, from_status, to_status, actor, payload)
                                VALUES (%s, 'create', NULL, 'ready_to_apply', 'system', '{}');
                                """,
                                (clean_uuid(application_id),)
                            )
                            await conn.commit()
                            db_saved = True
            except Exception as db_err:
                logger.warning(f"Could not save application to DB, falling back: {db_err}")
                
            if not db_saved:
                # Save to local applications file fallback
                fallback_file = os.path.join(settings.DATA_DIR, "local_applications.json")
                apps_data = []
                if os.path.exists(fallback_file):
                    try:
                        with open(fallback_file, "r", encoding="utf-8") as f:
                            apps_data = json.load(f)
                    except Exception:
                        pass
                apps_data.append({
                    "id": application_id,
                    "user_id": user_id,
                    "job_id": job_id,
                    "job_hash": job_hash,
                    "status": "ready_to_apply"
                })
                with open(fallback_file, "w", encoding="utf-8") as f:
                    json.dump(apps_data, f)
            
            FASTAPI_TASK_REGISTRY[task_id] = {
                "status": "success",
                "user_id": user_id,
                "logs": FASTAPI_TASK_REGISTRY[task_id]["logs"] + ["Copilot preparation finished successfully!"],
                "_created_at": FASTAPI_TASK_REGISTRY[task_id]["_created_at"]
            }
            await update_task_db_status(task_id, "success", result={"application_id": application_id}, logs=["Copilot preparation finished successfully!"])
            logger.info("Copilot preparation finished successfully.")
            
    except Exception as e:
        logger.error(f"Error executing auto-apply task {task_id}: {e}")
        FASTAPI_TASK_REGISTRY[task_id] = {
            "status": "failed",
            "user_id": user_id,
            "error": str(e),
            "logs": FASTAPI_TASK_REGISTRY[task_id]["logs"] + [f"Task failed: {str(e)}"],
            "_created_at": FASTAPI_TASK_REGISTRY[task_id]["_created_at"]
        }
        await update_task_db_status(task_id, "failed", error=str(e), logs=[f"Task failed: {str(e)}"])

async def recover_pending_tasks():
    """Re-enqueue tasks stuck as 'pending' or 'running' in the DB after a server restart."""
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT id, priority FROM background_tasks WHERE status IN ('pending', 'running') ORDER BY priority DESC, created_at ASC;"
                    )
                    rows = await cur.fetchall()
                    if rows:
                        # Reset any 'running' tasks back to 'pending' since they were interrupted
                        await cur.execute(
                            "UPDATE background_tasks SET status = 'pending', updated_at = NOW() WHERE status = 'running';"
                        )
                        await conn.commit()
                        for task_id, priority in rows:
                            await TASK_QUEUE.put((priority or 0, str(task_id)))
                        logger.info(f"Recovered {len(rows)} pending tasks from database.")
                    else:
                        logger.info("No pending tasks to recover from database.")
    except Exception as e:
        logger.warning(f"Failed to recover pending tasks from DB: {e}")

async def start_task_worker():
    """Worker loop running background tasks from the priority queue."""
    logger.info("Starting background task worker...")
    await recover_pending_tasks()
    while True:
        try:
            priority, task_id = await TASK_QUEUE.get()
            logger.info(f"Worker picked up task {task_id} with priority {priority}")
            
            payload = None
            task_type = None
            user_id = None
            try:
                async with get_db() as conn:
                    if conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "SELECT task_type, payload, user_id FROM background_tasks WHERE id = %s;",
                                (clean_uuid(task_id),)
                            )
                            row = await cur.fetchone()
                            if row:
                                task_type, payload_str, user_id = row
                                payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
            except Exception as e:
                logger.error(f"Failed to fetch task from DB: {e}")
                TASK_QUEUE.task_done()
                continue
                
            if not payload or not task_type:
                TASK_QUEUE.task_done()
                continue
                
            await update_task_db_status(task_id, "running", logs=["Task picked up by worker."])
            
            try:
                if task_type == "auto_apply":
                    await run_apply_pipeline(
                        task_id, 
                        user_id, 
                        payload.get("job_id"), 
                        payload.get("job_hash"), 
                        payload.get("apply_url"), 
                        payload.get("profile_dict"), 
                        payload.get("answers")
                    )
                else:
                    await update_task_db_status(task_id, "success", logs=["Task finished (unknown type)."])
            except Exception as handler_err:
                logger.error(f"Task handler failed: {handler_err}")
                await update_task_db_status(task_id, "failed", error=str(handler_err))
                
            TASK_QUEUE.task_done()
        except Exception as queue_err:
            logger.error(f"Queue worker exception: {queue_err}")
            await asyncio.sleep(1)

if celery_app:
    @celery_app.task(bind=True)
    def celery_apply_task(self, user_id: str, job_id: str, job_hash: str, apply_url: str, profile_dict: dict, answers: dict):
        task_id = self.request.id or str(uuid.uuid4())
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                run_apply_pipeline(task_id, user_id, job_id, job_hash, apply_url, profile_dict, answers),
                loop
            )
        else:
            try:
                loop.run_until_complete(run_apply_pipeline(task_id, user_id, job_id, job_hash, apply_url, profile_dict, answers))
            finally:
                loop.close()

async def run_job_alerts_check() -> Dict[str, Any]:
    """Scans all saved search alerts in the DB, queries live matching jobs, and triggers emails."""
    logger.info("Starting automated job alert check...")
    results = []
    searches = []
    
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    # Query active saved searches with user emails
                    await cur.execute(
                        """
                        SELECT s.id, s.user_id, s.keywords, s.location, u.email 
                        FROM saved_searches s
                        JOIN users u ON s.user_id = u.id;
                        """
                    )
                    searches = await cur.fetchall()
    except Exception as e:
        logger.error(f"Database error during job alert scan: {e}")
        return {"status": "failed", "error": str(e)}

    from app.services.job_service import JobService
    from app.schemas import JobSearchRequest
    from app.services.email_service import send_html_email, compile_alert_template
    
    job_service = JobService()
    
    for alert_id, user_id, keywords, location, email in searches:
        try:
            logger.info(f"Checking matches for alert {alert_id} (user: {email}, query: '{keywords}')")
            payload = JobSearchRequest(
                query=keywords,
                location=location or "",
                user_id=str(user_id)
            )
            search_res = await job_service.search_and_rank_jobs(payload)
            matching_jobs = [c.model_dump() for c in search_res.jobs[:3]]
            if matching_jobs:
                # Retrieve user name from profile if available
                name = "Candidate"
                try:
                    async with get_db() as conn:
                        if conn:
                            async with conn.cursor() as cur:
                                await cur.execute("SELECT parsed_resume_json FROM profiles WHERE user_id = %s;", (user_id,))
                                row = await cur.fetchone()
                                if row and row[0]:
                                    name = row[0].get("name", "Candidate")
                except Exception:
                    pass
                
                # Send email
                html_body = compile_alert_template(name, keywords, matching_jobs)
                subject = f"Echo Apply — New matches found for '{keywords}'"
                send_html_email(email, subject, html_body)
                results.append({
                    "alert_id": str(alert_id),
                    "user_id": str(user_id),
                    "matches_found": len(matching_jobs)
                })
        except Exception as alert_err:
            logger.error(f"Error checking matching jobs for alert {alert_id}: {alert_err}")
            
    return {"status": "success", "processed_alerts": len(searches), "matches": results}


async def start_keep_alive_ping():
    """
    Sends a lightweight health check ping to the public backend URL every 9 minutes (540s)
    to prevent free-tier instances (e.g. Render) from spinning down due to inactivity.
    """
    # Render automatically sets RENDER_EXTERNAL_URL; fallback to BACKEND_URL
    backend_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("BACKEND_URL") or "https://echo-apply-backend.onrender.com"
    if not backend_url.startswith("http"):
        backend_url = f"https://{backend_url}"
    
    health_url = f"{backend_url.rstrip('/')}/api/health"
    logger.info(f"[KeepAlive] Keep-alive worker active targeting: {health_url}")
    
    # Wait 60s after initial server boot
    await asyncio.sleep(60)
    
    import httpx
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(health_url)
                logger.info(f"[KeepAlive] Heartbeat ping sent to {health_url} -> Status {res.status_code}")
        except Exception as e:
            logger.debug(f"[KeepAlive] Heartbeat ping non-critical notice: {e}")
            
        # Ping every 9 minutes (540s), well within Render's 15-minute window
        await asyncio.sleep(540)
