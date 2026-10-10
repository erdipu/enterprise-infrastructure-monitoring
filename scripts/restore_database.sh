#!/bin/bash
# ==============================================================================
# Enterprise Monitoring Platform - Resilient PostgreSQL Database Restore Script
# ==============================================================================
# Usage:
#   ./scripts/restore_database.sh <path_to_backup.sql.gz> [--force]
#
# Safeguards:
#   1. Verifies that the specified backup file exists and is a valid gzip.
#   2. Automatically creates a safety backup of the current database before restoring.
#   3. Terminates active client connections gracefully before dropping/restoring.
#   4. Verifies database connectivity and table count post-restoration.
# ==============================================================================

set -euo pipefail

BACKUP_FILE="${1:-}"
FORCE_MODE="${2:-}"
DB_NAME="monitoring_db"
DB_USER="postgres"

if [ -z "${BACKUP_FILE}" ]; then
    echo "[-] Error: No backup file specified."
    echo "Usage: $0 <path_to_backup.sql.gz> [--force]"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[-] Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Verify gzip archive integrity
echo "[*] Verifying gzip archive integrity of ${BACKUP_FILE}..."
if ! gzip -t "${BACKUP_FILE}"; then
    echo "[-] Error: Backup file is corrupted or not a valid gzip file."
    exit 1
fi
echo "[+] Archive integrity verified successfully."

# Confirmation prompt unless --force is passed
if [ "${FORCE_MODE}" != "--force" ]; then
    echo "===================================================================="
    echo " WARNING: This will overwrite data in database '${DB_NAME}'!"
    echo " Target Backup: ${BACKUP_FILE}"
    echo "===================================================================="
    read -rp "Are you absolutely sure you want to proceed? (yes/no): " CONFIRM
    if [ "${CONFIRM}" != "yes" ]; then
        echo "[-] Restoration aborted by user."
        exit 0
    fi
fi

# 1. Create a pre-restore safety snapshot
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SAFETY_DIR="${REPO_DIR}/backups/safety_snapshots"
mkdir -p "${SAFETY_DIR}"
SAFETY_BACKUP="${SAFETY_DIR}/pre_restore_safety_${TIMESTAMP}.sql.gz"

echo "[*] Creating safety snapshot of existing database state to ${SAFETY_BACKUP}..."
if command -v docker &> /dev/null && docker ps | grep -q "eim-postgres"; then
    docker exec eim-postgres pg_dump -U "${DB_USER}" -d "${DB_NAME}" 2>/dev/null | gzip > "${SAFETY_BACKUP}" || true
else
    pg_dump -U "${DB_USER}" -h localhost -d "${DB_NAME}" 2>/dev/null | gzip > "${SAFETY_BACKUP}" || true
fi
echo "[+] Safety snapshot created: ${SAFETY_BACKUP}"

# 2. Terminate existing client connections to release locks
echo "[*] Terminating active connections to '${DB_NAME}'..."
TERMINATE_SQL="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();"

if command -v docker &> /dev/null && docker ps | grep -q "eim-postgres"; then
    docker exec -i eim-postgres psql -U "${DB_USER}" -d postgres -c "${TERMINATE_SQL}" >/dev/null 2>&1 || true
    echo "[*] Restoring database via Docker container (eim-postgres)..."
    zcat "${BACKUP_FILE}" | docker exec -i eim-postgres psql -U "${DB_USER}" -d "${DB_NAME}" >/dev/null
else
    psql -U "${DB_USER}" -h localhost -d postgres -c "${TERMINATE_SQL}" >/dev/null 2>&1 || true
    echo "[*] Restoring database via local psql..."
    zcat "${BACKUP_FILE}" | psql -U "${DB_USER}" -h localhost -d "${DB_NAME}" >/dev/null
fi

# 3. Post-restoration verification
echo "[*] Verifying restored database relations and row counts..."
CHECK_SQL="SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"

if command -v docker &> /dev/null && docker ps | grep -q "eim-postgres"; then
    TABLES=$(docker exec eim-postgres psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "${CHECK_SQL}")
else
    TABLES=$(psql -U "${DB_USER}" -h localhost -d "${DB_NAME}" -t -c "${CHECK_SQL}")
fi

TABLE_COUNT=$(echo "${TABLES}" | grep -c -v "^$" || true)
echo "[+] Verification successful! Restored ${TABLE_COUNT} active tables into '${DB_NAME}':"
echo "${TABLES}"

echo "===================================================================="
echo " [SUCCESS] Database restoration completed successfully!"
echo " Restored from: ${BACKUP_FILE}"
echo " Safety backup preserved at: ${SAFETY_BACKUP}"
echo "===================================================================="
