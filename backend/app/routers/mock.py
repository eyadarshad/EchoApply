from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from app.config import settings

router = APIRouter(tags=["mock"])

@router.get("/mock-apply-form", response_class=HTMLResponse)
async def mock_apply_form(
    login: bool = Query(False),
    captcha: bool = Query(False),
    unmapped: bool = Query(False)
):
    """
    Renders a mock job application form for local sandboxed testing of Playwright auto-apply.
    """
    if login:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Mock Job Board - Login</title></head>
        <body style="font-family: Arial, sans-serif; background: #0f172a; color: #f1f5f9; padding: 40px; text-align: center;">
            <h1>Sign in to your account</h1>
            <form action="/mock-login-submit" method="POST" style="max-width: 300px; margin: 0 auto; text-align: left;">
                <div style="margin-bottom: 15px;">
                    <label for="username" style="display:block; margin-bottom:5px;">Username</label>
                    <input type="text" id="username" name="username" required style="width:100%; padding:8px;">
                </div>
                <div style="margin-bottom: 15px;">
                    <label for="password" style="display:block; margin-bottom:5px;">Password</label>
                    <input type="password" id="password" name="password" required style="width:100%; padding:8px;">
                </div>
                <button type="submit" style="background:#4f46e5; color:white; border:none; padding:10px 20px; cursor:pointer;">Log In</button>
            </form>
        </body>
        </html>
        """, status_code=200)
        
    if captcha:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Mock Job Board - Verification</title></head>
        <body style="font-family: Arial, sans-serif; background: #0f172a; color: #f1f5f9; padding: 40px; text-align: center;">
            <h1>Verify you are human</h1>
            <p>Please complete the challenge below</p>
            <div style="max-width: 400px; margin: 20px auto; padding: 20px; border: 1px solid #334155;">
                <iframe src="about:blank" title="reCAPTCHA verification challenge" style="width: 300px; height: 80px; border:none; background:#1e293b;"></iframe>
                <form action="/mock-captcha-submit" method="POST" style="margin-top:15px; text-align: left;">
                    <div>
                        <label for="captcha" style="display:block; margin-bottom:5px;">Solve captcha *</label>
                        <input type="text" id="captcha" name="captcha" required style="width:100%; padding:8px;">
                    </div>
                    <button type="submit" style="background:#4f46e5; color:white; border:none; padding:10px 20px; margin-top:10px; cursor:pointer;">Verify & Submit</button>
                </form>
            </div>
        </body>
        </html>
        """, status_code=200)

    # Standard Mock Form
    unmapped_field_html = ""
    if unmapped:
        unmapped_field_html = """
        <div class="field">
            <label for="favorite_language">Favorite Coding Language *</label>
            <input type="text" id="favorite_language" name="favorite_language" required>
        </div>
        """

    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mock Job Board - Application Form</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; background: #0f172a; color: #f1f5f9; border: 1px solid #334155; border-radius: 12px; }}
            .field {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 8px; font-weight: 600; color: #94a3b8; }}
            input[type="text"], input[type="email"], input[type="tel"], input[type="url"], select, textarea {{
                width: 100%; padding: 10px; border: 1px solid #334155; border-radius: 8px; background: #1e293b; color: #f1f5f9; box-sizing: border-box;
            }}
            button {{ background: #4f46e5; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; }}
            button:hover {{ background: #4338ca; }}
        </style>
    </head>
    <body>
        <h1 style="color: #6366f1;">Apply for Software Engineer</h1>
        <p style="color: #64748b; font-size: 14px; margin-bottom: 24px;">Please fill out the form below to submit your application.</p>
        <form action="/mock-apply-submit" method="POST">
            <div class="field">
                <label for="fullname">Full Name *</label>
                <input type="text" id="fullname" name="fullname" required>
            </div>
            
            <div class="field">
                <label for="email">Email Address *</label>
                <input type="email" id="email" name="email" required>
            </div>
            
            <div class="field">
                <label for="phone">Phone Number</label>
                <input type="tel" id="phone" name="phone">
            </div>
            
            <div class="field">
                <label for="github">GitHub URL</label>
                <input type="url" id="github" name="github">
            </div>
            
            <div class="field">
                <label for="resume">Upload Resume / CV *</label>
                <input type="file" id="resume" name="resume" required>
            </div>
            
            <div class="field">
                <label for="fastapi_exp">How many years of experience do you have with FastAPI? *</label>
                <textarea id="fastapi_exp" name="fastapi_exp" rows="3" required></textarea>
            </div>
            
            <div class="field">
                <label for="salary_exp">What is your expected salary? *</label>
                <input type="text" id="salary_exp" name="salary_exp" required>
            </div>
            
            <div class="field">
                <label for="terms_agree">
                    <input type="checkbox" id="terms_agree" name="terms_agree" required value="agree">
                    Do you agree to the terms of service? *
                </label>
            </div>
            
            {unmapped_field_html}
            
            <button type="submit">Submit Application</button>
        </form>
    </body>
    </html>
    """, status_code=200)

@router.post("/mock-apply-submit", response_class=HTMLResponse)
async def mock_apply_submit():
    """
    Handles form submission for local mock job board.
    """
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head><title>Mock Job Board - Success</title></head>
    <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 100px; background: #0f172a; color: #f1f5f9;">
        <h1 style="color: #10b981;">Application Submitted Successfully!</h1>
        <p>Thank you for applying. We have received your application.</p>
    </body>
    </html>
    """, status_code=200)
