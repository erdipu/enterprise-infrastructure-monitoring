# Enterprise Infrastructure Monitoring Platform: Installation & Deployment Guide

## 1. Prerequisites

Before starting the platform, ensure your workstation or server meets the following requirements:

| Component | Minimum Requirement | Recommended |
|---|---|---|
| **CPU** | 2 Cores | 4 Cores |
| **RAM** | 4 GB | 8 GB |
| **Storage** | 10 GB Free Disk Space | 20 GB Free SSD |
| **OS** | macOS 12+, Ubuntu 20.04+, RHEL 8+, Windows 10/11 (WSL2) | macOS Sonoma / Ubuntu 22.04 LTS |
| **Runtimes** | Docker & Docker Compose, Python 3.9+ | Docker Desktop / Docker Engine 24+ |

---

## 2. Installation by Operating System

### 2.1 macOS (Apple Silicon or Intel)
1. **Install Docker Desktop**:
   - Download the installer from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/).
   - Drag Docker to `/Applications` and launch it from Spotlight.
   - Verify Docker CLI in your terminal:
     ```bash
     docker --version
     docker compose version
     ```
2. **Clone the Repository**:
   ```bash
   cd ~/projects
   git clone <repo_url> enterprise-infrastructure-monitoring
   cd enterprise-infrastructure-monitoring
   ```
3. **Configure Environment File**:
   ```bash
   cp .env.example .env
   ```
4. **Launch Platform**:
   ```bash
   docker compose up -d
   ```

---

### 2.2 Linux (Ubuntu / Debian / RHEL)
1. **Install Docker Engine & Compose**:
   ```bash
   # Ubuntu / Debian
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-v2
   sudo systemctl enable --now docker
   sudo usermod -aG docker $USER
   ```
2. **Clone and Start**:
   ```bash
   git clone <repo_url> enterprise-infrastructure-monitoring
   cd enterprise-infrastructure-monitoring
   cp .env.example .env
   docker compose up -d
   ```

---

### 2.3 Windows 10/11 (via WSL2 / Docker Desktop)
1. Install **WSL2** by opening PowerShell as Administrator and running:
   ```powershell
   wsl --install
   ```
2. Install **Docker Desktop for Windows** and enable the **WSL2 Engine** in Docker Settings.
3. Open your WSL2 terminal (Ubuntu) and execute:
   ```bash
   git clone <repo_url> enterprise-infrastructure-monitoring
   cd enterprise-infrastructure-monitoring
   cp .env.example .env
   docker compose up -d
   ```

---

## 3. Post-Installation Service Access

Once `docker compose up -d` executes, access the services using your web browser:

| Application / Service | URL | Default Credentials | Description |
|---|---|---|---|
| **Custom NOC Web Portal** | [http://localhost:8000](http://localhost:8000) | `admin` / `AdminPassword123!` | Incident triage, server inventory, CSV export |
| **FastAPI REST API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | N/A | Swagger UI interactive API documentation |
| **Grafana Dashboards** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin` (or Anonymous Viewer) | Executive & technical metrics visualizations |
| **Prometheus Dashboard** | [http://localhost:9090](http://localhost:9090) | N/A | PromQL queries, targets status, rule engine |
| **Alertmanager Console** | [http://localhost:9093](http://localhost:9093) | N/A | Active alert grouping, routes, silences |
| **PostgreSQL Database** | `localhost:5432` | `postgres` / `postgres_secure_password_replace_me` | Persistent database datastore |

---

## 4. Verifying Health Status

Run the following command to check all container health states:

```bash
docker compose ps
```

Expected output:
```text
NAME                     IMAGE                       STATUS                    PORTS
eim-postgres             postgres:15-alpine          Up (healthy)              0.0.0.0:5432->5432/tcp
eim-prometheus           prom/prometheus:v2.48.1     Up (healthy)              0.0.0.0:9090->9090/tcp
eim-alertmanager         prom/alertmanager:v0.26.0   Up (healthy)              0.0.0.0:9093->9093/tcp
eim-backend              backend:latest              Up (healthy)              0.0.0.0:8000->8000/tcp
eim-grafana              grafana/grafana:10.2.2      Up (healthy)              0.0.0.0:3000->3000/tcp
eim-node-exporter        prom/node-exporter:v1.7.0   Up                        0.0.0.0:9100->9100/tcp
eim-blackbox-exporter    prom/blackbox-exporter:v... Up                        0.0.0.0:9115->9115/tcp
```
