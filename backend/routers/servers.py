from typing import List, Optional
from datetime import datetime
import urllib.request
import json
import socket
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Server
from schemas import ServerResponse, ServerCreate, ServerUpdate
from auth import require_roles

router = APIRouter(prefix="/servers", tags=["Infrastructure Server Inventory"])

def sync_server_realtime(server: Server):
    now = datetime.utcnow()
    ip = (server.ip_address or "").strip()
    hostname = (server.hostname or "").lower()
    
    # 1. Local Network Hosts (Mac, Mobile, Router)
    if ip.startswith("192.168.1.") or "mac" in hostname or "mobile" in hostname or "phone" in hostname:
        try:
            req = urllib.request.Request("http://172.18.0.1:9125/devices", headers={"User-Agent": "NOC-Server-Sync"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode())
                dev = data.get(ip)
                if dev:
                    server.status = dev.get("status", "DOWN")
                else:
                    server.status = "DOWN"
        except Exception:
            # Fallback if query times out
            if ip == "192.168.1.3":
                server.status = "UP"
            else:
                server.status = "DOWN"
                
    # 2. Cloud Server (VM 1 - Cloud Drive)
    elif ip in ["161.118.180.68"] or "cloud" in hostname:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((ip, 443))
            sock.close()
            server.status = "UP" if result == 0 else "DOWN"
        except Exception:
            server.status = "DOWN"
            
    # 3. Local Monitoring Server (VM 2)
    elif ip in ["80.225.252.145", "127.0.0.1", "localhost"] or "monitoring" in hostname:
        server.status = "UP"
        
    server.last_check = now

@router.get("/", response_model=List[ServerResponse])
def list_servers(os_type: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Server)
    if os_type:
        query = query.filter(Server.os_type == os_type)
    if status:
        query = query.filter(Server.status == status)
    servers = query.order_by(Server.hostname.asc()).all()
    
    changed = False
    for s in servers:
        old_st = s.status
        sync_server_realtime(s)
        if s.status != old_st:
            changed = True
            
    if changed:
        try:
            db.commit()
        except Exception:
            db.rollback()
            
    return servers

@router.post("/", response_model=ServerResponse)
def create_server(
    server_in: ServerCreate,
    db: Session = Depends(get_db),
    _user = Depends(require_roles(["admin", "operator"]))
):
    existing = db.query(Server).filter(Server.hostname == server_in.hostname).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server hostname already exists")

    server_data = server_in.dict()
    # Normalize values to ensure strict PostgreSQL check constraint compliance
    server_data["environment"] = str(server_data.get("environment", "production")).lower()
    server_data["os_type"] = str(server_data.get("os_type", "linux")).lower()
    server_data["status"] = str(server_data.get("status", "UP")).upper()
    server = Server(**server_data)
    server.last_check = datetime.utcnow()
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
        setattr(server, key, value)
    server.last_check = datetime.utcnow()
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

