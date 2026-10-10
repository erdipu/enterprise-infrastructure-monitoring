# Enterprise Infrastructure Monitoring & Incident Operations Platform
## Master Backup, Export & Offline Portability Guide

![Type](https://img.shields.io/badge/Type-Comprehensive%20Backup%20Manual-purple)
![Scope](https://img.shields.io/badge/Scope-Code%20%7C%20Database%20%7C%20Configs-blue)
![Format](https://img.shields.io/badge/Formats-Git%20Bundle%20%7C%20SQL.GZ%20%7C%20TAR.GZ-brightgreen)

---

## 1. Overview

This guide explains how to export, download, verify, and restore all components of the platform for cold-storage backup, offline archiving, or migration to another machine or cloud host.

---

## 2. Downloadable Source Code & Repository Backups

### 2.1 Download Source as ZIP from GitHub (No Git Required)
If you do not have Git installed or want an immediate snapshot:
1. Navigate to: [https://github.com/erdipu/enterprise-infrastructure-monitoring](https://github.com/erdipu/enterprise-infrastructure-monitoring)
2. Click the green **Code** button at the top right.
3. Select **Download ZIP**.
4. Extract the ZIP archive anywhere on your machine.

*Direct Browser Download Link:*
```text
https://github.com/erdipu/enterprise-infrastructure-monitoring/archive/refs/heads/main.zip
```

### 2.2 Complete Git Bundle Backup (Preserves 100% History)
Standard ZIP downloads do not include Git branches, commit history, or tags. To create an authentic, offline Git repository bundle:

```bash
# Execute within repository root
cd enterprise-infrastructure-monitoring
bash scripts/create_offline_bundle.sh
```
This produces:
* `enterprise_monitoring_git_<timestamp>.bundle`: A complete, self-contained Git repository in a single file.
* `enterprise_monitoring_full_<timestamp>.tar.gz`: Complete source archive without git metadata.
* `*.sha256`: Cryptographic checksums.

#### How to Restore from a Git Bundle on a New PC:
```bash
# Clone directly from the offline .bundle file without internet:
git clone enterprise_monitoring_git_20261010_XXXXXX.bundle restored-project/
cd restored-project/
git log -n 5 --oneline
```

---

## 3. Database Export & Data Preservation

The PostgreSQL database (`monitoring_db`) stores 8 critical business tables: `users`, `servers`, `monitoring_targets`, `incidents`, `alerts`, `incident_comments`, `audit_logs`, and `notifications`.

### 3.1 Automated Snapshot Generation
Run on Oracle Cloud VM 2 (or locally):
```bash
bash scripts/backup_database.sh
```
* **Output Path**: `./backups/eim_db_backup_<YYYYMMDD_HHMMSS>.sql.gz`
* **Retention Policy**: Automatically purges snapshots older than 30 days.

### 3.2 Manual Database Export Command
To generate an immediate custom-named snapshot:
```bash
# On Oracle Cloud VM 2
docker exec eim-postgres pg_dump -U postgres -d monitoring_db | gzip > backup_manual_$(date +%F).sql.gz
```

### 3.3 Remote Backup Transfer to Local PC
To pull the latest cloud database backup to your personal computer:
```bash
# Run on your local computer
scp -i ~/.ssh/oracle_monitoring.key \
    ubuntu@80.225.252.145:/home/ubuntu/enterprise-infrastructure-monitoring/backups/eim_db_backup_*.sql.gz \
    ~/backups/
```

---

## 4. Encrypting Sensitive Configuration Backups

**Rule: Never store unencrypted `.env` files or SSH private keys in public cloud drives.**

To safely back up sensitive credentials (`.env`, `alert_config.json`, and `ssh-key-2026-10-08.key`), use military-grade OpenSSL AES-256-CBC encryption:

### 4.1 Encrypting Configuration Files
```bash
# Package credentials into an archive
tar -czf secrets_bundle.tar.gz .env alert_config.json /path/to/ssh-key-2026-10-08.key

# Encrypt using AES-256 with password
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
    -in secrets_bundle.tar.gz \
    -out secrets_bundle.tar.gz.enc
```
*You will be prompted to enter an encryption passphrase. Store this passphrase in a secure password manager (e.g. Bitwarden or 1Password).*

### 4.2 Decrypting Configuration Files on a New PC
```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
    -in secrets_bundle.tar.gz.enc \
    -out secrets_bundle.tar.gz

# Extract recovered credentials
tar -xzf secrets_bundle.tar.gz
```

---

## 5. Verifying Backup Integrity

Never assume a backup file is valid without testing. Use the automated verification tool:

```bash
python3 scripts/verify_backup_integrity.py backups/eim_db_backup_20261010_120706.sql.gz
```

Expected Output:
```text
[*] Analyzing backup file: backups/eim_db_backup_20261010_120706.sql.gz
[+] File size: 8.70 KB (8909 bytes)
[+] SHA-256 Checksum: 4f98a2e1d7...
[*] Testing GZIP decompression...
[+] GZIP compression is valid and uncorrupted.
[+] Verified 4/4 structural PostgreSQL keywords:
    - Found keyword: 'PostgreSQL database dump'
    - Found keyword: 'CREATE TABLE'
    - Found keyword: 'public.'
    - Found keyword: 'ALTER TABLE'
[+] Checksum recorded to: backups/eim_db_backup_20261010_120706.sql.gz.sha256

========================================================
 [VERIFICATION PASSED] Backup is complete, valid, and safe!
========================================================
```

---

## 6. Recommended 3-2-1 Storage Locations (&#8377;0 Budget)

| Storage Layer | Medium | Storage Tool | Cost | Security & Encryption |
|---|---|---|:---:|---|
| **Copy 1 (Active)** | Cloud Server (OCI VM 2) & Local PC | Live Filesystem | **&#8377;0** | Server-level disk isolation |
| **Copy 2 (Versioned)** | GitHub Cloud Repository | `git push origin main` | **&#8377;0** | Public code / Non-sensitive templates |
| **Copy 3A (Offline)** | External USB Flash Drive (FAT32/exFAT) | Git Bundle & SQL Dumps | **&#8377;0** | Physically disconnected cold storage |
| **Copy 3B (Offsite Cloud)** | Google Drive (15 GB Free) / OCI Object Storage | Encrypted `.tar.gz.enc` | **&#8377;0** | AES-256 PBKDF2 Password Protected |
