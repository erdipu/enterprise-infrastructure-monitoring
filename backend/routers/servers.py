from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Server
from schemas import ServerResponse, ServerCreate, ServerUpdate
from auth import require_roles

router = APIRouter(prefix="/servers", tags=["Infrastructure Server Inventory"])

@router.get("/", response_model=List[ServerResponse])
def list_servers(os_type: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Server)
    if os_type:
        query = query.filter(Server.os_type == os_type)
    if status:
        query = query.filter(Server.status == status)
    return query.order_by(Server.hostname.asc()).all()

@router.post("/", response_model=ServerResponse)
def create_server(
    server_in: ServerCreate,
    db: Session = Depends(get_db),
    _user = Depends(require_roles(["admin", "operator"]))
):
    existing = db.query(Server).filter(Server.hostname == server_in.hostname).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server hostname already exists")

    server = Server(**server_in.dict())
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

