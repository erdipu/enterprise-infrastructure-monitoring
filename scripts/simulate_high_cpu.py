#!/usr/bin/env python3
"""
Simulate Safe High CPU Utilization
Target: Safely stresses CPU cores for a specified duration to trigger Prometheus Alert rules:
  - HostCpuUtilizationWarning (>80% P2)
  - HostCpuUtilizationCritical (>90% P1)
Safe & Reversible: Automatically stops after duration or on Ctrl+C.
"""

import sys
import time
import math
import argparse
from multiprocessing import Pool, cpu_count

def cpu_stress_worker(duration_sec):
    end_time = time.time() + duration_sec
    while time.time() < end_time:
        _ = math.sqrt(math.factorial(250))

def main():
    parser = argparse.ArgumentParser(description="Safely generate CPU load for monitoring demonstration")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds (default: 30)")
    parser.add_argument("--cores", type=int, default=0, help="Number of cores to stress (0 = all cores)")
    args = parser.parse_args()

    cores = args.cores if args.cores > 0 else cpu_count()
    print(f"[*] Starting safe CPU simulation on {cores} cores for {args.duration} seconds...")
    print("    Press Ctrl+C anytime to terminate load early.")

    try:
        with Pool(processes=cores) as pool:
            pool.map(cpu_stress_worker, [args.duration] * cores)
        print("[+] CPU simulation completed successfully. System returned to baseline load.")
    except KeyboardInterrupt:
        print("\n[!] User interrupted: Terminated CPU stress workers immediately. Baseline restored.")

if __name__ == "__main__":
    main()
