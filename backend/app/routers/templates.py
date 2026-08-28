import logging
from fastapi import APIRouter, Request, Response, HTTPException
from app.limiter import limiter
from app.schemas import ResumeParsedData
from app.services.resume_templates import render_template, AVAILABLE_TEMPLATES

logger = logging.getLogger(__name__)

router = APIRouter(tags=["templates"])

@router.get("/api/templates")
async def list_templates():
    """List all available resume templates."""
    return {
        "templates": [
            {"id": "classic", "name": "Classic", "description": "Traditional serif, clean lines"},
            {"id": "modern", "name": "Modern", "description": "Sans-serif with indigo accent sidebar"},
            {"id": "minimal", "name": "Minimal", "description": "Whitespace-heavy, ultra-clean"},
            {"id": "creative", "name": "Creative", "description": "Bold gradient header, colorful"},
            {"id": "executive", "name": "Executive", "description": "Two-column, formal layout"},
            {"id": "classic_executive", "name": "Classic Executive", "description": "Traditional serif executive style, single column, maximum ATS compatibility"},
            {"id": "modern_executive", "name": "Modern Executive", "description": "High-impact visual layout with large metrics boxes, optimized for direct outreach"},
        ]
    }

@router.post("/api/resume/download-template")
@limiter.limit("20/minute")
async def download_template_pdf(request: Request):
    """Download resume as PDF using a specific template."""
    body = await request.json()
    template_name = body.get("template", "classic")
    resume_data = body.get("parsed_resume")
    
    if not resume_data:
        raise HTTPException(status_code=400, detail="parsed_resume is required")
    if template_name not in AVAILABLE_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown template: {template_name}. Available: {AVAILABLE_TEMPLATES}")
    
    parsed = ResumeParsedData(**resume_data)
    html_content = render_template(template_name, parsed)
    
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
    except Exception as e:
        logger.warning(f"WeasyPrint failed, using fallback: {e}")
        from app.services.resume_generator import generate_fallback_pdf
        pdf_bytes = generate_fallback_pdf(parsed, template_name)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=resume_{template_name}.pdf"}
    )

@router.post("/api/resume/generate-styled")
@limiter.limit("10/minute")
async def generate_styled_resume(request: Request):
    """
    AI-powered resume generation: rewrites resume content optimized for the
    selected template style, then renders to PDF.
    """
    body = await request.json()
    template_name = body.get("template", "modern")
    resume_data = body.get("parsed_resume")
    job_description = body.get("job_description")
    
    if not resume_data:
        raise HTTPException(status_code=400, detail="parsed_resume is required")
    if template_name not in AVAILABLE_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown template: {template_name}. Available: {AVAILABLE_TEMPLATES}")
    
    parsed = ResumeParsedData(**resume_data)
    
    # Step 1: AI rewrite for the selected style with psychological hooks & XYZ impact
    try:
        from app.services.resume_rewriter import rewrite_resume_for_style
        optimized = rewrite_resume_for_style(parsed, template_name, job_description)
    except Exception as e:
        logger.warning(f"AI rewrite failed, using original: {e}")
        optimized = parsed
    
    # Step 2: Render strict 1-page A4 PDF using multi-pass compiler
    from app.services.resume_generator import generate_resume_pdf
    pdf_bytes = generate_resume_pdf(optimized, template_name, compact_mode=False)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=resume_ai_{template_name}.pdf"}
    )


@router.post("/api/resume/generate-styled-html")
@limiter.limit("20/minute")
async def generate_styled_resume_html(request: Request):
    """
    AI-powered resume generation returning standalone, browser-printable HTML.
    Includes psychological hooks, ATS keywords, and an interactive print toolbar.
    """
    body = await request.json()
    template_name = body.get("template", "modern")
    resume_data = body.get("parsed_resume")
    job_description = body.get("job_description")
    
    if not resume_data:
        raise HTTPException(status_code=400, detail="parsed_resume is required")
    if template_name not in AVAILABLE_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown template: {template_name}. Available: {AVAILABLE_TEMPLATES}")
    
    parsed = ResumeParsedData(**resume_data)
    
    try:
        from app.services.resume_rewriter import rewrite_resume_for_style
        optimized = rewrite_resume_for_style(parsed, template_name, job_description)
    except Exception as e:
        logger.warning(f"AI rewrite failed, using original: {e}")
        optimized = parsed
        
    html_content = render_template(template_name, optimized, compact_mode=True)
    
    return {
        "template": template_name,
        "html": html_content,
        "optimized_resume": optimized.model_dump()
    }


@router.post("/api/resume/download-html")
@limiter.limit("30/minute")
async def download_resume_html_file(request: Request):
    """Download the styled resume as an offline HTML file with embedded browser print engine."""
    body = await request.json()
    template_name = body.get("template", "modern")
    resume_data = body.get("parsed_resume")
    
    if not resume_data:
        raise HTTPException(status_code=400, detail="parsed_resume is required")
    if template_name not in AVAILABLE_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown template: {template_name}. Available: {AVAILABLE_TEMPLATES}")
    
    parsed = ResumeParsedData(**resume_data)
    html_content = render_template(template_name, parsed, compact_mode=True)
    
    return Response(
        content=html_content.encode("utf-8"),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=resume_{template_name}_1page.html"}
    )


