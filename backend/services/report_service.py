import io
import csv
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Server, Incident, MonitoringTarget

class ReportService:
    @staticmethod
    def get_executive_summary(db: Session) -> dict:
        total_servers = db.query(func.count(Server.id)).scalar() or 0
        servers_up = db.query(func.count(Server.id)).filter(Server.status == "UP").scalar() or 0
        servers_down = db.query(func.count(Server.id)).filter(Server.status == "DOWN").scalar() or 0
        servers_warning = db.query(func.count(Server.id)).filter(Server.status == "WARNING").scalar() or 0

        total_targets = db.query(func.count(MonitoringTarget.id)).scalar() or 0
        targets_up = db.query(func.count(MonitoringTarget.id)).filter(MonitoringTarget.status == "UP").scalar() or 0

        combined_total = total_servers + total_targets
        combined_up = servers_up + targets_up
        availability_pct = round((combined_up / combined_total * 100), 2) if combined_total > 0 else 100.0

        total_incidents = db.query(func.count(Incident.id)).scalar() or 0
        open_incidents = db.query(func.count(Incident.id)).filter(Incident.status.in_(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"])).scalar() or 0

        p1_count = db.query(func.count(Incident.id)).filter(Incident.priority == "P1").scalar() or 0
        p2_count = db.query(func.count(Incident.id)).filter(Incident.priority == "P2").scalar() or 0
        p3_count = db.query(func.count(Incident.id)).filter(Incident.priority == "P3").scalar() or 0
        p4_count = db.query(func.count(Incident.id)).filter(Incident.priority == "P4").scalar() or 0

        # Mean Time to Resolution (MTTR) calculation
        resolved_incidents = db.query(Incident).filter(Incident.mttr_seconds.isnot(None)).all()
        if resolved_incidents:
            avg_mttr_sec = sum(inc.mttr_seconds for inc in resolved_incidents) / len(resolved_incidents)
            avg_mttr_min = round(avg_mttr_sec / 60.0, 1)
        else:
            avg_mttr_min = 0.0

        # Top alerting systems
        top_systems = (
            db.query(Incident.target_system, func.count(Incident.id).label("count"))
            .group_by(Incident.target_system)
            .order_by(func.count(Incident.id).desc())
            .limit(5)
            .all()
        )
        top_alerting = [{"system": s[0], "incidents": s[1]} for s in top_systems]

        return {
            "total_servers": total_servers,
            "servers_up": servers_up,
            "servers_down": servers_down,
            "servers_warning": servers_warning,
            "overall_availability_pct": availability_pct,
            "total_incidents": total_incidents,
            "open_incidents": open_incidents,
            "p1_count": p1_count,
            "p2_count": p2_count,
            "p3_count": p3_count,
            "p4_count": p4_count,
            "avg_mttr_minutes": avg_mttr_min,
            "top_alerting_systems": top_alerting,
        }

    @staticmethod
    def generate_incidents_csv(db: Session) -> str:
        incidents = db.query(Incident).order_by(Incident.id.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Incident Number", "Title", "Priority", "Severity", "Status",
            "Target System", "Created At", "Resolved At", "MTTR (Sec)", "Root Cause", "Resolution Notes"
        ])
        for inc in incidents:
            writer.writerow([
                inc.incident_number,
                inc.title,
                inc.priority,
                inc.severity,
                inc.status,
                inc.target_system,
                inc.created_at.isoformat() if inc.created_at else "",
                inc.resolved_at.isoformat() if inc.resolved_at else "",
                inc.mttr_seconds or "",
                inc.root_cause or "",
                inc.resolution_notes or ""
            ])
        return output.getvalue()
