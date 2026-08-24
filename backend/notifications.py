from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Optional


def email_delivery_configured() -> bool:
    return bool(os.environ.get("CONSENSUS_SCOPE_SMTP_HOST") and os.environ.get("CONSENSUS_SCOPE_EMAIL_FROM"))


def send_transactional_email(*, recipient: str, subject: str, body: str) -> bool:
    if not email_delivery_configured():
        return False
    host = os.environ["CONSENSUS_SCOPE_SMTP_HOST"]
    port = int(os.environ.get("CONSENSUS_SCOPE_SMTP_PORT", "587"))
    username = os.environ.get("CONSENSUS_SCOPE_SMTP_USERNAME", "")
    password = os.environ.get("CONSENSUS_SCOPE_SMTP_PASSWORD", "")
    use_ssl = os.environ.get("CONSENSUS_SCOPE_SMTP_SSL", "").strip().lower() in {"1", "true", "yes"}
    use_starttls = os.environ.get("CONSENSUS_SCOPE_SMTP_STARTTLS", "true").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    message = EmailMessage()
    message["From"] = os.environ["CONSENSUS_SCOPE_EMAIL_FROM"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_class(host, port, timeout=15) as client:
        if use_starttls and not use_ssl:
            client.starttls()
        if username:
            client.login(username, password)
        client.send_message(message)
    return True


def account_action_url(path: str, token: str) -> str:
    public_url = os.environ.get("CONSENSUS_SCOPE_PUBLIC_URL", "https://demo.consensusscope.cn").rstrip("/")
    separator = "&" if "?" in path else "?"
    return f"{public_url}/{path.lstrip('/')}{separator}token={token}"


def exposed_test_token(token: str) -> Optional[str]:
    expose = os.environ.get("CONSENSUS_SCOPE_EXPOSE_ONE_TIME_TOKENS", "").strip().lower()
    return token if expose in {"1", "true", "yes"} else None
