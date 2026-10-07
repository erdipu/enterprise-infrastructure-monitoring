import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from sqlalchemy.orm import Session
from models import Incident, Notification
from config import settings

logger = logging.getLogger("monitoring.notifications")

class NotificationService:
    @staticmethod
    def dispatch_incident_notification(db: Session, incident: Incident, event_type: str = "CREATED"):
        """
        Dispatches notification across configured channels (Local, Telegram, Email)
        and persists delivery logs to the database.
        """
        subject = f"[{incident.priority}] Incident {incident.incident_number} {event_type}: {incident.title}"
        body = (
            f"=== ENTERPRISE MONITORING INCIDENT ALERT ===\n"
            f"Incident Number : {incident.incident_number}\n"
            f"Event Type      : {event_type}\n"
            f"Priority        : {incident.priority}\n"
            f"Severity        : {incident.severity}\n"
            f"Target System   : {incident.target_system}\n"
            f"Current Status  : {incident.status}\n"
            f"Description     : {incident.description}\n"
            f"Timestamp       : {incident.created_at.isoformat() if incident.created_at else ''}\n"
            f"==========================================="
        )

        # 1. Local Structured Log Notification
        logger.warning(f"NOTIFICATION DISPATCH: {subject}\n{body}")
        local_log = Notification(
            incident_id=incident.id,
            channel="local",
            recipient="NOC-Console",
            status="SENT",
            payload=body
        )
        db.add(local_log)

        # 2. Telegram Bot Dispatch (if credentials provided)
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            try:
                tg_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                tg_payload = {
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": f"🚨 *{incident.priority} Alert*\n*{incident.incident_number}* - {incident.title}\n*Target:* `{incident.target_system}`\n*Status:* {incident.status}\n\n{incident.description}",
                    "parse_mode": "Markdown"
                }
                res = requests.post(tg_url, json=tg_payload, timeout=5)
                tg_status = "SENT" if res.status_code == 200 else "FAILED"
                tg_err = None if res.status_code == 200 else res.text
            except Exception as e:
                tg_status = "FAILED"
                tg_err = str(e)
            
            db.add(Notification(
                incident_id=incident.id,
                channel="telegram",
                recipient=settings.TELEGRAM_CHAT_ID,
                status=tg_status,
                payload=body,
                error_message=tg_err
            ))

        # 3. SMTP Email Dispatch (if host provided)
        if settings.SMTP_HOST and settings.SMTP_USERNAME:
            try:
                msg = MIMEMultipart()
                msg["From"] = settings.SMTP_FROM_EMAIL
                msg["To"] = "noc-team@monitoring.local"
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as server:
                    server.starttls()
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
                    server.send_message(msg)
                mail_status = "SENT"
                mail_err = None
            except Exception as e:
                mail_status = "FAILED"
                mail_err = str(e)

            db.add(Notification(
                incident_id=incident.id,
                channel="email",
                recipient="noc-team@monitoring.local",
                status=mail_status,
                payload=body,
                error_message=mail_err
            ))

        db.commit()
