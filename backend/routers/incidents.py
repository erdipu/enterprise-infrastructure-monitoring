import hashlib
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Incident, IncidentComment, AuditLog, User, Alert, MonitoringTarget, Server
from schemas import (
    IncidentResponse, IncidentUpdate, IncidentCommentCreate, 
    IncidentCommentResponse, InternalTriggerIncidentRequest, InternalResolveIncidentRequest
)
from auth import get_current_user, require_roles
from services.notification_service import NotificationService

router = APIRouter(prefix="/incidents", tags=["ITIL Incident Management"])

@router.post("/internal/trigger")
def internal_trigger_incident(payload: InternalTriggerIncidentRequest, db: Session = Depends(get_db)):
    """
    Automated incident trigger endpoint used by Watchdog probers and local telemetry agents.
    Deduplicates active open incidents, generates official INC sequence number,
    creates audit & alert records, and marks target DOWN in real-time.
    """
    # 1. Deduplication: Check if there is an active incident for this target
    active_inc = db.query(Incident).filter(
        (Incident.target_system == payload.target_name) | 
        (Incident.target_system == payload.target_info) |
        (Incident.title == payload.summary),
        Incident.status.in_(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"])
    ).first()

    if active_inc:
        return {
            "status": "existing",
            "incident_number": active_inc.incident_number,
            "incident_id": active_inc.id,
            "priority": active_inc.priority,
            "created_at": active_inc.created_at.isoformat() if active_inc.created_at else None
        }

    # 2. Fingerprint generation
    clean_target = (payload.target_info or payload.target_name).replace("https://", "").replace("http://", "").strip("/")
    fingerprint = hashlib.sha256(f"watchdog:{clean_target}".encode()).hexdigest()[:16]

    # 3. Create Alert record
    alert_record = Alert(
        fingerprint=fingerprint,
        alert_name=f"{payload.target_name} Outage",
        target_name=payload.target_name,
        target_type=payload.target_type,
        severity=payload.severity.lower(),
        priority=payload.priority,
        status="firing",
        summary=payload.summary,
        description=payload.description or payload.summary,
        started_at=datetime.utcnow()
    )
    db.add(alert_record)
    db.flush()

    # 4. Generate next sequential incident number: INC-2026-XXXX
    count = db.query(func.count(Incident.id)).scalar() or 0
    incident_number = f"INC-2026-{count + 1:04d}"

    # 5. Create Incident
    new_inc = Incident(
        incident_number=incident_number,
        alert_id=alert_record.id,
        fingerprint=fingerprint,
        title=payload.summary,
        description=payload.description or payload.summary,
        priority=payload.priority,
        severity=payload.severity,
        status="OPEN",
        target_system=payload.target_name,
        alert_source="Watchdog",
        created_at=datetime.utcnow()
    )
    db.add(new_inc)

    # 6. Update target status to DOWN
    if payload.target_info:
        targets = db.query(MonitoringTarget).filter(
            (MonitoringTarget.name.ilike(f"%{payload.target_name}%")) |
            (MonitoringTarget.url_or_host.ilike(f"%{clean_target}%"))
        ).all()
        for t in targets:
            t.status = "DOWN"
            t.last_check = datetime.utcnow()

        srvs = db.query(Server).filter(
            (Server.hostname.ilike(f"%{payload.target_name}%")) |
            (Server.ip_address.ilike(f"%{clean_target}%"))
        ).all()
        for s in srvs:
            s.status = "DOWN"
            s.last_check = datetime.utcnow()

    db.commit()
    db.refresh(new_inc)

    return {
        "status": "created",
        "incident_number": new_inc.incident_number,
        "incident_id": new_inc.id,
        "priority": new_inc.priority,
        "created_at": new_inc.created_at.isoformat()
    }

@router.post("/internal/resolve")
def internal_resolve_incident(payload: InternalResolveIncidentRequest, db: Session = Depends(get_db)):
    """
    Automated incident resolution endpoint called when Watchdog prober detects service recovery.
    Marks incident RESOLVED, calculates MTTR, and restores target status to UP.
    """
    query = db.query(Incident).filter(Incident.status.in_(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]))
    if payload.incident_number:
        query = query.filter(Incident.incident_number == payload.incident_number)
    else:
        query = query.filter(
            (Incident.target_system == payload.target_name) |
            (Incident.target_system == payload.target_info) |
            (Incident.title.ilike(f"%{payload.target_name}%"))
        )
    
    active_inc = query.order_by(Incident.id.desc()).first()
    if not active_inc:
        return {
            "status": "not_found",
            "message": f"No active incident found for {payload.target_name}"
        }

    now = datetime.utcnow()
    active_inc.status = "RESOLVED"
    active_inc.resolved_at = now
    if active_inc.created_at:
        active_inc.mttr_seconds = int((now - active_inc.created_at.replace(tzinfo=None)).total_seconds())
    active_inc.resolution_notes = payload.resolution_notes or "Auto-resolved via Watchdog recovery telemetry."

    if active_inc.alert_id:
        alert_rec = db.query(Alert).filter(Alert.id == active_inc.alert_id).first()
        if alert_rec:
            alert_rec.status = "resolved"
            alert_rec.resolved_at = now

    # Restore target status to UP
    clean_target = (payload.target_info or payload.target_name).replace("https://", "").replace("http://", "").strip("/")
    targets = db.query(MonitoringTarget).filter(
        (MonitoringTarget.name.ilike(f"%{payload.target_name}%")) |
        (MonitoringTarget.url_or_host.ilike(f"%{clean_target}%"))
    ).all()
    for t in targets:
        t.status = "UP"
        t.last_check = now

    srvs = db.query(Server).filter(
        (Server.hostname.ilike(f"%{payload.target_name}%")) |
        (Server.ip_address.ilike(f"%{clean_target}%"))
    ).all()
    for s in srvs:
        s.status = "UP"
        s.last_check = now

    db.commit()

    return {
        "status": "resolved",
        "incident_number": active_inc.incident_number,
        "incident_id": active_inc.id,
        "mttr_seconds": active_inc.mttr_seconds
    }

