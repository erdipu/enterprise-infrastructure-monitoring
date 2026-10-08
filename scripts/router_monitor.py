#!/usr/bin/env python3
"""
Enterprise Router Heartbeat Agent (Zero Dependency - uses Python standard library)
Pings secondary TP-Link router (192.168.1.7) and sends live telemetry to the Cloud Monitoring Platform.
If the LAN cable is disconnected or the router loses power, triggers an immediate P1 alert and email.
"""

import time
import subprocess
import json
import urllib.request
import urllib.error
import sys

ROUTER_IP = "192.168.1.7"
CLOUD_HEARTBEAT_URL = "http://deepak-monitoring.duckdns.org:8090/api/v1/targets/heartbeat"
TARGET_NAME = "TP-Link Access Point WR845N (Deepak_2112)"
POLL_INTERVAL_SECONDS = 15

def ping_router(ip: str):
    """Pings the secondary router and returns (is_up: bool, latency_ms: float)"""
    try:
        # Send 1 ICMP ping packet with a 1-second timeout
        cmd = ["ping", "-c", "1", "-W", "1000", ip]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "time=" in line:
                    parts = line.split("time=")[1].split()
                    latency = float(parts[0])
                    return True, latency
            return True, 1.0
        return False, 0.0
    except Exception:
        return False, 0.0

def send_heartbeat(status: str, latency: float):
    payload = json.dumps({
        "target_name": TARGET_NAME,
        "status": status,
        "response_time_ms": latency
    }).encode("utf-8")

    req = urllib.request.Request(
        CLOUD_HEARTBEAT_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return response.status

def main():
    print(f"============================================================")
    print(f"[*] Enterprise Secondary Router Monitor (TL-WR845N)")
    print(f"[*] Target IP: {ROUTER_IP}")
    print(f"[*] Cloud Ingestion: {CLOUD_HEARTBEAT_URL}")
    print(f"[*] Press Ctrl+C to terminate.")
    print(f"============================================================\n")

    consecutive_failures = 0

    while True:
        is_up, latency_ms = ping_router(ROUTER_IP)
        status = "UP" if is_up else "DOWN"

        if not is_up:
            consecutive_failures += 1
            print(f"[!] OUTAGE DETECTED: TP-Link Router {ROUTER_IP} is DOWN! (Failure: {consecutive_failures})")
        else:
            consecutive_failures = 0
            print(f"[+] TP-Link Router {ROUTER_IP} is HEALTHY | Latency: {latency_ms:.2f} ms")

        try:
            code = send_heartbeat(status, latency_ms)
            if code == 200:
                print(f"    └── Cloud Heartbeat synced successfully.")
        except Exception as e:
            print(f"    └── [!] Warning syncing with cloud: {e}")

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
