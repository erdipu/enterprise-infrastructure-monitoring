#!/usr/bin/env python3
"""
Simulate Safe Filesystem Disk Utilization
Target: Creates a temporary dummy file to trigger Prometheus Alert rules:
  - HostDiskUtilizationWarning (>85% P2)
  - HostDiskUtilizationCritical (>95% P1)
Safe & Reversible: Writes to a temporary path and automatically purges the file.
"""

import os
import sys
import time
import argparse
import tempfile

def main():
    parser = argparse.ArgumentParser(description="Safely generate disk space consumption")
    parser.add_argument("--size_mb", type=int, default=200, help="Size of temporary dummy file in MB (default: 200)")
    parser.add_argument("--hold_sec", type=int, default=15, help="Seconds to hold file before automatic deletion (default: 15)")
    args = parser.parse_args()

    temp_dir = tempfile.gettempdir()
    dummy_file = os.path.join(temp_dir, "eim_disk_stress_test.tmp")

    print(f"[*] Creating temporary dummy file ({args.size_mb} MB) at {dummy_file}...")
    try:
        # Write sparse/dummy data in 1MB chunks
        chunk = b"X" * (1024 * 1024)
        with open(dummy_file, "wb") as f:
            for _ in range(args.size_mb):
                f.write(chunk)

        print(f"[+] Dummy file created successfully ({args.size_mb} MB).")
        print(f"[*] Holding file for {args.hold_sec} seconds to simulate sustained filesystem usage...")

        for remaining in range(args.hold_sec, 0, -1):
            sys.stdout.write(f"\r    Remaining hold time: {remaining}s ")
            sys.stdout.flush()
            time.sleep(1)

        print("\n[*] Deleting temporary test file...")
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
        print("[+] File removed cleanly. Storage returned to baseline.")

    except KeyboardInterrupt:
        print("\n[!] User interrupted: Removing test file immediately...")
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
        print("[+] Test file removed.")
    except Exception as e:
        print(f"\n[!] Error during disk simulation: {e}")
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

if __name__ == "__main__":
    main()
