from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Server
from schemas import ServerResponse, ServerCreate, ServerUpdate
from auth import require_roles
from prober import probe_universal

router = APIRouter(prefix="/servers", tags=["Infrastructure Server Inventory"])

def sync_server_realtime(server: Server):
    """Probes the server in real-time and updates its status and response time."""
    now = datetime.utcnow()
    ip = (server.ip_address or "").strip()
    status, latency = probe_universal(ip, target_type="server")
    server.status = status
    server.last_response_time_ms = latency
    server.last_check = now

@router.get("/", response_model=List[ServerResponse])
def list_servers(os_type: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Server)
    if os_type:
        query = query.filter(Server.os_type == os_type.lower())
    if status:
        query = query.filter(Server.status == status.upper())
    servers = query.order_by(Server.hostname.asc()).all()
    
    changed = False
    for s in servers:
        old_st = s.status
        old_lat = float(s.last_response_time_ms or 0.0)
        sync_server_realtime(s)
        if s.status != old_st or abs(float(s.last_response_time_ms or 0.0) - old_lat) > 0.01:
            changed = True
            
    if changed:
        try:
            db.commit()
        except Exception:
            db.rollback()
            
    return servers

@router.post("/", response_model=ServerResponse)
def create_or_update_server(
    server_in: ServerCreate,
    db: Session = Depends(get_db),
    _user = Depends(require_roles(["admin", "operator"]))
):
    server_data = server_in.dict()
    server_data["environment"] = str(server_data.get("environment", "production")).lower()
    server_data["os_type"] = str(server_data.get("os_type", "linux")).lower()

    existing = db.query(Server).filter(Server.hostname == server_in.hostname).first()
    if existing:
        # Update existing record seamlessly instead of throwing duplicate error
        existing.ip_address = server_data["ip_address"]
        existing.os_type = server_data["os_type"]
        existing.environment = server_data["environment"]
        existing.cpu_cores = server_data.get("cpu_cores", existing.cpu_cores)
        existing.total_ram_gb = server_data.get("total_ram_gb", existing.total_ram_gb)
        existing.total_disk_gb = server_data.get("total_disk_gb", existing.total_disk_gb)
        sync_server_realtime(existing)
        db.commit()
        db.refresh(existing)
        return existing

    server = Server(**server_data)
    sync_server_realtime(server)
    db.add(server)
    db.commit()
    db.refresh(server)
    return server

@router.put("/{server_id}", response_model=ServerResponse)
def update_server(
    server_id: int,
    server_in: ServerUpdate,
    db: Session = Depends(get_db),
    _user = Depends(require_roles(["admin", "operator"]))
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    for key, value in server_in.dict(exclude_unset=True).items():
        if key == "environment" and value:
            value = str(value).lower()
        elif key == "os_type" and value:
            value = str(value).lower()
        setattr(server, key, value)
        
    sync_server_realtime(server)
    db.commit()
    db.refresh(server)
    return server

@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    _user = Depends(require_roles(["admin", "operator"]))
):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    db.delete(server)
    db.commit()
    return {"status": "success", "message": f"Server {server.hostname} deleted"}
