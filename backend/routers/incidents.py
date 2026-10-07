from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from models import Incident, IncidentComment, AuditLog, User
from schemas import IncidentResponse, IncidentUpdate, IncidentCommentCreate, IncidentCommentResponse
from auth import get_current_user, require_roles
from services.notification_service import NotificationService

router = APIRouter(prefix="/incidents", tags=["ITIL Incident Management"])

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
