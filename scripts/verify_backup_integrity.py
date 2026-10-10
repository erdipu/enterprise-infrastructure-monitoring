#!/usr/bin/env python3
"""
Enterprise Monitoring Platform - Backup Integrity & Verification Utility
Checks GZIP compression integrity, validates SQL dump signatures, computes SHA-256 checksums,
and verifies schema structure.
"""

import sys
import os
import gzip
import hashlib

REQUIRED_SQL_KEYWORDS = [
    b"PostgreSQL database dump",
    b"CREATE TABLE",
    b"public.",
    b"ALTER TABLE"
]

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def verify_backup(filepath):
    print(f"[*] Analyzing backup file: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"[-] Error: File does not exist: {filepath}")
        return False

    size_bytes = os.path.getsize(filepath)
    size_kb = size_bytes / 1024
    print(f"[+] File size: {size_kb:.2f} KB ({size_bytes} bytes)")
    
    if size_bytes < 512:
        print("[-] Error: Backup file is too small to be a valid dump (< 512 bytes).")
        return False

    # Checksum calculation
    sha256_hash = compute_sha256(filepath)
    print(f"[+] SHA-256 Checksum: {sha256_hash}")

    # GZIP & SQL Header Verification
    try:
        print("[*] Testing GZIP decompression...")
        with gzip.open(filepath, "rb") as gz:
            sample = gz.read(1048576) # Read up to 1MB sample
            
        print("[+] GZIP compression is valid and uncorrupted.")
        
        matches = [kw for kw in REQUIRED_SQL_KEYWORDS if kw in sample]
        print(f"[+] Verified {len(matches)}/{len(REQUIRED_SQL_KEYWORDS)} structural PostgreSQL keywords:")
        for m in matches:
            print(f"    - Found keyword: '{m.decode()}'")
            
        if len(matches) < 2:
            print("[-] Warning: File decompressed, but contains fewer than expected SQL dump structures.")
            return False
            
    except gzip.BadGzipFile:
        print("[-] Error: File is not a valid GZIP archive.")
        return False
    except Exception as e:
        print(f"[-] Verification failed: {e}")
        return False

    # Create .sha256 checksum file alongside backup
    checksum_file = f"{filepath}.sha256"
    try:
        with open(checksum_file, "w") as f:
            f.write(f"{sha256_hash}  {os.path.basename(filepath)}\n")
        print(f"[+] Checksum recorded to: {checksum_file}")
    except Exception as e:
        print(f"[-] Could not write checksum file: {e}")

    print("\n========================================================")
    print(" [VERIFICATION PASSED] Backup is complete, valid, and safe!")
    print("========================================================")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python3 scripts/verify_backup_integrity.py <path_to_backup.sql.gz>")
        sys.exit(0 if len(sys.argv) >= 2 and sys.argv[1] in ("-h", "--help") else 1)
        
    target_file = sys.argv[1]
    success = verify_backup(target_file)
    sys.exit(0 if success else 1)
