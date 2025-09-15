import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List

from livekit.agents import function_tool, RunContext

from . import config


def send_email_smtp(to_emails: List[str], subject: str, message: str, cc_emails: Optional[List[str]] = None) -> None:
    if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
        raise RuntimeError("Gmail credentials not configured.")

    msg = MIMEMultipart()
    msg["From"] = config.GMAIL_USER
    msg["To"] = ", ".join(to_emails)
    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    recipients = list(to_emails) + (cc_emails or [])

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
    server.sendmail(config.GMAIL_USER, recipients, msg.as_string())
    server.quit()


@function_tool()
async def send_email(context: RunContext, to_email: str, subject: str, message: str, cc_email: Optional[str] = None) -> str:
    try:
        cc_list = [cc_email] if cc_email else None
        send_email_smtp([to_email], subject, message, cc_list)
        return f"✅ Email sent successfully to {to_email}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"


