# Enterprise Infrastructure Monitoring & Incident Operations Platform
## Complete End-to-End Project Setup & Deployment Guide

![Platform](https://img.shields.io/badge/Platform-Ubuntu%2022.04%20LTS-orange)
![Docker](https://img.shields.io/badge/Docker-Compose%20v2-2496ED)
![Prometheus](https://img.shields.io/badge/Prometheus-v2.48.1-F46800)
![Services](https://img.shields.io/badge/Systemd-router--syslog%20%7C%20router--watchdog-green)

---

## 1. System Architecture & Prerequisites

This guide explains how to deploy the complete platform on a fresh Linux server (Oracle Cloud VM 2 or any Ubuntu 22.04 LTS instance).

### Minimum Hardware Requirements:
* **CPU**: 1 vCPU (AMD or ARM Ampere).
* **RAM**: 1 GB RAM (2 GB recommended).
* **Disk**: 15 GB available SSD storage.
* **OS**: Ubuntu 22.04 LTS (x86_64 or aarch64).

---

## 2. Server Initial Configuration & Dependencies

Execute on your target Linux host as `ubuntu` or root:

```bash
# 1. Update OS package repositories
sudo apt update && sudo apt upgrade -y

# 2. Install essential system dependencies
sudo apt install -y git curl wget net-tools python3 python3-pip python3-venv \
                    docker.io docker-compose-plugin python3-reportlab

# 3. Add current user to docker group
sudo usermod -aG docker $USER

# 4. Enable and start Docker service
sudo systemctl enable --now docker
```

---

## 3. Clone Repository & Configure Environment

```bash
# 1. Clone repository to /home/ubuntu
cd /home/ubuntu
git clone https://github.com/erdipu/enterprise-infrastructure-monitoring.git
cd enterprise-infrastructure-monitoring

# 2. Provision environment configuration
cp .env.example .env
cp alert_config.example.json /home/ubuntu/alert_config.json
chmod 600 /home/ubuntu/alert_config.json
```

### 3.1 Configure `alert_config.json`
Edit `/home/ubuntu/alert_config.json`:
```json
{
  "telegram_bot_token": "<YOUR_TELEGRAM_BOT_TOKEN>",
  "telegram_chat_id": "<YOUR_TELEGRAM_CHAT_ID>",
  "fast2sms_api_key": "<YOUR_FAST2SMS_KEY_IF_ANY>",
  "sms_mobile_number": "<YOUR_MOBILE_NUMBER>"
}
```

---

## 4. Deploy Docker Observability & Incident Stack

Launch the 7 core containerized services:
* `eim-backend`: Custom NOC Web Portal & REST API (:8090)
* `eim-postgres`: PostgreSQL 15 Database (:5432)
* `eim-prometheus`: Prometheus Time-Series Database (:9090)
* `eim-grafana`: Grafana Visualizations Dashboard (:3000)
* `eim-alertmanager`: Prometheus Alertmanager (:9093)
* `eim-node-exporter`: Host Performance Metrics (:9100)
* `eim-blackbox-exporter`: Synthetic HTTP Probing (:9115)

```bash
cd /home/ubuntu/enterprise-infrastructure-monitoring
docker compose up -d

# Verify all containers boot and reach healthy status
docker compose ps
```

---

## 5. Deploy Native Systemd Telemetry Daemons

The edge router monitoring requires low-level UDP 514 socket binding and continuous background watchdog evaluation:

### 5.1 Copy Daemon Scripts to `/home/ubuntu`
```bash
cp router_syslog_exporter.py /home/ubuntu/router_syslog_exporter.py
cp router_watchdog.py /home/ubuntu/router_watchdog.py
```

### 5.2 Create Telemetry Exporter Service (`router-syslog.service`)
```bash
sudo tee /etc/systemd/system/router-syslog.service > /dev/null << 'EOF'
[Unit]
Description=Router Syslog Telemetry Collector & Prometheus Exporter
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/python3 /home/ubuntu/router_syslog_exporter.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

### 5.3 Create Incident Watchdog Service (`router-watchdog.service`)
```bash
sudo tee /etc/systemd/system/router-watchdog.service > /dev/null << 'EOF'
[Unit]
Description=Corporate Router Escalation Watchdog Engine
After=network.target router-syslog.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/usr/bin/python3 /home/ubuntu/router_watchdog.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

### 5.4 Enable and Start Both Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now router-syslog.service
sudo systemctl enable --now router-watchdog.service

# Verify both services report active (running)
sudo systemctl status router-syslog.service -n 5
sudo systemctl status router-watchdog.service -n 5
```

---

## 6. Edge Gateway Telemetry Configuration (ZTE F670LV9)

To stream real-time Layer-2 physical bridge telemetry to your cloud server:

1. Open a browser and log in to your primary gateway: `http://192.168.1.1`.
2. Navigate to: **Management & Diagnosis** $\rightarrow$ **System Log** (or **Syslog Configuration**).
3. Configure settings:
   * **Log Level**: Informational (or Notice).
   * **Server Address**: `deepak-monitoring.duckdns.org` (or your cloud server IP: `80.225.252.145`).
   * **Server Port**: `514` (UDP).
4. Click **Apply / Save**.
5. Connect your secondary router (TP-Link TL-WR845N) via physical Ethernet to **Port 3** of the ZTE gateway.

---

## 7. Cloud Firewall / Ingress Rules (Oracle OCI VCN)

Ensure your Oracle Cloud Virtual Cloud Network (VCN) Ingress Security List permits the following incoming ports:

| Protocol | Port | Source CIDR | Purpose |
|:---:|:---:|:---:|---|
| **TCP** | 22 | `0.0.0.0/0` | Secure Shell (SSH) Administrative Access |
| **TCP** | 8090 | `0.0.0.0/0` | Custom NOC Operations Web Portal |
| **TCP** | 3000 | `0.0.0.0/0` | Grafana Operations Dashboards |
| **TCP** | 9090 | `0.0.0.0/0` | Prometheus Time-Series UI |
| **TCP** | 9093 | `0.0.0.0/0` | Alertmanager Console |
| **TCP** | 9125 | `0.0.0.0/0` | Router Syslog Prometheus Metrics Exporter |
| **UDP** | 514 | `0.0.0.0/0` | Edge Gateway Syslog Telemetry Stream |

---

## 8. Verification & End-to-End Health Checks

Run these diagnostic commands to verify the entire platform:

```bash
# 1. Check raw router exporter metrics
curl -s http://127.0.0.1:9125

# 2. Check Prometheus target health
curl -s http://127.0.0.1:9090/api/v1/targets | grep -o '"health":"[^"]*"'

# 3. View live watchdog telemetry evaluation
sudo journalctl -u router-watchdog -n 20 --no-pager

# 4. Trigger safe test alert to Telegram
python3 /home/ubuntu/send_router_alert.py test
```

If you receive the test alert on your Telegram bot (`@my_infrastructure_alert_bot`), your platform is 100% operational!
