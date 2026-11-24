"""Send clearly structured contact reports through a configured SMTP service."""

import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from uuid import uuid4


class EmailNotConfigured(Exception):
    pass


def send_contact_report(report) -> str:
    host = os.environ.get("CYBERPLATFORM_SMTP_HOST", "").strip()
    sender = os.environ.get("CYBERPLATFORM_CONTACT_FROM", "").strip()
    recipient = os.environ.get("CYBERPLATFORM_CONTACT_TO", "").strip()
    username = os.environ.get("CYBERPLATFORM_SMTP_USERNAME", "").strip()
    password = os.environ.get("CYBERPLATFORM_SMTP_PASSWORD", "")
    security = os.environ.get("CYBERPLATFORM_SMTP_SECURITY", "starttls").lower()

    if not all((host, sender, recipient)) or bool(username) != bool(password):
        raise EmailNotConfigured("Contact email settings are incomplete")
    if security not in ("starttls", "ssl"):
        raise EmailNotConfigured("Contact email security must be starttls or ssl")

    port = int(
        os.environ.get("CYBERPLATFORM_SMTP_PORT", "465" if security == "ssl" else "587")
    )
    reference = f"CP-{uuid4().hex[:10].upper()}"
    category = report.category.value
    received_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Reply-To"] = report.email
    message["Subject"] = f"[CyberPlatform][{category}] {report.subject} ({reference})"
    message["X-CyberPlatform-Category"] = category
    message["X-CyberPlatform-Reference"] = reference
    message.set_content(
        "\n".join(
            [
                f"Reference: {reference}",
                f"Category: {category}",
                f"Received (UTC): {received_at}",
                f"Name: {report.name}",
                f"Reply email: {report.email}",
                f"Subject: {report.subject}",
                "",
                "WHAT HAPPENED",
                report.description,
                "",
                "STEPS TO REPRODUCE",
                report.steps or "Not provided",
                "",
                "EXPECTED RESULT",
                report.expected or "Not provided",
                "",
                "ACTUAL RESULT / ERROR MESSAGE",
                report.actual or "Not provided",
                "",
                f"Page or feature: {report.page or 'Not provided'}",
                f"Device and browser: {report.device or 'Not provided'}",
            ]
        )
    )

    context = ssl.create_default_context()
    if security == "ssl":
        connection = smtplib.SMTP_SSL(host, port, timeout=10, context=context)
    else:
        connection = smtplib.SMTP(host, port, timeout=10)
    with connection as smtp:
        if security == "starttls":
            smtp.starttls(context=context)
        if username:
            smtp.login(username, password)
        smtp.send_message(message)
    return reference
