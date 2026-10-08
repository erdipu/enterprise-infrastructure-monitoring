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

