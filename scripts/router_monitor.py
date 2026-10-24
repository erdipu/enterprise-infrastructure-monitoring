#!/usr/bin/env python3
"""
Enterprise Edge Monitoring Agent (Zero Dependency - standard library)
Pings local home infrastructure devices:
- Secondary Router: 192.168.1.2 (every 1s)
- Mobile Phone: 192.168.1.7 (every 2s)
- Mac Host: 192.168.1.3 (heartbeat stream every 2s)
Streams real-time UDP telemetry directly to Oracle Cloud VM 2 on UDP port 514.
"""

import time
import subprocess
import socket
import signal
import sys

CLOUD_VM_IP = "80.225.252.145"
CLOUD_VM_PORT = 514

ROUTER_IP = "192.168.1.2"
ROUTER_MAC = "d8:44:89:f5:41:fa"

MOBILE_IP = "192.168.1.7"
MOBILE_MAC = "2e:c3:63:01:b2:97"

MAC_IP = "192.168.1.3"
MAC_HARDWARE = "ac:29:3a:e7:8a:ec"

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def ping_host(ip: str):
    """Pings a local IP and returns (is_up: bool, latency_ms: float)"""
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

def send_udp_heartbeat(mac: str, ip: str, status: str, latency: float):
    msg = f"<14>EDGE_HEARTBEAT: mac={mac} ip={ip} status={status} latency={latency:.2f}ms\n"
    try:
        udp_sock.sendto(msg.encode("utf-8"), (CLOUD_VM_IP, CLOUD_VM_PORT))
    except Exception:
        pass

def handle_exit(signum, frame):
    try:
        udp_sock.sendto(b"<14>EDGE_HEARTBEAT: mac=" + ROUTER_MAC.encode() + b" status=PAUSED\n", (CLOUD_VM_IP, CLOUD_VM_PORT))
    except Exception:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    print(f"============================================================")
    print(f"[*] Enterprise Multi-Device Edge Monitoring Agent")
    print(f"[*] Targets: Router ({ROUTER_IP}), Mobile ({MOBILE_IP}), Mac ({MAC_IP})")
    print(f"[*] Cloud Ingestion: {CLOUD_VM_IP}:{CLOUD_VM_PORT} (UDP Syslog)")
    print(f"============================================================\n")

    cycle = 0

    while True:
        cycle += 1

        # 1. Probe Secondary Router (every 1s)
        router_up, router_lat = ping_host(ROUTER_IP)
        r_status = "UP" if router_up else "DOWN"
        send_udp_heartbeat(ROUTER_MAC, ROUTER_IP, r_status, router_lat)

        # 2. Probe Mobile Phone (every 2s)
        if cycle % 2 == 0:
            mobile_up, mobile_lat = ping_host(MOBILE_IP)
            m_status = "UP" if mobile_up else "DOWN"
            send_udp_heartbeat(MOBILE_MAC, MOBILE_IP, m_status, mobile_lat)
            if not mobile_up:
                print(f"[{time.strftime('%H:%M:%S')}] [!] Mobile {MOBILE_IP} is DOWN / Disconnected from Wi-Fi")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] [+] Mobile {MOBILE_IP} is ONLINE | Latency: {mobile_lat:.2f} ms")

        # 3. Stream Mac Host Heartbeat (every 2s)
        if cycle % 2 == 0:
            send_udp_heartbeat(MAC_HARDWARE, MAC_IP, "UP", 0.15)

        time.sleep(1)

if __name__ == "__main__":
    main()
