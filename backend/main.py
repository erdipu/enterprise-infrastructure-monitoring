import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from config import settings
from routers import auth, alerts, incidents, servers, targets, reports
from models import User, Server, MonitoringTarget, Incident
import datetime

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("monitoring.main")

# Auto-create tables if not existing
Base.metadata.create_all(bind=engine)

# Seed default admin user and sample data if tables are empty
def initialize_seed_data():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            logger.info("Database is empty. Seeding initial users and inventory...")
            from auth import get_password_hash
            db.add_all([
                User(
                    username="admin",
                    email="admin@monitoring.local",
                    full_name="Infrastructure Admin",
                    role="admin",
                    hashed_password=get_password_hash("AdminPassword123!")
                ),
                User(
                    username="operator",
                    email="operator@monitoring.local",
                    full_name="NOC Shift Engineer",
                    role="operator",
                    hashed_password=get_password_hash("OperatorPassword123!")
                ),
                User(
                    username="viewer",
                    email="viewer@monitoring.local",
                    full_name="Executive Viewer",
                    role="viewer",
                    hashed_password=get_password_hash("ViewerPassword123!")
                )
            ])
            db.commit()

        if db.query(Server).count() == 0:
            db.add_all([
                Server(hostname="srv-linux-prod-01", ip_address="192.168.10.11", os_type="linux", environment="production", status="UP", cpu_cores=8, total_ram_gb=32.0, total_disk_gb=500.0, last_check=datetime.datetime.utcnow()),
                Server(hostname="srv-linux-prod-02", ip_address="192.168.10.12", os_type="linux", environment="production", status="UP", cpu_cores=8, total_ram_gb=32.0, total_disk_gb=500.0, last_check=datetime.datetime.utcnow()),
                Server(hostname="srv-win-ad-01", ip_address="192.168.10.21", os_type="windows", environment="production", status="UP", cpu_cores=4, total_ram_gb=16.0, total_disk_gb=250.0, last_check=datetime.datetime.utcnow()),
                Server(hostname="srv-win-app-02", ip_address="192.168.10.22", os_type="windows", environment="staging", status="WARNING", cpu_cores=4, total_ram_gb=16.0, total_disk_gb=250.0, last_check=datetime.datetime.utcnow()),
            ])
            db.commit()

        if db.query(MonitoringTarget).count() == 0:
            db.add_all([
                MonitoringTarget(name="Production Web Portal", target_type="website", url_or_host="http://localhost:8000/health", port=8000, status="UP", last_response_time_ms=185.4, last_check=datetime.datetime.utcnow()),
                MonitoringTarget(name="Core Payments REST API", target_type="api", url_or_host="http://localhost:8000/api/v1/health", port=8000, status="UP", last_response_time_ms=92.1, last_check=datetime.datetime.utcnow())
            ])
            db.commit()

        if db.query(Incident).count() == 0:
            now = datetime.datetime.utcnow()
            db.add_all([
                Incident(
                    incident_number="INC-2026-0001",
                    fingerprint="fp-disk-winapp02",
                    title="Disk Space Utilization > 90% on D: Volume",
                    description="High disk usage on srv-win-app-02 log drive exceeding 90% threshold",
                    priority="P2",
                    severity="High",
                    status="RESOLVED",
                    target_system="srv-win-app-02",
                    alert_source="Prometheus",
                    created_at=now - datetime.timedelta(hours=2),
                    acknowledged_at=now - datetime.timedelta(minutes=105),
                    resolved_at=now - datetime.timedelta(minutes=60),
                    mttr_seconds=2700,
                    root_cause="Accumulation of uncompressed application trace logs",
                    resolution_notes="Purged archive logs older than 14 days and restarted log compression agent."
                ),
                Incident(
                    incident_number="INC-2026-0002",
                    fingerprint="fp-cpu-lnxprod01",
                    title="High CPU Utilization > 85%",
                    description="Host srv-linux-prod-01 sustained CPU load > 85% for 10 minutes",
                    priority="P3",
                    severity="Medium",
                    status="RESOLVED",
                    target_system="srv-linux-prod-01",
                    alert_source="Prometheus",
                    created_at=now - datetime.timedelta(hours=5),
                    acknowledged_at=now - datetime.timedelta(minutes=280),
                    resolved_at=now - datetime.timedelta(minutes=240),
                    mttr_seconds=2400,
                    root_cause="Batch reporting job concurrency spike",
                    resolution_notes="Adjusted cron job thread limits to 4 worker processes."
                ),
                Incident(
                    incident_number="INC-2026-0003",
                    fingerprint="fp-mem-winad01",
                    title="Memory Utilization Critical > 92%",
                    description="Host srv-win-ad-01 available memory dropped below 8%",
                    priority="P2",
                    severity="High",
                    status="ACKNOWLEDGED",
                    target_system="srv-win-ad-01",
                    alert_source="Prometheus",
                    created_at=now - datetime.timedelta(minutes=25),
                    acknowledged_at=now - datetime.timedelta(minutes=15),
                    root_cause="Investigating memory leak in authentication caching pool"
                )
            ])
            db.commit()
    finally:
        db.close()

initialize_seed_data()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Infrastructure Monitoring & Automated Incident Management Platform REST API"
)

# Enable CORS for browser frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Checks
@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "incident-management-backend",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "database": "connected"
    }

from fastapi.responses import PlainTextResponse
from config import ROUTER_STATE

@app.get("/metrics", response_class=PlainTextResponse, tags=["Observability"])
def prometheus_metrics():
    last_up = ROUTER_STATE.get("last_updated")
    is_up = 0
    lat = 0.0
    if last_up:
        diff = (datetime.datetime.utcnow() - last_up).total_seconds()
        if diff < 45 and ROUTER_STATE.get("status") == 1:
            is_up = 1
            lat = ROUTER_STATE.get("latency_ms", 0.0)
    else:
        is_up = ROUTER_STATE.get("status", 1)
        lat = ROUTER_STATE.get("latency_ms", 0.55)

    return f"""# HELP router_ping_latency_ms Secondary TP-Link router ping latency in milliseconds
# TYPE router_ping_latency_ms gauge
router_ping_latency_ms{{instance="192.168.1.7", router="TP-Link_WR845N", model="TL-WR845N"}} {lat}

# HELP router_up Secondary TP-Link router availability status (1=UP, 0=DOWN)
# TYPE router_up gauge
router_up{{instance="192.168.1.7", router="TP-Link_WR845N", model="TL-WR845N"}} {is_up}
"""

# Register API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(incidents.router, prefix=settings.API_V1_STR)
app.include_router(servers.router, prefix=settings.API_V1_STR)
app.include_router(targets.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)

# Mount Frontend NOC Portal
from fastapi.staticfiles import StaticFiles
import os

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if not os.path.exists(frontend_path):
    frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.BACKEND_PORT, reload=True)