@router.get("/", response_model=List[IncidentResponse])
def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    target: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Incident)
    if status_filter:
        query = query.filter(Incident.status == status_filter)
    if priority:
        query = query.filter(Incident.priority == priority)
    if target:
        query = query.filter(Incident.target_system.ilike(f"%{target}%"))
    return query.order_by(Incident.id.desc()).limit(limit).all()

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@router.put("/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: int,
    update_data: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "operator"]))
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status = incident.status
    if update_data.status:
        incident.status = update_data.status
        if update_data.status == "ACKNOWLEDGED" and not incident.acknowledged_at:
            incident.acknowledged_at = datetime.utcnow()
        elif update_data.status == "RESOLVED":
            if not incident.resolved_at:
                now = datetime.utcnow()
                incident.resolved_at = now
                if incident.created_at:
                    incident.mttr_seconds = int((now - incident.created_at.replace(tzinfo=None)).total_seconds())

    if update_data.assigned_to_user_id is not None:
        incident.assigned_to_user_id = update_data.assigned_to_user_id
    if update_data.root_cause:
        incident.root_cause = update_data.root_cause
    if update_data.resolution_notes:
        incident.resolution_notes = update_data.resolution_notes

    # Audit log
    db.add(AuditLog(
        user_id=current_user.id,
        action="UPDATE_INCIDENT",
        entity_type="incident",
        entity_id=incident.id,
        details=f"Status: {old_status} -> {incident.status}"
    ))

    db.commit()
    db.refresh(incident)

    if old_status != incident.status:
        NotificationService.dispatch_incident_notification(db, incident, f"STATUS_CHANGE_TO_{incident.status}")

    return incident

@router.post("/{incident_id}/comments", response_model=IncidentCommentResponse)
def add_incident_comment(
    incident_id: int,
    comment_in: IncidentCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "operator", "viewer"]))
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    new_comment = IncidentComment(
        incident_id=incident.id,
        user_id=current_user.id,
        comment=comment_in.comment
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment
