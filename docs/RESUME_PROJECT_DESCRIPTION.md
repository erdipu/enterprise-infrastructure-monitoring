# Resume Description & Portfolio Assets

Use the following tailored bullet points, project summaries, and technical skills on your **Resume**, **LinkedIn**, and **Portfolio**.

---

## 1. Resume Project Entry (Standard Format)

**Enterprise Infrastructure Monitoring & Incident Management Platform**  
*Technologies: Prometheus, Grafana, Alertmanager, Python (FastAPI), PostgreSQL, Docker, Node Exporter, Blackbox Exporter, Bash, ITIL*

- Architected and deployed an end-to-end infrastructure monitoring and ITIL incident response platform for hybrid Linux/Windows servers, web applications, and microservice APIs.
- Implemented Prometheus-based pull metrics collection and auto-provisioned Grafana dashboards covering real-time CPU saturation, memory exhaustion, filesystem utilization, network I/O, and synthetic HTTP latencies.
- Designed 11 enterprise alerting rules with P1–P4 priority classification matrix, configuring Alertmanager grouping, deduplication, and inhibit rules to eliminate alert storms.
- Developed a Python FastAPI automation service integrated with PostgreSQL that ingests Alertmanager webhooks, automatically creates stateful tickets (`INC-2026-XXXX`), tracks engineer triage, and calculates Mean Time to Resolution (MTTR).
- Built a responsive dark-mode NOC Operations Web Portal with role-based access control (RBAC), multi-channel notification dispatchers (Telegram, Email, Console), and 1-click CSV SLA reporting.
- Authored 6 ITIL Standard Operating Procedure (SOP) runbooks and 5 safe failure simulation scripts (CPU stress, OOM risk, disk saturation, and service outages) for zero-risk operational drill testing.

---

## 2. Short LinkedIn Summary Format

**Enterprise Infrastructure Monitoring & Incident Management Platform (Open-Source)**
Developed a production-grade, 100% free and locally hosted infrastructure observability platform mirroring capabilities of enterprise platforms like BMC TrueSight and OpsRamp. Features Prometheus time-series collection, Grafana executive dashboards, Alertmanager deduplication/inhibit rules, an automated Python/FastAPI incident management engine with PostgreSQL, an interactive NOC web portal, and comprehensive ITIL SOP runbooks.

---

## 3. Key Technical Skills Demonstrated

- **Infrastructure Monitoring & Observability**: Prometheus, Node Exporter, Blackbox Exporter, PromQL, Time-Series Databases (TSDB), Synthetic Probing, SSL Verification.
- **Data Visualization & Dashboards**: Grafana 10+, Automated Datasource & Dashboard Provisioning, Executive KPI Dashboards.
- **Event & Alert Management**: Prometheus Alertmanager, Inhibit Rules, Alert Grouping & Suppression, Alert Storm Mitigation.
- **ITIL Incident Management**: Priority Matrix (P1 Critical to P4 Low), Lifecycle Triage (`OPEN` → `ACKNOWLEDGED` → `IN_PROGRESS` → `RESOLVED`), MTTR Metrics, SLA Compliance (99.5%).
- **Backend & Automation**: Python 3, FastAPI, SQLAlchemy ORM, Pydantic, RESTful APIs, Webhook Handlers, JWT Authentication, PBKDF2 Cryptography, RBAC.
- **Database & Storage**: PostgreSQL 15, Relational Schema Design, Foreign Keys, Index Optimization, Audit Logging.
- **DevOps & Containerization**: Docker, Docker Compose, Multi-Container Orchestration, Container Health Checks, Shell Scripting, Git.
- **Operations & Systems**: Linux & Windows Server Administration, Memory Architecture (`MemAvailable` vs `MemFree`), Filesystem Maintenance, Runbook/SOP Authoring.
