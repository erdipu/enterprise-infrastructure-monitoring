#!/usr/bin/env python3
"""
Simulate Safe High Memory Utilization
Target: Safely allocates controlled RAM blocks to trigger Prometheus Alert rules:
  - HostMemoryUtilizationWarning (>85% P2)
  - HostMemoryUtilizationCritical (>92% P1)
Safe & Reversible: Automatically releases RAM after timeout or on Ctrl+C.
"""

import sys
import time
import argparse

def main():
    parser = argparse.ArgumentParser(description="Safely generate controlled memory usage")
    parser.add_argument("--megabytes", type=int, default=500, help="Megabytes of RAM to allocate (default: 500)")
    parser.add_argument("--hold_sec", type=int, default=20, help="Hold duration in seconds (default: 20)")
    args = parser.parse_args()

    print(f"[*] Allocating {args.megabytes} MB of memory in RAM...")
    print(f"[*] Will hold memory for {args.hold_sec} seconds before releasing...")

    try:
        # Allocate bytes in memory (1MB = 1024 * 1024 bytes)
        block = bytearray(args.megabytes * 1024 * 1024)
        for i in range(0, len(block), 4096):
            block[i] = 1  # Touch each page to force resident allocation

        print(f"[+] Memory allocated successfully ({args.megabytes} MB). Holding allocation...")
        for remaining in range(args.hold_sec, 0, -1):
            sys.stdout.write(f"\r    Remaining hold time: {remaining}s ")
            sys.stdout.flush()
            time.sleep(1)

        print("\n[*] Releasing allocated memory...")
        del block
        print("[+] Memory cleanly released and returned to OS. Baseline restored.")

    except KeyboardInterrupt:
        print("\n[!] User interrupted: Released memory immediately.")
    except MemoryError:
        print("\n[!] Memory limit reached safely: Stopping allocation to protect host.")

if __name__ == "__main__":
    main()
