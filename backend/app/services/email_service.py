import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "alerts@echoapply.ai")

def send_html_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an HTML transactional email. Logs to console if SMTP variables are not set."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.info(
            f"[MOCK EMAIL SENT]\nTo: {to_email}\nSubject: {subject}\nBody: {html_body[:300]}..."
        )
        # Log mock email to a local file in data directory for validation
        from app.config import settings
        log_dir = os.path.join(settings.DATA_DIR, "sent_emails")
        os.makedirs(log_dir, exist_ok=True)
        import uuid
        file_path = os.path.join(log_dir, f"{uuid.uuid4()}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"<!-- Subject: {subject} | To: {to_email} -->\n{html_body}")
        logger.info(f"Mock HTML email saved to file: {file_path}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        part = MIMEText(html_body, "html")
        msg.attach(part)

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        
        logger.info(f"Successfully sent email alert to {to_email}.")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

def compile_alert_template(candidate_name: str, keyword: str, jobs: List[Dict[str, Any]]) -> str:
    """Compile a beautiful, premium responsive email alert template."""
    from app.config import settings
    jobs_rows = ""
    for j in jobs:
        jobs_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 12px 8px; font-family: sans-serif; font-size: 14px; color: #1e293b;">
                <strong>{j.get('title')}</strong><br>
                <span style="font-size: 12px; color: #64748b;">{j.get('company')} — {j.get('location', 'Remote')}</span>
            </td>
            <td style="padding: 12px 8px; font-family: sans-serif; font-size: 14px; text-align: right;">
                <a href="{j.get('apply_url') or '#'}" style="display: inline-block; background-color: #0d9488; color: #ffffff; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold;">Apply</a>
            </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 20px; background-color: #f8fafc; font-family: sans-serif;">
        <table align="center" width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <!-- Header -->
            <tr>
                <td style="background-color: #0d9488; padding: 24px 20px; text-align: center; color: #ffffff;">
                    <h1 style="margin: 0; font-size: 20px; font-weight: bold; letter-spacing: 0.5px;">Echo Apply</h1>
                    <p style="margin: 4px 0 0 0; font-size: 12px; opacity: 0.85;">New Job Matches Alert</p>
                </td>
            </tr>
            <!-- Content -->
            <tr>
                <td style="padding: 24px 20px;">
                    <p style="margin: 0 0 12px 0; font-size: 15px; color: #1e293b; line-height: 1.5;">Hi {candidate_name},</p>
                    <p style="margin: 0 0 20px 0; font-size: 14px; color: #475569; line-height: 1.5;">We found new job openings matching your saved alert query for <strong>"{keyword}"</strong>:</p>
                    
                    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; margin-bottom: 24px;">
                        {jobs_rows}
                    </table>
                    
                    <div style="text-align: center;">
                        <a href="{settings.FRONTEND_URL or 'http://localhost:3000'}" style="display: inline-block; background-color: #0d9488; color: #ffffff; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: bold; box-shadow: 0 4px 6px -1px rgba(13, 148, 136, 0.2);">Open Echo Apply Dashboard</a>
                    </div>
                </td>
            </tr>
            <!-- Footer -->
            <tr>
                <td style="background-color: #f1f5f9; padding: 16px 20px; text-align: center; font-size: 11px; color: #64748b; border-t: 1px solid #e2e8f0;">
                    This is an automated notification from EchoApply.ai. You can edit or unsubscribe from these alerts in your account settings.<br>
                    &copy; 2026 Echo Apply. All rights reserved.
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html
