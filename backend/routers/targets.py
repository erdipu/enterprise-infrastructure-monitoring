from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import MonitoringTarget
from schemas import MonitoringTargetResponse, MonitoringTargetCreate
from auth import require_roles
from pydantic import BaseModel
import urllib.request
import json
from prober import probe_universal

router = APIRouter(prefix="/targets", tags=["Synthetic Monitoring Targets"])

def sync_target_realtime(target: MonitoringTarget):
    """
    Real-time multi-protocol status check for targets:
    Supports websites, APIs, private LAN IPs, and network hosts.
    """
    now = datetime.now(timezone.utc)
    status, latency = probe_universal(
        host=target.url_or_host,
        port=target.port,
        target_type=target.target_type
    )
    target.status = status
    target.last_response_time_ms = latency
    target.last_check = now

@router.get("/", response_model=List[MonitoringTargetResponse])
def list_targets(target_type: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(MonitoringTarget)
    if target_type:
        query = query.filter(MonitoringTarget.target_type == target_type)
    targets = query.order_by(MonitoringTarget.name.asc()).all()
    
    changed = False
    for t in targets:
        old_st = t.status
        old_lat = float(t.last_response_time_ms or 0.0)
        sync_target_realtime(t)
        if t.status != old_st or abs(float(t.last_response_time_ms or 0.0) - old_lat) > 0.01:
            changed = True
            
    if changed:
        try:
            db.commit()
        except Exception:
            db.rollback()
            
    return targets

@router.post("/", response_model=MonitoringTargetResponse)
def create_target(
    target_in: MonitoringTargetCreate,
    db: Session = Depends(get_db),
    _user = Depends(require_roles(["admin", "operator"]))
):
    target_data = target_in.dict()
    existing = db.query(MonitoringTarget).filter(MonitoringTarget.name == target_in.name).first()
    if existing:
        existing.url_or_host = target_data.get("url_or_host", existing.url_or_host)
        existing.target_type = target_data.get("target_type", existing.target_type)
        existing.port = target_data.get("port", existing.port)
        existing.check_interval_sec = target_data.get("check_interval_sec", existing.check_interval_sec)
        existing.expected_status_code = target_data.get("expected_status_code", existing.expected_status_code)
        sync_target_realtime(existing)
        db.commit()
        db.refresh(existing)
        return existing

    target = MonitoringTarget(**target_data)
    sync_target_realtime(target)
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

class HeartbeatPayload(BaseModel):
    target_name: str
    status: str  # "UP" or "DOWN"
    response_time_ms: float = 0.0

@router.post("/heartbeat")
def receive_heartbeat(
    payload: HeartbeatPayload,
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    target = db.query(MonitoringTarget).filter(MonitoringTarget.name == payload.target_name).first()
    if not target:
        target = MonitoringTarget(
            name=payload.target_name,
            target_type="host",
            url_or_host="192.168.1.2",
            port=80,
            check_interval_sec=15,
            expected_status_code=200,
            status=payload.status,
            last_response_time_ms=payload.response_time_ms if payload.status == "UP" else 0.0,
            last_check=now
        )
        db.add(target)
    else:
        target.status = payload.status
        target.last_response_time_ms = payload.response_time_ms if payload.status == "UP" else 0.0
        target.last_check = now

    db.commit()

    # Forward heartbeat directly to router_syslog_exporter on :9125
    is_router_hb = (
        "router" in payload.target_name.lower() or
        "wr845n" in payload.target_name.lower() or
        "192.168.1.2" in payload.target_name or
        "192.168.1.7" in payload.target_name
    )
    if is_router_hb:
        fwd_payload = json.dumps({
            "status": payload.status,
            "response_time_ms": payload.response_time_ms,
            "source": "noc_api_heartbeat"
        }).encode("utf-8")
        for exporter_url in ["http://172.18.0.1:9125/heartbeat", "http://127.0.0.1:9125/heartbeat", "http://host.docker.internal:9125/heartbeat"]:
            try:
                fwd_req = urllib.request.Request(exporter_url, data=fwd_payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(fwd_req, timeout=1) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                continue

    return {"status": "success", "target": payload.target_name, "state": payload.status}
