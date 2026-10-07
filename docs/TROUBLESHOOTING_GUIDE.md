# Enterprise Infrastructure Monitoring Platform: Troubleshooting Guide

## 1. Quick Diagnostic Checklist

When observing monitoring anomalies, run this diagnostic sequence first:

```bash
# 1. Check all container statuses
docker compose ps

# 2. Inspect container logs for errors
docker compose logs --tail 50 backend
docker compose logs --tail 50 prometheus
docker compose logs --tail 50 alertmanager

# 3. Verify backend health endpoint
curl -s http://localhost:8000/health | jq .
```

---

## 2. Common Scenarios & Remediation

### Scenario 1: Prometheus Target Shows "DOWN"
- **Symptom**: In Prometheus UI (`http://localhost:9090/targets`), a scrape target displays `DOWN` with error `connection refused` or `context deadline exceeded`.
- **Root Cause**:
  - The exporter daemon (Node Exporter / Blackbox) is not running or listening on the target port.
  - A host firewall (iptables, ufw, Windows Defender) is blocking incoming TCP traffic on port 9100.
- **Fix**:
  1. Verify the process is running on the target:
     ```bash
     ps aux | grep node_exporter
     netstat -tuln | grep 9100
     ```
  2. Check firewall rules:
     ```bash
     sudo ufw allow 9100/tcp
     ```

---

### Scenario 2: Alertmanager Not Delivering Webhooks to FastAPI
- **Symptom**: Alerts appear in Alertmanager UI (`:9093`) but no incidents are created in the NOC Portal or database.
- **Root Cause**:
  - Alertmanager cannot resolve the hostname `backend:8000`.
  - FastAPI webhook route returned a 422 Unprocessable Entity or 500 error.
- **Fix**:
  1. Inspect Alertmanager logs:
     ```bash
     docker compose logs alertmanager | grep -i webhook
     ```
  2. Test the webhook manually:
     ```bash
     python3 scripts/simulate_webhook_alert.py --alert HostDown --status firing
     ```
  3. Check FastAPI application logs:
     ```bash
     docker compose logs backend | grep -i "alerts/webhook"
     ```

---

### Scenario 3: Grafana Shows "No Data" or Datasource Error
- **Symptom**: Dashboard panels show red triangle warning or empty graphs.
- **Root Cause**:
  - Datasource provisioning file had incorrect credentials or network URL.
  - Prometheus TSDB is still warming up or scrape targets have not completed their first scrape interval.
- **Fix**:
  1. In Grafana, navigate to **Connections → Data Sources**.
  2. Click **Prometheus** → scroll down and click **Save & Test**. Confirm green banner `Data source is working`.
  3. If testing PostgreSQL datasource, confirm banner `Database Connection OK`.

---

### Scenario 4: Port Conflicts on Workstation (8000, 3000, 5432, 9090)
- **Symptom**: `docker compose up` fails with:
  `Error response from daemon: driver failed programming external connectivity on endpoint: Bind for 0.0.0.0:5432 failed: port is already allocated`
- **Root Cause**: A local PostgreSQL instance, local Grafana, or local web server is already running outside Docker.
- **Fix**:
  1. Identify which process owns the port:
     - **macOS/Linux**:
       ```bash
       sudo lsof -i :5432
       sudo lsof -i :8000
       ```
     - **Windows**:
       ```powershell
       netstat -ano | findstr :5432
       ```
  2. Stop the local service:
     ```bash
     # Stop local brew postgres on Mac:
     brew services stop postgresql
     ```
  3. Alternatively, map to a different host port in `.env` (e.g., `POSTGRES_PORT=5433`).

---

### Scenario 5: Database Connection Exhaustion
- **Symptom**: Backend logs show `psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections`.
- **Root Cause**: SQLAlchemy connection pool leaking sessions without closing.
- **Fix**:
  1. Restart database container:
     ```bash
     docker compose restart postgres backend
     ```
  2. Check current active connections:
     ```sql
     SELECT count(*), state FROM pg_stat_activity GROUP BY state;
     ```
