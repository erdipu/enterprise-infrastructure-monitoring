#!/bin/bash
# ==============================================================================
# Enterprise Monitoring Platform - Automated PostgreSQL Backup & Disaster Recovery
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/eim_db_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

echo "[*] Starting PostgreSQL automated database snapshot at $(date)..."

# Dump database using Docker container or local pg_dump
if command -v docker &> /dev/null && docker ps | grep -q "eim-postgres"; then
    echo "[*] Executing pg_dump via eim-postgres container..."
    docker exec eim-postgres pg_dump -U postgres -d monitoring_db | gzip > "${BACKUP_FILE}"
else
    echo "[*] Executing local pg_dump..."
    pg_dump -U postgres -h localhost -d monitoring_db | gzip > "${BACKUP_FILE}"
fi

FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[+] Snapshot successfully created: ${BACKUP_FILE} (${FILE_SIZE})"

# Enforce 30-day retention policy
echo "[*] Enforcing ${RETENTION_DAYS}-day backup retention policy..."
find "${BACKUP_DIR}" -type f -name "eim_db_backup_*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete
echo "[+] Retention check complete. Database backup process finished successfully."
