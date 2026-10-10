# Antigravity AI Cold-Start Handover & Reconnection Guide

> **Purpose:** If you format your computer, lose this conversation, or start a completely fresh AI coding session in Google Antigravity, use this master prompt to instantly onboard Antigravity to your project and resume development with zero context loss.

---

## 1. What Is Required From Your Side (User Checklist)

Before starting a new Antigravity session on a fresh or formatted PC, make sure you have the following 4 prerequisites ready:

```text
[ ] 1. GITHUB REPOSITORY ACCESS:
       Repository URL: https://github.com/erdipu/enterprise-infrastructure-monitoring.git
       Authentication: GitHub Personal Access Token (PAT) or GitHub SSH Key configured.

[ ] 2. CLOUD SERVER SSH PRIVATE KEY:
       File Name: ssh-key-2026-10-08.key
       Destination on PC: ~/.ssh/ssh-key-2026-10-08.key
       Permissions: chmod 600 ~/.ssh/ssh-key-2026-10-08.key
       Server IP: 80.225.252.145 (User: ubuntu)

[ ] 3. ENVIRONMENT & CREDENTIAL SECRETS (From your Bitwarden Vault / Cold Backup):
       • Telegram Bot Token & Chat ID (@my_infrastructure_alert_bot)
       • Fast2SMS API Key & Phone Number
       • Gmail SMTP App Password (alerts@example.com)
       • DuckDNS Token (Domain: deepak-monitoring.duckdns.org)
       • PostgreSQL Master Password (Default: PostgresAdmin2026!)

[ ] 4. INSTALLED TOOLS ON YOUR PC:
       • Git, Python 3.10+, and Docker Desktop
       • Google Antigravity IDE / Agent
```

---

## 2. The Master Cold-Start Prompt for Antigravity

Copy the entire prompt block below and paste it directly into your first message to Antigravity:

```markdown
Hello Antigravity. I am the lead engineer for the **Universal Device & Service Monitoring Platform**. My PC was formatted / my previous conversation was cleared, and I need you to onboard onto this project, inspect its codebase and live hybrid cloud deployment, and assist me with developing and updating it.

### 1. Project Overview & Repository
- **GitHub Repository**: https://github.com/erdipu/enterprise-infrastructure-monitoring.git
- **Production Host**: http://deepak-monitoring.duckdns.org (Oracle Cloud OCI VM 2: 80.225.252.145)
- **Local Workspace**: Clone or open `enterprise-infrastructure-monitoring` in your scratch workspace.

### 2. Architecture & Technology Stack
- **Edge Network (On-Premises)**: TP-Link TL-WR845N (Target 1: 192.168.1.7, AP Mode) hardwired to ZTE F670LV9 Gateway. Transmits UDP 514 Syslog telemetry through CGNAT to Cloud VM 2.
- **Telemetry Daemons**:
  - `router_syslog_exporter.py`: UDP 514 syslog receiver & Prometheus metrics exporter on port :9125.
  - `router_watchdog.py`: 7-stage multi-target escalation engine (Telegram, SMS, Email).
- **Core Observability Stack (Docker Compose)**:
  - PostgreSQL 15 (`monitoring_db` with 8 tables: users, servers, monitoring_targets, incidents, alerts, incident_comments, audit_logs, notifications).
  - Prometheus (:9090), Alertmanager (:9093), Grafana (:3000), Node Exporter (:9100), Blackbox Exporter (:9115).
  - Backend API (:5000) & Custom NOC Portal Frontend (:8090).
- **Production Server Daemons**: Running 24/7 on Ubuntu 22.04 (`ubuntu@80.225.252.145`) under systemd (`router-syslog.service`, `router-watchdog.service`, cron backup).

### 3. Key Documentation to Read First
Please read the following documents in `docs/` before making changes:
1. `README.md` - Master portfolio documentation and emergency checklist.
2. `docs/ENTERPRISE_SYSTEM_ARCHITECTURE.md` - Live hybrid cloud architecture and CGNAT traversal.
3. `docs/DISASTER_RECOVERY_PLAN.md` - Master DRP and 3-2-1 backup strategy.
4. `docs/PROJECT_SETUP_GUIDE.md` - Complete server and local deployment instructions.
5. `docs/DATABASE_RECOVERY_GUIDE.md` - PostgreSQL schema and backup/restore scripts.

### 4. Strict Safety & Engineering Rules
1. **Never commit secrets**: Never commit private keys (`*.key`, `*.pem`), passwords, or API tokens to Git. Always use `.env.example` and `alert_config.example.json`.
2. **Zero-downtime on Production**: Do not restart or modify production containers or systemd daemons on `80.225.252.145` without verifying changes locally first.
3. **Always take pre-change backups**: If modifying the database, run `scripts/backup_database.sh` before running migrations.
4. **Synchronize GitHub and Cloud**: Any changes committed to GitHub must be cleanly pulled onto the cloud VM via SSH (`ssh -i ~/.ssh/ssh-key-2026-10-08.key ubuntu@80.225.252.145`).

### 5. My Immediate Request
Please first verify that you have cloned or navigated to the repository, inspect `git status` and the directory layout, verify your understanding of the architecture, and then help me with:

[DESCRIBE YOUR DESIRED CHANGE OR TASK HERE]
```

---

## 3. How Antigravity Will Respond and Execute

When you paste this prompt, Antigravity will automatically:
1. **Locate or Clone the Repository**: If the project isn't already present in your scratch directory, Antigravity will clone `https://github.com/erdipu/enterprise-infrastructure-monitoring.git`.
2. **Inspect the Architecture**: It will read `README.md` and `docs/ENTERPRISE_SYSTEM_ARCHITECTURE.md` to map out all 7 Docker containers, 2 edge daemons, and 8 database tables.
3. **Verify Cloud Connectivity**: It will test SSH access to `80.225.252.145` using `~/.ssh/ssh-key-2026-10-08.key`.
4. **Implement Your Requested Changes**: Whether adding a new monitoring target, modifying an alert rule, updating the frontend dashboard, or tuning database schemas, it will make the edits safely.
5. **Commit, Push, and Synchronize**: It will stage and commit your changes, push them to GitHub `main`, and run `git pull` on your production cloud VM.

---

## 4. Example Tasks You Can Request

Replace `[DESCRIBE YOUR DESIRED CHANGE OR TASK HERE]` with any specific task, such as:

- **Add a New Monitoring Target**:
  > *"Add a new HTTP health check target for my third server `https://api.mycompany.com` in `prometheus/blackbox.yml` and add an alert in `prometheus/alert.rules.yml`."*

- **Modify Alert Thresholds**:
  > *"Change the router watchdog offline alert threshold from 3 missed pings to 5 missed pings, and increase the Telegram notification cooldown from 5 minutes to 15 minutes."*

- **Update Frontend Dashboard**:
  > *"Add a new metric card in `frontend/index.html` that displays total daily resolved incidents and active router link uptime."*

- **Perform a Production Server Audit**:
  > *"SSH into `80.225.252.145`, check Docker container health, review systemd logs for `router-watchdog.service`, and verify that the nightly cron database backup ran successfully."*

- **Restore Database from Snapshot**:
  > *"Run `scripts/restore_database.sh` with the latest backup file from `/home/ubuntu/enterprise-infrastructure-monitoring/backups/` and verify table integrity."*
