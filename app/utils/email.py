import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from typing import Optional


def send_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
    """Send email using SMTP"""
    try:
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            print(f"Email not configured. Would send to {to_email}: {subject}")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_password_reset_email(email: str, reset_token: str) -> bool:
    """Send password reset email"""
    reset_url = f"https://yourdomain.com/reset-password?token={reset_token}"
    subject = "Reset Your Password - Dely"
    html_body = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>You requested to reset your password. Click the link below to reset it:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>If you didn't request this, please ignore this email.</p>
            <p>This link will expire in 1 hour.</p>
        </body>
    </html>
    """
    return send_email(email, subject, "", html_body)

