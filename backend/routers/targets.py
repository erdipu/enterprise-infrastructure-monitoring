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
import time

router = APIRouter(prefix="/targets", tags=["Synthetic Monitoring Targets"])

def sync_target_realtime(target: MonitoringTarget):
    """
    Real-time status check for targets so the UI never displays stale or cached status.
    - Router/Heartbeat devices: Check if heartbeat arrived recently from router-syslog exporter.
    - External websites/APIs: Real-time HTTP/Socket probe.
    """
    now = datetime.now(timezone.utc)
    
    # Check if this target is a local router (192.168.1.7) or marked as router
    is_router = (
        "router" in target.name.lower() or 
        "wr845n" in target.name.lower() or 
        target.url_or_host == "192.168.1.7" or
        "103.181.90.226" in (target.url_or_host or "")
    )
    
    if is_router:
        try:
            # Query the cloud syslog exporter running on 172.18.0.1:9125 or 127.0.0.1:9125
            req = urllib.request.Request("http://172.18.0.1:9125", headers={"User-Agent": "NOC-Realtime-Sync"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = resp.read().decode()
                alive = 0
                latency = 0.0
                for line in data.splitlines():
                    if line.startswith("router_syslog_alive") and not line.startswith("#"):
                        alive = int(float(line.split()[-1]))
                    elif line.startswith("router_syslog_last_seen_seconds") and not line.startswith("#"):
                        age = float(line.split()[-1])
                        latency = 0.6 if alive == 1 else 0.0
                
                if alive == 1:
                    target.status = "UP"
                    target.last_response_time_ms = latency
                else:
                    target.status = "DOWN"
                    target.last_response_time_ms = 0.0
                target.last_check = now
        except Exception:
            try:
                # Fallback to local container host
                req = urllib.request.Request("http://host.docker.internal:9125", headers={"User-Agent": "NOC-Realtime-Sync"})
                with urllib.request.urlopen(req, timeout=2) as resp:
                    data = resp.read().decode()
                    alive = 0
                    for line in data.splitlines():
                        if line.startswith("router_syslog_alive") and not line.startswith("#"):
                            alive = int(float(line.split()[-1]))
                    if alive == 1:
                        target.status = "UP"
                        target.last_response_time_ms = 0.6
                    else:
                        target.status = "DOWN"
                        target.last_response_time_ms = 0.0
                    target.last_check = now
            except Exception:
                target.status = "DOWN"
                target.last_response_time_ms = 0.0
                target.last_check = now
    else:
        # Generic HTTP probe
        if target.target_type in ["website", "api"] and target.url_or_host:
            url = target.url_or_host if target.url_or_host.startswith("http") else f"http://{target.url_or_host}"
            try:
                start = time.time()
                req = urllib.request.Request(url, headers={"User-Agent": "NOC-HealthCheck/1.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    elapsed = (time.time() - start) * 1000.0
                    target.status = "UP" if resp.status < 400 else "DOWN"
                    target.last_response_time_ms = round(elapsed, 1)
            except Exception:
                target.status = "DOWN"
                target.last_response_time_ms = 0.0
            target.last_check = now

@router.get("/", response_model=List[MonitoringTargetResponse])
def list_targets(target_type: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(MonitoringTarget)
    if target_type:
        query = query.filter(MonitoringTarget.target_type == target_type)
    targets = query.order_by(MonitoringTarget.name.asc()).all()
    
    # Real-time synchronization
    changed = False
    for t in targets:
        sync_target_realtime(t)
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
    existing = db.query(MonitoringTarget).filter(MonitoringTarget.name == target_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Target name already registered")

    target = MonitoringTarget(**target_in.dict())
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
            url_or_host="192.168.1.7",
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
    return {"status": "success", "target": payload.target_name, "state": payload.status}
