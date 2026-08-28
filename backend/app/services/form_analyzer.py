import logging
from typing import Dict, Any, List
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class FormAnalyzer:
    """
    Compliance-friendly service that analyzes job application pages.
    Extracts fields and labels without filling or submitting anything.
    """
    async def analyze_apply_page(self, apply_url: str) -> Dict[str, Any]:
        logger.info(f"FormAnalyzer: Navigating to {apply_url} for analysis...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(apply_url, wait_until="networkidle", timeout=15000)
                
                # JavaScript helper to resolve label or identifier text for an element
                js_resolver = """
                (element) => {
                    if (element.id) {
                        const label = document.querySelector(`label[for="${element.id}"]`);
                        if (label) return label.innerText.trim();
                    }
                    const parentLabel = element.closest('label');
                    if (parentLabel) return parentLabel.innerText.trim();
                    const labelledby = element.getAttribute('aria-labelledby');
                    if (labelledby) {
                        const labels = labelledby.split(/\\s+/).map(id => document.getElementById(id)).filter(Boolean);
                        if (labels.length > 0) return labels.map(l => l.innerText).join(' ').trim();
                    }
                    const ariaLabel = element.getAttribute('aria-label');
                    if (ariaLabel) return ariaLabel.trim();
                    const placeholder = element.getAttribute('placeholder');
                    if (placeholder) return placeholder.trim();
                    const name = element.getAttribute('name');
                    if (name) return name.trim();
                    const id = element.getAttribute('id');
                    if (id) return id.trim();
                    return '';
                }
                """
                
                form_elements = await page.locator("input, textarea, select").all()
                extracted_fields = []
                
                for el in form_elements:
                    if not await el.is_visible() or not await el.is_enabled():
                        continue
                    
                    el_type = await el.get_attribute("type")
                    if el_type in ["hidden", "submit", "image", "button", "reset"]:
                        continue
                    
                    label_text = await el.evaluate(js_resolver)
                    is_required = (
                        await el.get_attribute("required") is not None
                        or await el.get_attribute("aria-required") == "true"
                        or "*" in label_text
                    )
                    
                    extracted_fields.append({
                        "label": label_text,
                        "type": el_type or "text",
                        "tag": await el.evaluate("el => el.tagName.toLowerCase()"),
                        "required": is_required
                    })
                
                await browser.close()
                return {
                    "status": "success",
                    "fields": extracted_fields
                }
            except Exception as e:
                logger.error(f"FormAnalyzer failed to analyze page: {e}")
                await browser.close()
                return {
                    "status": "error",
                    "message": str(e)
                }
