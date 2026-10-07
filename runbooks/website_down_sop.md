# Standard Operating Procedure (SOP): Synthetic Web & API Outage

**Document ID**: SOP-INFRA-005  
**Category**: Application & Synthetic Availability  
**Alert Trigger**: `WebsiteDown` (`probe_success == 0` for 1m → **P1 Critical**)

---

## 1. Initial Assessment & Triage
1. **Acknowledge Ticket**: Within 5-minute SLA.
2. **Review Blackbox Exporter Telemetry**:
   - Check Grafana Synthetic Probe panel: What failed? HTTP status code (500, 502, 503, 504), connection refused, SSL certificate expiry, or DNS lookup failure?

---

## 2. Investigation Steps
1. **Manual HTTP Probe from Terminal**:
   ```bash
   curl -Iv -s -S https://<target_url>
   ```
2. **Interpret HTTP Response Codes**:
   - `000 (Connection Refused)`: Web server (Nginx/Apache) or backend application process is stopped.
   - `502 Bad Gateway`: Reverse proxy is running, but upstream application server (FastAPI/NodeJS/Gunicorn) is down or crashing.
   - `504 Gateway Timeout`: Upstream service is hanging or database queries are locked.
   - `SSL Certificate Expired`: TLS handshake failed due to expired x509 cert.
3. **Inspect Application Pods / Services**:
   ```bash
   sudo systemctl status nginx
   sudo systemctl status backend
   # Or docker/kubernetes:
   docker ps -a
   docker logs --tail 100 eim-backend
   ```

---

## 3. Remediation & Recovery Actions
1. **Web Server / Backend Down**:
   ```bash
   sudo systemctl restart nginx
   sudo systemctl restart backend
   ```
2. **Database Connectivity Lockout**:
   - Verify PostgreSQL connection pool:
     ```bash
     pg_isready -h localhost -p 5432
     ```
3. **SSL Certificate Expiration**:
   - Renew certificate using Certbot or install refreshed company CA cert:
     ```bash
     sudo certbot renew
     ```

---

## 4. Ticket Closure
1. Verify `curl -s -o /dev/null -w "%{http_code}" https://<target_url>` returns `200`.
2. Confirm Blackbox prober reports `probe_success == 1`.
3. Document root cause and close incident in NOC Portal.
