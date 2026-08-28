import logging
from typing import Optional
from fastapi import APIRouter, Request, Response, Query, HTTPException, status, Depends
from app.limiter import limiter
from app.auth import get_optional_user, AuthenticatedUser
from app.schemas import ResumeParsedData
from app.services.resume_generator import generate_resume_pdf, generate_resume_docx
from app.services.billing_service import check_entitlement, record_usage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["render"])

@router.post("/render")
@limiter.limit("20/minute")
async def render_resume(
    request: Request,
    data: ResumeParsedData, 
    format: str = Query("pdf", pattern="^(pdf|docx)$"),
    template_name: str = Query("classic"),
    compact_mode: bool = Query(False),
    user: Optional[AuthenticatedUser] = Depends(get_optional_user)
):
    """
    Renders structured resume data to either PDF (WeasyPrint) or Word (.docx) file.
    """
    # Determine the correct usage action type for this format
    usage_action = "pdf_generation" if format == "pdf" else "docx_generation"

    if user:
        if not check_entitlement(user.user_id, usage_action):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Billing limit reached: Upgrade to Pro for unlimited document rendering."
            )

    try:
        if format == "pdf":
            result_bytes = generate_resume_pdf(data, template_name, compact_mode=compact_mode)
            media_type = "application/pdf"
            filename = "resume.pdf"
        else:
            result_bytes = generate_resume_docx(data)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = "resume.docx"

        # Record usage AFTER successful render so failed renders don't consume quota
        if user:
            record_usage(user.user_id, usage_action, tokens_used=0, cost_usd=0.0)

        return Response(
            content=result_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except (ImportError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System rendering libraries missing: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to render resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render document: {str(e)}"
        )
