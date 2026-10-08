from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import MonitoringTarget
from schemas import MonitoringTargetResponse, MonitoringTargetCreate
from auth import require_roles

router = APIRouter(prefix="/targets", tags=["Synthetic Monitoring Targets"])

@router.get("/", response_model=List[MonitoringTargetResponse])
def list_targets(target_type: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(MonitoringTarget)
    if target_type:
        query = query.filter(MonitoringTarget.target_type == target_type)
    return query.order_by(MonitoringTarget.name.asc()).all()

@router.post("/", response_model=MonitoringTargetResponse)
def create_target(
    target_in: MonitoringTargetCreate,
    db: Session = Depends(get_db),
    _user = Depends(require_roles(["admin", "operator"]))
):
    existing = db.query(MonitoringTarget).filter(MonitoringTarget.name == target_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Target name already registered")

    target = MonitoringTarget(**target_in.dict())
    target.last_check = datetime.utcnow()
    db.add(target)
    db.commit()
    db.refresh(target)
    return target

@router.delete("/{target_id}")
def delete_target(
    target_id: int,
    db: Session = Depends(get_db),
    _user = Depends(require_roles(["admin", "operator"]))
):
    target = db.query(MonitoringTarget).filter(MonitoringTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    db.delete(target)
    db.commit()
    return {"status": "success", "message": f"Target {target.name} deleted"}

from pydantic import BaseModel
import requests

class HeartbeatPayload(BaseModel):
    target_name: str
    status: str  # "UP" or "DOWN"
    response_time_ms: float = 0.0

@router.post("/heartbeat")
def receive_heartbeat(
    payload: HeartbeatPayload,
    db: Session = Depends(get_db)
):
    target = db.query(MonitoringTarget).filter(MonitoringTarget.name == payload.target_name).first()
    if not target:
        target = MonitoringTarget(
            name=payload.target_name,
            target_type="host",
            url_or_host="192.168.1.7",
            port=80,
            check_interval_sec=15,
            expected_status_code=200,
            status=payload.status,
            last_response_time_ms=payload.response_time_ms,
            last_check=datetime.utcnow()
        )
        db.add(target)
    else:
        old_status = target.status
        target.status = payload.status
        target.last_response_time_ms = payload.response_time_ms
        target.last_check = datetime.utcnow()

        if payload.status == "DOWN" and old_status != "DOWN":
            try:
                requests.post(
                    "http://alertmanager:9093/api/v2/alerts",
                    json=[{
                        "labels": {
                            "alertname": "SecondaryRouterDown",
                            "instance": "TP-Link_TL-WR845N (192.168.1.7)",
                            "severity": "critical",
                            "priority": "P1",
                            "target_type": "host"
                        },
                        "annotations": {
                            "summary": "Secondary Router TP-Link TL-WR845N is DOWN",
                            "description": "Ping checks to 192.168.1.7 failed. Router powered off or LAN wire disconnected."
                        }
                    }],
                    timeout=3
                )
            except Exception:
                pass

    db.commit()
    return {"status": "success", "target": payload.target_name, "state": payload.status}

