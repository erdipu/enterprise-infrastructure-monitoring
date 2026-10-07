from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Alert
from schemas import AlertmanagerWebhookPayload
from services.incident_engine import IncidentEngine

router = APIRouter(prefix="/alerts", tags=["Prometheus Alerts & Webhook"])

@router.post("/webhook")
def receive_alertmanager_webhook(payload: AlertmanagerWebhookPayload, db: Session = Depends(get_db)):
    """
    Ingests firing and resolved alerts from Prometheus Alertmanager.
    Automatically correlates events, deduplicates noise, and manages incident lifecycles.
    """
    result = IncidentEngine.process_webhook_payload(db, payload)
    return {
        "status": "success",
        "message": f"Processed alert batch: {result['created']} created, {result['resolved']} resolved, {result['deduplicated']} deduplicated",
        "details": result
    }

@router.get("/")
def list_alerts(
    status: Optional[str] = Query(None, description="Filter by alert status: firing, resolved"),
    priority: Optional[str] = Query(None, description="Filter by priority: P1, P2, P3, P4"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    if priority:
        query = query.filter(Alert.priority == priority)
    return query.order_by(Alert.id.desc()).limit(limit).all()
