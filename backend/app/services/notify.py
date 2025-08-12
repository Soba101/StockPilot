from __future__ import annotations
import smtplib
import json
import hmac
import hashlib
from email.message import EmailMessage
from typing import List, Dict, Any
import requests
from app.core.config import settings

class NotificationResult(Dict[str, Any]):
    pass

def send_email(subject: str, body: str) -> NotificationResult:
    if not settings.SMTP_HOST:
        return NotificationResult(channel="email", delivered=False, reason="smtp_not_configured")
    try:
        msg = EmailMessage()
        msg["From"] = settings.ALERT_EMAIL_FROM or "alerts@stockpilot.local"
        msg["To"] = settings.ALERT_EMAIL_TO or settings.ALERT_EMAIL_FROM or "devnull@local"
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)
        return NotificationResult(channel="email", delivered=True)
    except Exception as e:
        return NotificationResult(channel="email", delivered=False, error=str(e))

def send_webhook(payload: dict) -> NotificationResult:
    if not settings.ALERT_WEBHOOK_URL:
        return NotificationResult(channel="webhook", delivered=False, reason="webhook_not_configured")
    try:
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json"}
        if settings.ALERT_SIGNING_SECRET:
            digest = hmac.new(settings.ALERT_SIGNING_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Signature"] = digest
        resp = requests.post(settings.ALERT_WEBHOOK_URL, data=body, headers=headers, timeout=5)
        return NotificationResult(channel="webhook", delivered=resp.status_code < 300, status=resp.status_code)
    except Exception as e:
        return NotificationResult(channel="webhook", delivered=False, error=str(e))

def dispatch_digest(digest, channels: List[str]) -> List[NotificationResult]:
    subject = f"Stockout Digest {digest.run_date} (H:{digest.counts['high']} M:{digest.counts['medium']})"
    lines = [subject, f"Strategy: {digest.strategy}"]
    for item in digest.top_soonest:
        lines.append(f"{item.sku} {item.name} on_hand={item.on_hand} days={item.days_to_stockout} src={item.velocity_source}")
    body = "\n".join(lines)
    results: List[NotificationResult] = []
    if "email" in channels:
        results.append(send_email(subject, body))
    if "webhook" in channels:
        results.append(send_webhook({"digest": digest.__dict__}))
    return results

__all__ = ["dispatch_digest", "send_email", "send_webhook", "NotificationResult"]
