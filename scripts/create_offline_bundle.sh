#!/bin/bash
# ==============================================================================
# Enterprise Monitoring Platform - Complete Offline Recovery Bundle Creator
# ==============================================================================
# Packs the entire git repository, source code, schemas, and documentation
# into an offline standalone archive (.tar.gz) and Git bundle (.bundle)
# with SHA-256 checksums for 3-2-1 disaster recovery backup.
# ==============================================================================

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_DIR}/dist_backups}"
mkdir -p "${OUTPUT_DIR}"

BUNDLE_FILE="${OUTPUT_DIR}/enterprise_monitoring_git_${TIMESTAMP}.bundle"
ARCHIVE_FILE="${OUTPUT_DIR}/enterprise_monitoring_full_${TIMESTAMP}.tar.gz"

echo "=================================================================="
echo " Starting Enterprise Platform Offline Backup Packaging"
echo " Timestamp: ${TIMESTAMP}"
echo " Destination: ${OUTPUT_DIR}"
echo "=================================================================="

# 1. Create a complete Git Bundle (contains all commits, branches, and tags)
echo "[*] Creating complete offline Git bundle with full version history..."
git -C "${REPO_DIR}" bundle create "${BUNDLE_FILE}" --all
BUNDLE_SIZE=$(du -h "${BUNDLE_FILE}" | cut -f1)
echo "[+] Git bundle created: ${BUNDLE_FILE} (${BUNDLE_SIZE})"

# 2. Create a complete standalone archive (excluding temporary caches and local secrets)
echo "[*] Creating full standalone source archive..."
tar -C "${REPO_DIR}" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='alert_config.json' \
    --exclude='*.key' \
    --exclude='node_modules' \
    --exclude='dist_backups' \
    --exclude='backups' \
    -czf "${ARCHIVE_FILE}" .

ARCHIVE_SIZE=$(du -h "${ARCHIVE_FILE}" | cut -f1)
echo "[+] Standalone archive created: ${ARCHIVE_FILE} (${ARCHIVE_SIZE})"

# 3. Generate SHA-256 Checksums
calc_sha256() {
    local target="$1"
    if command -v sha256sum &>/dev/null; then
        sha256sum "${target}"
    else
        shasum -a 256 "${target}"
    fi
}

echo "[*] Computing cryptographic SHA-256 checksums..."
(
    cd "${OUTPUT_DIR}"
    calc_sha256 "$(basename "${BUNDLE_FILE}")" > "$(basename "${BUNDLE_FILE}").sha256"
    calc_sha256 "$(basename "${ARCHIVE_FILE}")" > "$(basename "${ARCHIVE_FILE}").sha256"
)

echo "=================================================================="
echo " [SUCCESS] Offline Disaster Recovery Bundle Created!"
echo " 1. Git Bundle:       ${BUNDLE_FILE}"
echo " 2. Source Archive:   ${ARCHIVE_FILE}"
echo " 3. Checksums:        ${OUTPUT_DIR}/*.sha256"
echo "=================================================================="
echo " Next Steps for 3-2-1 Compliance:"
echo " Copy these files to an external USB flash drive and an encrypted"
echo " offsite cloud folder (e.g., Google Drive / Oracle Object Storage)."
echo "=================================================================="
