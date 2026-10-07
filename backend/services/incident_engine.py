import logging
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Alert, Incident, Server, MonitoringTarget
from schemas import AlertmanagerWebhookPayload, PrometheusAlertItem
from services.notification_service import NotificationService

logger = logging.getLogger("monitoring.incident_engine")

class IncidentEngine:
    @staticmethod
    def compute_fingerprint(alert: PrometheusAlertItem) -> str:
        if alert.fingerprint:
            return alert.fingerprint
        key_str = f"{alert.labels.get('alertname', '')}:{alert.labels.get('instance', '')}:{alert.labels.get('severity', '')}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    @staticmethod
    def map_priority_and_severity(alert: PrometheusAlertItem) -> tuple:
        priority = alert.labels.get("priority")
        severity = alert.labels.get("severity", "warning").capitalize()

        if not priority:
            if severity.lower() == "critical":
                priority = "P1"
            elif severity.lower() == "warning":
                priority = "P2"
            elif severity.lower() == "info":
                priority = "P4"
            else:
                priority = "P3"

        return priority, severity

    @classmethod
    def process_webhook_payload(cls, db: Session, payload: AlertmanagerWebhookPayload) -> dict:
        results = {"created": 0, "resolved": 0, "deduplicated": 0}

        for alert_item in payload.alerts:
            fingerprint = cls.compute_fingerprint(alert_item)
            alert_name = alert_item.labels.get("alertname", "UnknownAlert")
            target_instance = alert_item.labels.get("instance", "unknown-target")
            target_type = alert_item.labels.get("target_type", "host")
            summary = alert_item.annotations.get("summary", f"{alert_name} on {target_instance}")
            description = alert_item.annotations.get("description", summary)
            priority, severity = cls.map_priority_and_severity(alert_item)

            if alert_item.status.lower() == "firing":
                # Check for existing active incident with same fingerprint
                active_inc = db.query(Incident).filter(
                    Incident.fingerprint == fingerprint,
                    Incident.status.in_(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"])
                ).first()

                if active_inc:
                    logger.info(f"Deduplicated firing alert {alert_name} for {target_instance} (Active Incident {active_inc.incident_number})")
                    results["deduplicated"] += 1
                    continue

                # 1. Create Alert record
                alert_record = Alert(
                    fingerprint=fingerprint,
                    alert_name=alert_name,
                    target_name=target_instance,
                    target_type=target_type,
                    severity=alert_item.labels.get("severity", "warning"),
                    priority=priority,
                    status="firing",
                    summary=summary,
                    description=description,
                    started_at=datetime.utcnow()
                )
                db.add(alert_record)
                db.flush()

                # 2. Generate Next Incident Sequence Number
                count = db.query(func.count(Incident.id)).scalar() or 0
                incident_number = f"INC-2026-{count + 1:04d}"

                # 3. Create Incident
                new_incident = Incident(
                    incident_number=incident_number,
                    alert_id=alert_record.id,
                    fingerprint=fingerprint,
                    title=summary,
                    description=description,
                    priority=priority,
                    severity=severity,
                    status="OPEN",
                    target_system=target_instance,
                    alert_source="Prometheus",
                    created_at=datetime.utcnow()
                )
                db.add(new_incident)

                # 4. Update Target Status if found
                server_target = db.query(Server).filter(Server.hostname == target_instance).first()
                if server_target:
                    server_target.status = "DOWN" if priority == "P1" else "WARNING"
                    server_target.last_check = datetime.utcnow()

                web_target = db.query(MonitoringTarget).filter(MonitoringTarget.name == target_instance).first()
                if web_target:
                    web_target.status = "DOWN" if priority == "P1" else "WARNING"
                    web_target.last_check = datetime.utcnow()

                db.commit()
                db.refresh(new_incident)

                # 5. Dispatch Notifications
                NotificationService.dispatch_incident_notification(db, new_incident, "CREATED")
                results["created"] += 1

            elif alert_item.status.lower() == "resolved":
                active_inc = db.query(Incident).filter(
                    Incident.fingerprint == fingerprint,
                    Incident.status.in_(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"])
                ).first()

                if active_inc:
                    now = datetime.utcnow()
                    active_inc.status = "RESOLVED"
                    active_inc.resolved_at = now
                    if active_inc.created_at:
                        active_inc.mttr_seconds = int((now - active_inc.created_at.replace(tzinfo=None)).total_seconds())
                    active_inc.resolution_notes = "Auto-resolved via Prometheus Alertmanager resolution signal."

                    # Update associated alert
                    alert_rec = db.query(Alert).filter(Alert.fingerprint == fingerprint, Alert.status == "firing").first()
                    if alert_rec:
                        alert_rec.status = "resolved"
                        alert_rec.resolved_at = now

                    # Restore server / target status
                    server_target = db.query(Server).filter(Server.hostname == target_instance).first()
                    if server_target:
                        server_target.status = "UP"
                        server_target.last_check = now

                    web_target = db.query(MonitoringTarget).filter(MonitoringTarget.name == target_instance).first()
                    if web_target:
                        web_target.status = "UP"
                        web_target.last_check = now

                    db.commit()
                    NotificationService.dispatch_incident_notification(db, active_inc, "RESOLVED")
                    results["resolved"] += 1

        return results
