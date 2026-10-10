# Enterprise Infrastructure Monitoring & Incident Operations Platform
## Step-by-Step PC Rebuild & Workstation Recovery Guide

![Target](https://img.shields.io/badge/Target-Fresh%20or%20Formatted%20PC-blue)
![OS](https://img.shields.io/badge/OS-macOS%20%7C%20Windows%2011%20%7C%20Ubuntu-orange)
![Estimated Time](https://img.shields.io/badge/Time-15%20Minutes-green)

---

## 1. Overview & Objective

If your primary PC is formatted, replaced, damaged, or lost in a disaster, this guide provides a **step-by-step, beginner-friendly playbook** to restore your complete development environment and regain operational management of the platform within 15 minutes.

---

## 2. Prerequisites & Tool Installation

Execute these steps on your new or formatted machine:

### 2.1 Install Core Utilities

#### On macOS:
```bash
# 1. Install Xcode Command Line Tools (includes Git)
xcode-select --install

# 2. Install Homebrew package manager
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. Install Python 3.10+ and Docker
brew install python@3.10 git
brew install --cask docker
```

#### On Windows (PowerShell as Administrator):
```powershell
# 1. Install Git and Python using Winget
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3.10 -e --source winget

# 2. Install Docker Desktop
winget install --id Docker.DockerDesktop -e --source winget
```

#### On Ubuntu / Debian Linux:
```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

---

## 3. GitHub Authentication & Repository Cloning

### 3.1 Authenticate with GitHub
1. Open your browser and log in to [GitHub](https://github.com/login).
2. Generate a Personal Access Token (PAT) if needed:
   * Go to **Settings** $\rightarrow$ **Developer Settings** $\rightarrow$ **Personal Access Tokens (Tokens classic)**.
   * Generate token with `repo` scope.
3. Configure your local Git identity:
   ```bash
   git config --global user.name "Deepak"
   git config --global user.email "infoworld2112@gmail.com"
   ```

### 3.2 Clone the Project Repository
```bash
# Choose a workspace directory
mkdir -p ~/projects
cd ~/projects

# Clone repository
git clone https://github.com/erdipu/enterprise-infrastructure-monitoring.git
cd enterprise-infrastructure-monitoring
```

---

## 4. Restoring Configuration & Secrets

Public repositories do not store passwords or secret keys. Recover them using your secure backup or `.env.example` templates:

### 4.1 Create Local Environment File
```bash
cp .env.example .env
```
Open `.env` in any text editor and fill in your local secrets:
* `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/monitoring_db`
* `SECRET_KEY=<your_generated_jwt_secret>`
* `SMTP_PASSWORD=<your_gmail_app_password>`
* `TELEGRAM_BOT_TOKEN=<your_bot_token>`
* `TELEGRAM_CHAT_ID=<your_chat_id>`

### 4.2 Recover Oracle Cloud SSH Key
To manage your cloud servers (VM 1 and VM 2), restore your private SSH key (`ssh-key-2026-10-08.key`) from your secure offline storage (e.g. encrypted USB drive or password manager):

```bash
# Place key in your SSH directory
mkdir -p ~/.ssh
cp /path/to/backup/ssh-key-2026-10-08.key ~/.ssh/oracle_monitoring.key

# Set strict permissions (required by SSH protocol)
chmod 600 ~/.ssh/oracle_monitoring.key
```

### 4.3 Verify Cloud Server Connectivity
Test your connection to Oracle Cloud VM 2:
```bash
ssh -i ~/.ssh/oracle_monitoring.key -o StrictHostKeyChecking=no ubuntu@80.225.252.145 "uptime && sudo docker ps"
```
If you see the system uptime and 7 running Docker containers, your cloud access is 100% restored!

---

## 5. Local Development Stack Launch

To run the entire monitoring platform, PostgreSQL database, and NOC portal on your new machine:

### 5.1 Launch with Docker Compose
```bash
# Start all 7 containers in background
docker compose up -d

# Verify all containers are healthy
docker compose ps
```

### 5.2 Access Local Interfaces
Once launched, verify your local browser access:
* **NOC Operations Web Portal**: [http://localhost:8090](http://localhost:8090)
* **Grafana Dashboards**: [http://localhost:3000](http://localhost:3000)
* **Prometheus TSDB**: [http://localhost:9090](http://localhost:9090)
* **Alertmanager Console**: [http://localhost:9093](http://localhost:9093)
* **FastAPI Swagger Docs**: [http://localhost:8090/docs](http://localhost:8090/docs)

---

## 6. Restoring Database from Cloud or Backup

If you want your local database to match the exact historical records from production:

### 6.1 Download Latest Database Snapshot from VM 2
```bash
mkdir -p backups
scp -i ~/.ssh/oracle_monitoring.key ubuntu@80.225.252.145:/home/ubuntu/enterprise-infrastructure-monitoring/backups/eim_db_backup_*.sql.gz backups/
```

### 6.2 Restore into Local PostgreSQL
```bash
LATEST_BACKUP=$(ls -t backups/eim_db_backup_*.sql.gz | head -n 1)
bash scripts/restore_database.sh "${LATEST_BACKUP}" --force
```

---

## 7. Rebuilding Python Virtual Environment (Optional / Local Dev)

If you wish to run backend development scripts outside Docker:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\Activate.ps1

# Install project dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# Run backend unit tests
pytest tests/
```

---

## 8. Verification & Resuming Operations Checklist

Perform this 6-point checklist to confirm your new PC is 100% operational:

- [ ] Repository cloned with clean `git status`.
- [ ] SSH connection to Oracle Cloud VM 2 (`80.225.252.145`) succeeds.
- [ ] SSH connection to Oracle Cloud VM 1 (`161.118.180.68`) succeeds.
- [ ] Local Docker Compose containers report `healthy`.
- [ ] NOC Portal at `http://localhost:8090` opens and displays inventory.
- [ ] Production alerts continue dispatching to Telegram (`@my_infrastructure_alert_bot`).
