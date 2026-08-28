import os
import json
import logging
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.limiter import limiter
from app.auth import get_current_user, AuthenticatedUser
from app.sanitize import sanitize_user_id
from app.utils import clean_uuid, encrypt_value, decrypt_value
from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth_sync"])

class ExtensionCookie(BaseModel):
    platform: str
    name: str
    value: str
    domain: str
    path: str
    secure: bool
    httpOnly: bool
    expirationDate: Optional[float] = None

class ExtensionSyncRequest(BaseModel):
    user_id: str
    cookies: List[ExtensionCookie]

class OpenLoginWindowRequest(BaseModel):
    user_id: str
    platform: str

@router.post("/api/auth/extension-sync")
@limiter.limit("10/minute")
async def extension_sync(
    request: Request,
    payload: ExtensionSyncRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Securely receive, encrypt, and store job board session cookies."""
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format")
    if clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access/modify this resource"
        )
    payload.user_id = sanitized_id
    logger.info(f"Received cookie sync request for user: {payload.user_id}")
    
    # Group cookies by platform
    by_platform = {}
    for cookie in payload.cookies:
        if cookie.platform not in by_platform:
            by_platform[cookie.platform] = []
        by_platform[cookie.platform].append(cookie.model_dump())
        
    for platform, cookies in by_platform.items():
        # Encrypt the serialized cookies list
        plain_str = json.dumps(cookies)
        encrypted_str = encrypt_value(plain_str)
        
        # Save to database
        db_saved = False
        try:
            async with get_db() as conn:
                if conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            INSERT INTO platform_credentials (user_id, platform, cookies_encrypted, updated_at)
                            VALUES (%s, %s, %s, NOW())
                            ON CONFLICT (user_id, platform) DO UPDATE 
                            SET cookies_encrypted = EXCLUDED.cookies_encrypted, updated_at = NOW();
                            """,
                            (clean_uuid(payload.user_id), platform, encrypted_str)
                        )
                        await conn.commit()
                        db_saved = True
                        logger.info(f"Saved encrypted cookies for {platform} to DB.")
        except Exception as e:
            logger.warning(f"DB save failed, falling back to local storage: {e}")
            
        if not db_saved:
            # Local file fallback
            fallback_dir = os.path.join(settings.DATA_DIR, "credentials")
            os.makedirs(fallback_dir, exist_ok=True)
            file_path = os.path.join(fallback_dir, f"{clean_uuid(payload.user_id)}_{platform}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"encrypted_cookies": encrypted_str}, f)
            logger.info(f"Saved encrypted cookies for {platform} to local fallback file.")
            
    return {"status": "success", "message": "Synced active sessions successfully!"}

@router.get("/api/auth/sync-status")
@limiter.limit("30/minute")
async def get_sync_status(request: Request, user_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    sanitized_id = sanitize_user_id(user_id)
    if not sanitized_id or clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    uid = clean_uuid(sanitized_id)
    status_dict = {"linkedin": False, "indeed": False, "glassdoor": False}
    
    try:
        async with get_db() as conn:
            if conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT platform FROM platform_credentials WHERE user_id = %s;",
                        (uid,)
                    )
                    rows = await cur.fetchall()
                    for row in rows:
                        platform = row[0]
                        if platform in status_dict:
                            status_dict[platform] = True
    except Exception as e:
        logger.warning(f"Failed to fetch sync status from DB: {e}")
        
    for platform in status_dict:
        if not status_dict[platform]:
            file_path = os.path.join(settings.DATA_DIR, "credentials", f"{uid}_{platform}.json")
            if os.path.exists(file_path):
                status_dict[platform] = True
                
    return status_dict

@router.post("/api/auth/open-login-window")
@limiter.limit("5/minute")
async def open_login_window(request: Request, payload: OpenLoginWindowRequest, user: AuthenticatedUser = Depends(get_current_user)):
    sanitized_id = sanitize_user_id(payload.user_id)
    if not sanitized_id or clean_uuid(user.user_id) != clean_uuid(sanitized_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        
    platform = payload.platform.lower().strip()
    if platform not in ["linkedin", "indeed", "glassdoor"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported platform")
        
    # Pre-check: verify Playwright is importable
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright is not installed. Run: pip install playwright && playwright install chromium")
        return {
            "status": "error",
            "message": "Playwright is not installed. Run these commands in the backend directory:\n1. pip install playwright\n2. playwright install chromium"
        }
    
    logger.info(f"Opening secure browser login window for {platform}...")
    
    url_map = {
        "linkedin": "https://www.linkedin.com/login",
        "indeed": "https://secure.indeed.com/account/login",
        "glassdoor": "https://www.glassdoor.com/index.htm"
    }
    
    target_url = url_map.get(platform)
    user_id_clean = clean_uuid(sanitized_id)

    def _run_playwright_login():
        """
        Run Playwright in a synchronous background thread.
        This bypasses the Windows ProactorEventLoop limitation where
        asyncio.create_subprocess_exec() raises NotImplementedError.
        Using sync_playwright() avoids the async event loop conflict entirely.
        """
        import time
        from playwright.sync_api import sync_playwright
        
        browser = None
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(
                        headless=False,
                        args=["--start-maximized"]
                    )
                except Exception as launch_err:
                    err_msg = str(launch_err)
                    if "Executable doesn't exist" in err_msg or "browserType.launch" in err_msg:
                        return {
                            "status": "error",
                            "message": "Chromium browser is not installed for Playwright. Run this command:\nplaywright install chromium"
                        }
                    raise
                
                context = browser.new_context(
                    viewport=None,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                page.goto(target_url)
                
                logged_in = False
                captured_cookies = []
                
                # Poll cookies to detect successful login (up to 180 seconds)
                for _ in range(180):
                    time.sleep(1)
                    
                    # Check if browser was manually closed by the user
                    try:
                        if len(browser.contexts) == 0 or page.is_closed():
                            break
                    except Exception:
                        break
                        
                    cookies = context.cookies()
                    
                    # Platform-specific session detection
                    if platform == "linkedin":
                        li_at = next((c for c in cookies if c["name"] == "li_at"), None)
                        if li_at:
                            logged_in = True
                            captured_cookies = cookies
                            break
                    elif platform == "indeed":
                        ctk = next((c for c in cookies if c["name"] == "CTK"), None)
                        if ctk and "login" not in page.url.lower():
                            logged_in = True
                            captured_cookies = cookies
                            break
                    elif platform == "glassdoor":
                        gd_token = next((c for c in cookies if c["name"] == "gdToken" or c["name"] == "asid"), None)
                        if gd_token and "login" not in page.url.lower():
                            logged_in = True
                            captured_cookies = cookies
                            break
                
                if logged_in and captured_cookies:
                    formatted_cookies = []
                    for c in captured_cookies:
                        formatted_cookies.append({
                            "platform": platform,
                            "name": c["name"],
                            "value": c["value"],
                            "domain": c["domain"],
                            "path": c.get("path", "/"),
                            "secure": c.get("secure", True),
                            "httpOnly": c.get("httpOnly", False),
                            "expirationDate": c.get("expires")
                        })
                    
                    try:
                        browser.close()
                    except Exception:
                        pass
                    return {"status": "success", "cookies": formatted_cookies}
                else:
                    try:
                        browser.close()
                    except Exception:
                        pass
                    return {"status": "cancelled", "message": "Authentication window closed or timed out."}
                    
        except Exception as e:
            logger.error(f"Playwright login thread error: {e}")
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            err_msg = str(e)
            if "Executable doesn't exist" in err_msg or "not found" in err_msg.lower():
                return {"status": "error", "message": "Chromium browser not installed. Run: playwright install chromium"}
            return {"status": "error", "message": f"Browser login failed: {err_msg}"}

    try:
        # Run synchronous Playwright in a background thread to avoid
        # Windows ProactorEventLoop NotImplementedError
        result = await asyncio.to_thread(_run_playwright_login)
        
        if result.get("status") == "success" and result.get("cookies"):
            # Save cookies to DB or fallback
            plain_str = json.dumps(result["cookies"])
            encrypted_str = encrypt_value(plain_str)
            
            db_saved = False
            try:
                async with get_db() as conn:
                    if conn:
                        async with conn.cursor() as cur:
                            # Ensure user exists first (FK constraint fix)
                            await cur.execute(
                                """
                                INSERT INTO users (id, email, created_at)
                                VALUES (%s, %s, NOW())
                                ON CONFLICT (id) DO NOTHING;
                                """,
                                (user_id_clean, user.email or "unknown@user")
                            )
                            await cur.execute(
                                """
                                INSERT INTO platform_credentials (user_id, platform, cookies_encrypted, updated_at)
                                VALUES (%s, %s, %s, NOW())
                                ON CONFLICT (user_id, platform) DO UPDATE 
                                SET cookies_encrypted = EXCLUDED.cookies_encrypted, updated_at = NOW();
                                """,
                                (user_id_clean, platform, encrypted_str)
                            )
                            await conn.commit()
                            db_saved = True
            except Exception as db_err:
                logger.error(f"Failed to save cookies to DB: {db_err}")
                
            if not db_saved:
                fallback_dir = os.path.join(settings.DATA_DIR, "credentials")
                os.makedirs(fallback_dir, exist_ok=True)
                file_path = os.path.join(fallback_dir, f"{user_id_clean}_{platform}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({"encrypted_cookies": encrypted_str}, f)
            
            return {"status": "success", "message": f"Successfully authenticated and synced {platform} cookies!"}
        else:
            return result
            
    except Exception as e:
        logger.error(f"Error in open_login_window handler: {e}")
        return {"status": "error", "message": f"Browser login failed: {str(e)}"}

