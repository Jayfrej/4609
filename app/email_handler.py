import smtplib, ssl, os
from email.message import EmailMessage

def send_email(subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    passwd = os.getenv("SMTP_PASS", "")
    sender = os.getenv("SMTP_FROM", "alerts@example.com")
    to = os.getenv("SMTP_TO", "")

    if not host or not to:
        return False  # SMTP not configured

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, port) as s:
        s.starttls(context=ctx)
        if user and passwd:
            s.login(user, passwd)
        s.send_message(msg)
    return True
