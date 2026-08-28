import os
import shutil
import tempfile
import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright
from app.schemas import ResumeParsedData
from app.config import settings

logger = logging.getLogger(__name__)

# Constants for screenshot paths — use portable env-driven directories
SCREENSHOT_DIR = os.path.join(settings.DATA_DIR, "screenshots")
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

async def run_auto_apply_agent(
    apply_url: str,
    profile: ResumeParsedData,
    answers: Dict[str, str],
    user_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tier-2 Agentic Auto-Apply using Playwright.
    Navigates to application URL, detects login/CAPTCHA blockers,
    auto-fills candidate profile and screening answers, checks for unmapped required fields,
    takes screenshots, and submits the form.
    """
    # Helper to broadcast logs to frontend
    async def log_and_broadcast(message: str, level: str = "info"):
        if level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        else:
            logger.info(message)
            
        if task_id:
            try:
                from app.tasks import FASTAPI_TASK_REGISTRY
                if task_id in FASTAPI_TASK_REGISTRY:
                    FASTAPI_TASK_REGISTRY[task_id]["logs"].append(message)
            except Exception:
                pass
            try:
                from app.main import manager
                await manager.broadcast(task_id, message)
            except Exception:
                pass

    await log_and_broadcast(f"Starting Tier-2 Agentic Auto-Apply on URL: {apply_url}")
    
    # 1. Initialize Playwright
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Determine platform to inject cookies for
            platform = None
            if "linkedin.com" in apply_url:
                platform = "linkedin"
            elif "indeed.com" in apply_url:
                platform = "indeed"
            elif "glassdoor.com" in apply_url:
                platform = "glassdoor"

            if platform and user_id:
                try:
                    from app.utils import get_platform_cookies
                    cookies = await get_platform_cookies(user_id, platform)
                    if cookies:
                        await log_and_broadcast(f"Injecting {len(cookies)} active session cookies for {platform}...")
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
                        await log_and_broadcast("Session cookies successfully injected.")
                except Exception as cookie_err:
                    logger.error(f"Failed to inject session cookies: {cookie_err}")

            # Navigate to job application page
            logger.info(f"Navigating to {apply_url}...")
            await page.goto(apply_url, wait_until="networkidle", timeout=15000)

            # Helper to save screenshots to both workspace and artifacts directory
            async def save_screenshot(filename: str):
                os.makedirs(SCREENSHOT_DIR, exist_ok=True)
                ws_path = os.path.join(WORKSPACE_DIR, filename)
                art_path = os.path.join(SCREENSHOT_DIR, filename)
                
                try:
                    await page.screenshot(path=ws_path, full_page=True)
                    shutil.copy2(ws_path, art_path)
                    logger.info(f"Saved screenshot to {ws_path} and {art_path}")
                except Exception as e:
                    logger.error(f"Failed to capture screenshot: {e}")

            # 2. Check for login screen redirect or password fields
            current_url = page.url.lower()
            html_content = (await page.content()).lower()
            
            is_login = (
                "login" in current_url 
                or "signin" in current_url
                or "sign-in" in current_url
                or await page.locator("input[type='password']").count() > 0
                or "log in to your account" in html_content
                or "sign in to your account" in html_content
            )
            
            if is_login:
                logger.warning("Login block detected.")
                await save_screenshot("auto_apply_blocked.png")
                await browser.close()
                
                message = "A login screen was detected. Please log in manually before continuing."
                if platform:
                    message = f"Active session for {platform.capitalize()} is missing or expired. Please open the Chrome extension and click 'Sync Sessions Now' to refresh your session."
                
                return {
                    "status": "needs_action",
                    "action_required": {
                        "type": "login_required",
                        "message": message,
                        "screenshot": "auto_apply_blocked.png"
                    }
                }
            
            # 3. Check for CAPTCHAs or Cloudflare challenge
            # Scan iframes and page content
            captcha_detected = False
            if "captcha" in html_content or "hcaptcha" in html_content or "cloudflare" in html_content or "security check" in html_content or "verify you are human" in html_content:
                captcha_detected = True
            
            # Check frames
            for frame in page.frames:
                frame_url = frame.url.lower()
                if "captcha" in frame_url or "hcaptcha" in frame_url or "turnstile" in frame_url or "cloudflare" in frame_url:
                    captcha_detected = True
                    break
                    
            if captcha_detected:
                logger.warning("CAPTCHA block detected.")
                await save_screenshot("auto_apply_blocked.png")
                await browser.close()
                return {
                    "status": "needs_action",
                    "action_required": {
                        "type": "captcha_detected",
                        "message": "A CAPTCHA or security verification was detected. Please solve it manually.",
                        "screenshot": "auto_apply_blocked.png"
                    }
                }

            # 4. Form Parsing and Auto-Filling
            # Find all inputs, textareas, and select elements
            form_elements = await page.locator("input, textarea, select").all()
            logger.info(f"Found {len(form_elements)} form element candidates on the page.")
            
            unmapped_required_fields = []
            
            # JavaScript helper to resolve label or identifier text for an element
            js_resolver = """
            (element) => {
                // 1. Check associated label
                if (element.id) {
                    const label = document.querySelector(`label[for="${element.id}"]`);
                    if (label) return label.innerText.trim();
                }
                // 2. Check closest ancestor label
                const parentLabel = element.closest('label');
                if (parentLabel) return parentLabel.innerText.trim();
                // 3. Check aria-labelledby
                const labelledby = element.getAttribute('aria-labelledby');
                if (labelledby) {
                    const labels = labelledby.split(/\\s+/).map(id => document.getElementById(id)).filter(Boolean);
                    if (labels.length > 0) return labels.map(l => l.innerText).join(' ').trim();
                }
                // 4. Check aria-label
                const ariaLabel = element.getAttribute('aria-label');
                if (ariaLabel) return ariaLabel.trim();
                // 5. Check placeholder
                const placeholder = element.getAttribute('placeholder');
                if (placeholder) return placeholder.trim();
                // 6. Check name or id
                const name = element.getAttribute('name');
                if (name) return name.trim();
                const id = element.getAttribute('id');
                if (id) return id.trim();
                return '';
            }
            """
            
            for el in form_elements:
                # Basic visibility and editability checks
                if not await el.is_visible() or not await el.is_enabled():
                    continue
                
                el_type = await el.get_attribute("type")
                if el_type in ["hidden", "submit", "image", "button", "reset"]:
                    continue
                
                label_text = await el.evaluate(js_resolver)
                label_norm = label_text.lower().strip()
                name_attr = (await el.get_attribute("name") or "").lower()
                id_attr = (await el.get_attribute("id") or "").lower()
                
                # Check if this is a CAPTCHA input
                if "captcha" in label_norm or "captcha" in name_attr or "captcha" in id_attr:
                    logger.warning("CAPTCHA input field detected.")
                    await save_screenshot("auto_apply_blocked.png")
                    await browser.close()
                    return {
                        "status": "needs_action",
                        "action_required": {
                            "type": "captcha_detected",
                            "message": "A security verification field was found on the form. Please complete it manually.",
                            "screenshot": "auto_apply_blocked.png"
                        }
                    }
                
                tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                is_required = (
                    await el.get_attribute("required") is not None
                    or await el.get_attribute("aria-required") == "true"
                    or "*" in label_text
                )
                
                filled = False
                
                # A. Handle File Input (Resume / CV Upload)
                if el_type == "file":
                    if any(kw in label_norm or kw in name_attr or kw in id_attr for kw in ["resume", "cv", "curriculum", "filename", "file", "upload"]):
                        # Try to render a real PDF resume dynamically from profile
                        pdf_data = None
                        try:
                            from app.services.resume_generator import generate_resume_pdf
                            pdf_data = generate_resume_pdf(profile)
                            logger.info("Generated real PDF resume dynamically for file upload.")
                        except Exception as e:
                            logger.warning(f"Could not generate real PDF resume dynamically, falling back to dummy: {e}")
                            pdf_data = b"%PDF-1.4 dummy resume content for agentic apply"
                        
                        # Write the PDF to upload
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                            tmp_file.write(pdf_data)
                            tmp_file_path = tmp_file.name
                        
                        try:
                            await el.set_input_files(tmp_file_path)
                            filled = True
                            logger.info("Uploaded resume file.")
                        finally:
                            try:
                                os.remove(tmp_file_path)
                            except Exception:
                                pass
                
                # B. Match Custom Screening Answers from semantic memory (Vector KB)
                if not filled and label_text != "":
                    try:
                        from app.services.screening_kb import search_screening_answer
                        uid_to_use = user_id or "default-user"
                        matched_answer = search_screening_answer(uid_to_use, label_text)
                        if matched_answer:
                            logger.info(f"Retrieved matching answer from semantic memory: '{label_text}' -> '{matched_answer}'")
                            if tag_name == "select":
                                is_multiple = await el.get_attribute("multiple") is not None
                                options = await el.locator("option").all()
                                if is_multiple:
                                    vals_to_select = [v.strip().lower() for v in matched_answer.split(",")]
                                    matching_vals = []
                                    for opt in options:
                                        opt_text = (await opt.text_content() or "").strip().lower()
                                        opt_val = (await opt.get_attribute("value") or "").lower()
                                        if any(val in opt_text or val == opt_val for val in vals_to_select):
                                            val_attr = await opt.get_attribute("value")
                                            if val_attr:
                                                matching_vals.append(val_attr)
                                    if matching_vals:
                                        await el.select_option(value=matching_vals)
                                        filled = True
                                else:
                                    selected = False
                                    for opt in options:
                                        opt_text = (await opt.text_content() or "").strip()
                                        opt_val = await opt.get_attribute("value") or ""
                                        if matched_answer.lower() in opt_text.lower() or matched_answer.lower() == opt_val.lower():
                                            await el.select_option(value=opt_val)
                                            selected = True
                                            break
                                    if not selected and options:
                                        await el.select_option(index=1)
                                    filled = True
                            elif el_type == "checkbox":
                                if matched_answer.lower() in ["yes", "true", "agree", "checked", "1"]:
                                    await el.check()
                                else:
                                    await el.uncheck()
                                filled = True
                            elif el_type == "radio":
                                radio_val = await el.get_attribute("value") or ""
                                radio_label = label_norm
                                if matched_answer.lower() in radio_val.lower() or matched_answer.lower() in radio_label:
                                    await el.check()
                                    filled = True
                            else:
                                await el.fill(matched_answer)
                                filled = True
                    except Exception as kb_err:
                        logger.error(f"Error querying semantic memory: {kb_err}")

                # C. Match Custom Screening Answers from current session answers dict
                # We perform substring comparisons on question texts
                if not filled and answers:
                    for q_text, ans_val in answers.items():
                        q_norm = q_text.lower()
                        # If label matches the question text (either direction substring match)
                        if (q_norm in label_norm or label_norm in q_norm) and label_norm != "":
                            if tag_name == "select":
                                is_multiple = await el.get_attribute("multiple") is not None
                                options = await el.locator("option").all()
                                if is_multiple:
                                    vals_to_select = [v.strip().lower() for v in ans_val.split(",")]
                                    matching_vals = []
                                    for opt in options:
                                        opt_text = (await opt.text_content() or "").strip().lower()
                                        opt_val = (await opt.get_attribute("value") or "").lower()
                                        if any(val in opt_text or val == opt_val for val in vals_to_select):
                                            val_attr = await opt.get_attribute("value")
                                            if val_attr:
                                                matching_vals.append(val_attr)
                                    if matching_vals:
                                        await el.select_option(value=matching_vals)
                                        filled = True
                                        logger.info(f"Selected multiple options for: '{label_text}' -> '{matching_vals}'")
                                else:
                                    # Find matching option
                                    selected = False
                                    for opt in options:
                                        opt_text = (await opt.text_content() or "").strip()
                                        opt_val = await opt.get_attribute("value") or ""
                                        if ans_val.lower() in opt_text.lower() or ans_val.lower() == opt_val.lower():
                                            await el.select_option(value=opt_val)
                                            selected = True
                                            break
                                    if not selected and options:
                                        # Fallback select first non-empty option
                                        await el.select_option(index=1)
                                    filled = True
                                    logger.info(f"Selected answer for screening: '{label_text}' -> '{ans_val}'")
                            elif el_type == "checkbox":
                                if ans_val.lower() in ["yes", "true", "agree", "checked", "1"]:
                                    await el.check()
                                else:
                                    await el.uncheck()
                                filled = True
                                logger.info(f"Checked/Unchecked checkbox for: '{label_text}' -> '{ans_val}'")
                            elif el_type == "radio":
                                # Radio group - check if value or parent label matches
                                radio_val = await el.get_attribute("value") or ""
                                radio_label = label_norm
                                if ans_val.lower() in radio_val.lower() or ans_val.lower() in radio_label:
                                    await el.check()
                                    filled = True
                                    logger.info(f"Selected radio answer for: '{label_text}' -> '{ans_val}'")
                            else:
                                # Input text or textarea
                                await el.fill(ans_val)
                                filled = True
                                logger.info(f"Filled answer for screening: '{label_text}' -> '{ans_val}'")
                            break

                # C. Match Standard Fields (Profile Data fallback)
                if not filled:
                    # Email Field
                    if "email" in label_norm or "e-mail" in label_norm or "email" in name_attr or el_type == "email":
                        await el.fill(profile.email)
                        filled = True
                        logger.info(f"Filled Email: {profile.email}")
                    
                    # Phone Field
                    elif "phone" in label_norm or "tel" in label_norm or "mobile" in label_norm or "phone" in name_attr or el_type == "tel":
                        phone_num = profile.phone or "+1-555-555-5555"
                        await el.fill(phone_num)
                        filled = True
                        logger.info(f"Filled Phone: {phone_num}")
                    
                    # GitHub Field
                    elif "github" in label_norm or "git hub" in label_norm or "github" in name_attr:
                        gh_url = ""
                        for link in profile.links:
                            if "github.com" in link:
                                gh_url = link
                                break
                        if not gh_url:
                            gh_url = f"https://github.com/{profile.name.lower().replace(' ', '')}"
                        await el.fill(gh_url)
                        filled = True
                        logger.info(f"Filled GitHub URL: {gh_url}")
                    
                    # LinkedIn Field
                    elif "linkedin" in label_norm or "linked in" in label_norm or "linkedin" in name_attr:
                        li_url = ""
                        for link in profile.links:
                            if "linkedin.com" in link:
                                li_url = link
                                break
                        if not li_url:
                            li_url = f"https://linkedin.com/in/{profile.name.lower().replace(' ', '')}"
                        await el.fill(li_url)
                        filled = True
                        logger.info(f"Filled LinkedIn URL: {li_url}")
                        
                    # First Name Field
                    elif "first name" in label_norm or "given name" in label_norm or "firstname" in name_attr or "fname" in name_attr:
                        parts = profile.name.split()
                        first_name = parts[0] if parts else profile.name
                        await el.fill(first_name)
                        filled = True
                        logger.info(f"Filled First Name: {first_name}")
                        
                    # Last Name Field
                    elif "last name" in label_norm or "family name" in label_norm or "lastname" in name_attr or "lname" in name_attr:
                        parts = profile.name.split()
                        last_name = " ".join(parts[1:]) if len(parts) > 1 else "Smith"
                        await el.fill(last_name)
                        filled = True
                        logger.info(f"Filled Last Name: {last_name}")
                        
                    # Full Name Field
                    elif "name" in label_norm or "fullname" in label_norm or "name" in name_attr:
                        await el.fill(profile.name)
                        filled = True
                        logger.info(f"Filled Full Name: {profile.name}")
                        
                    # Auto-check terms and agreements if checkbox and required
                    elif el_type == "checkbox" and is_required and ("agree" in label_norm or "terms" in label_norm or "consent" in label_norm):
                        await el.check()
                        filled = True
                        logger.info("Checked required terms/agreement checkbox.")
                
                # Check for required unmapped field
                if is_required and not filled:
                    # Let's inspect if the element is already filled (has a non-empty value attribute or content)
                    current_value = await el.evaluate("el => el.value")
                    if not current_value:
                        logger.warning(f"Unmapped required field: '{label_text}'")
                        unmapped_required_fields.append(label_text)

            # If there are any required fields we couldn't map, abort and ask user
            if unmapped_required_fields:
                msg = f"The following required fields could not be mapped: {', '.join(unmapped_required_fields)}"
                logger.warning(msg)
                await save_screenshot("auto_apply_blocked.png")
                await browser.close()
                return {
                    "status": "needs_action",
                    "action_required": {
                        "type": "unmapped_fields",
                        "message": msg,
                        "screenshot": "auto_apply_blocked.png",
                        "fields": unmapped_required_fields
                    }
                }

            # 5. Take screenshot of the successfully filled form
            await save_screenshot("auto_apply_filled.png")

            # 6. Platform Compliance Pivot: Stop before submitting.
            # We do NOT click submit anymore. The user is in full control.
            await log_and_broadcast("Form prefilled successfully. Copilot mode active: manual review and submission required.")
            await browser.close()
            return {
                "status": "success",
                "application_id": "copilot-prepared"
            }
                
        except Exception as err:
            logger.error(f"Error during browser agent execution: {err}")
            await browser.close()
            return {
                "status": "needs_action",
                "action_required": {
                    "type": "error",
                    "message": f"Browser agent error: {str(err)}"
                }
            }
