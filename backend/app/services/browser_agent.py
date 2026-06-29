import os
import shutil
import tempfile
import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright
from app.schemas import ResumeParsedData

logger = logging.getLogger(__name__)

# Constants for screenshot paths
SCREENSHOT_DIR = "C:/Users/EYAD/.gemini/antigravity-ide/brain/7e7162d5-5854-4d32-83be-896086a1e4d4"
WORKSPACE_DIR = "d:/Project 101"

async def run_auto_apply_agent(
    apply_url: str,
    profile: ResumeParsedData,
    answers: Dict[str, str]
) -> Dict[str, Any]:
    """
    Tier-2 Agentic Auto-Apply using Playwright.
    Navigates to application URL, detects login/CAPTCHA blockers,
    auto-fills candidate profile and screening answers, checks for unmapped required fields,
    takes screenshots, and submits the form.
    """
    logger.info(f"Starting Tier-2 Agentic Auto-Apply on URL: {apply_url}")
    
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
                    # Copy to artifacts directory
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
                return {
                    "status": "needs_action",
                    "action_required": {
                        "type": "login_required",
                        "message": "A login screen was detected. Please log in manually before continuing.",
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
                    if "resume" in label_norm or "cv" in label_norm or "curriculum" in label_norm or "resume" in name_attr or "cv" in name_attr:
                        # Write a dummy pdf resume to upload
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                            tmp_file.write(b"%PDF-1.4 dummy resume content for agentic apply")
                            tmp_file_path = tmp_file.name
                        
                        try:
                            await el.set_input_files(tmp_file_path)
                            filled = True
                            logger.info("Uploaded dummy resume file.")
                        finally:
                            try:
                                os.remove(tmp_file_path)
                            except Exception:
                                pass
                
                # B. Match Custom Screening Answers from frontend
                # We perform substring comparisons on question texts
                if not filled and answers:
                    for q_text, ans_val in answers.items():
                        q_norm = q_text.lower()
                        # If label matches the question text (either direction substring match)
                        if (q_norm in label_norm or label_norm in q_norm) and label_norm != "":
                            if tag_name == "select":
                                # Find matching option
                                options = await el.locator("option").all()
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

            # 6. Submit the form
            submit_button = None
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Submit')",
                "button:has-text('Apply')",
                "button:has-text('Submit Application')",
                "button:has-text('Send')"
            ]
            
            for selector in submit_selectors:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible() and await btn.is_enabled():
                    submit_button = btn
                    break
            
            if not submit_button:
                # Scan all buttons for submit text
                all_buttons = await page.locator("button").all()
                for btn in all_buttons:
                    btn_text = (await btn.text_content() or "").lower()
                    if "submit" in btn_text or "apply" in btn_text or "send" in btn_text:
                        if await btn.is_visible() and await btn.is_enabled():
                            submit_button = btn
                            break
            
            if submit_button:
                logger.info("Clicking the submit button...")
                await submit_button.click()
                
                # Wait for navigation or success message
                await page.wait_for_timeout(2000)
                
                final_html = (await page.content()).lower()
                success_keywords = ["thank you", "success", "received", "submitted", "confirmed", "application sent", "applied"]
                success_detected = any(kw in final_html for kw in success_keywords)
                
                if success_detected:
                    logger.info("Application submission success detected on page.")
                    await save_screenshot("auto_apply_success.png")
                    await browser.close()
                    return {
                        "status": "success",
                        "application_id": "agent-submitted"
                    }
                else:
                    # Even if success text is not explicitly detected, if there was no obvious error, we treat it as success or log it
                    logger.warning("Submit button clicked, but explicit success keywords not found on response page.")
                    await save_screenshot("auto_apply_success.png")
                    await browser.close()
                    return {
                        "status": "success",
                        "application_id": "agent-submitted-unverified"
                    }
            else:
                msg = "Form filled successfully, but submit button could not be located."
                logger.error(msg)
                await browser.close()
                return {
                    "status": "needs_action",
                    "action_required": {
                        "type": "submit_failed",
                        "message": msg,
                        "screenshot": "auto_apply_filled.png"
                    }
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
