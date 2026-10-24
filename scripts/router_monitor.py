#!/usr/bin/env python3
"""
Enterprise Router Heartbeat Edge Agent (Zero Dependency - standard library)
Pings secondary TP-Link router (192.168.1.2) every 1 second and sends real-time UDP telemetry
directly to Oracle Cloud VM 2 on UDP port 514.
Provides sub-second power-off and recovery detection with zero network blockers.
"""

import time
import subprocess
import socket
import signal
import sys

ROUTER_IP = "192.168.1.2"
CLOUD_VM_IP = "80.225.252.145"
CLOUD_VM_PORT = 514
TARGET_NAME = "Secondary Router (TP-Link WR845N)"
POLL_INTERVAL_SECONDS = 1

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def ping_router(ip: str):
    """Pings the secondary router and returns (is_up: bool, latency_ms: float)"""
    try:
        cmd = ["ping", "-c", "1", "-W", "1000", ip]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "time=" in line:
                    parts = line.split("time=")[1].split()
                    latency = float(parts[0])
                    return True, latency
            return True, 0.55
        return False, 0.0
    except Exception:
        return False, 0.0

def send_udp_heartbeat(status: str, latency: float):
    msg = f"<14>EDGE_HEARTBEAT: mac=d8:44:89:f5:41:fa ip={ROUTER_IP} status={status} latency={latency:.2f}ms\n"
    try:
        udp_sock.sendto(msg.encode("utf-8"), (CLOUD_VM_IP, CLOUD_VM_PORT))
    except Exception:
        pass

def handle_exit(signum, frame):
    try:
        udp_sock.sendto(b"<14>EDGE_HEARTBEAT: mac=d8:44:89:f5:41:fa status=PAUSED\n", (CLOUD_VM_IP, CLOUD_VM_PORT))
    except Exception:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    print(f"============================================================")
    print(f"[*] Enterprise Secondary Router Edge Agent (TL-WR845N)")
    print(f"[*] Target IP: {ROUTER_IP}")
    print(f"[*] Cloud Ingestion: {CLOUD_VM_IP}:{CLOUD_VM_PORT} (UDP Syslog)")
    print(f"[*] Poll Interval: {POLL_INTERVAL_SECONDS}s")
    print(f"============================================================\n")

    consecutive_failures = 0

    while True:
        is_up, latency_ms = ping_router(ROUTER_IP)
        status = "UP" if is_up else "DOWN"

        if not is_up:
            consecutive_failures += 1
            print(f"[{time.strftime('%H:%M:%S')}] [!] OUTAGE: Router {ROUTER_IP} is DOWN! (Failure count: {consecutive_failures})")
        else:
            if consecutive_failures > 0:
                print(f"[{time.strftime('%H:%M:%S')}] [✓] RECOVERED: Router {ROUTER_IP} is back UP!")
            consecutive_failures = 0
            print(f"[{time.strftime('%H:%M:%S')}] [+] Router {ROUTER_IP} is HEALTHY | Latency: {latency_ms:.2f} ms")

        send_udp_heartbeat(status, latency_ms)
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
