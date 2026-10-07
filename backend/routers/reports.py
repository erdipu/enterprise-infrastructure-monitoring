from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database import get_db
from schemas import ExecutiveSummaryResponse
from services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Executive & Operational Reports"])

@router.get("/summary", response_model=ExecutiveSummaryResponse)
def get_summary_report(db: Session = Depends(get_db)):
    summary = ReportService.get_executive_summary(db)
    return summary

@router.get("/export/csv")
def export_incidents_csv(db: Session = Depends(get_db)):
    csv_data = ReportService.generate_incidents_csv(db)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=incidents_report.csv"}
    )
