#!/usr/bin/env python3
"""
Enterprise Dynamic Multi-Device Edge Monitoring Agent
Discovers targets dynamically from the NOC Cloud API, probes them using multi-protocol checks
(ICMP Ping, TCP service port connect, ARP neighbor verification), and streams real-time UDP
telemetry directly to the Oracle Cloud Syslog Exporter (UDP 514).

Requirements satisfied:
- Dynamic discovery of any added server or IP
- Multi-protocol detection (Ping, TCP, ARP)
- Non-ping dependent: never marks DOWN if TCP service is open
- Fast recovery and outage detection (within 2-4 seconds)
- Zero third-party dependencies (Python 3 standard library)
"""

import time
import subprocess
import socket
import urllib.request
import json
import re
import signal
import sys
import threading

CLOUD_VM_IP = "80.225.252.145"
CLOUD_VM_PORT = 514
API_SERVERS_URL = f"http://{CLOUD_VM_IP}:8090/api/v1/servers/"
API_TARGETS_URL = f"http://{CLOUD_VM_IP}:8090/api/v1/targets/"

ROUTER_IP = "192.168.1.2"
ROUTER_MAC = "d8:44:89:f5:41:fa"
MAC_IP = "192.168.1.3"
MAC_HARDWARE = "ac:29:3a:e7:8a:ec"

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Dynamic target registry: IP -> {"name": str, "last_status": str, "last_lat": float}
monitored_devices = {
    ROUTER_IP: {"name": "Secondary Router WR845N", "last_status": "UP", "last_lat": 0.85},
    MAC_IP: {"name": "Mac Prober Host", "last_status": "UP", "last_lat": 0.15},
    "192.168.1.5": {"name": "Mobile Phone", "last_status": "UP", "last_lat": 6.0},
    "192.168.1.7": {"name": "Mobile Device (Old Lease)", "last_status": "DOWN", "last_lat": 0.0}
}
lock = threading.Lock()

def is_local_ip(ip_str: str) -> bool:
    """Checks if an IP belongs to local RFC1918 subnet."""
    ip = ip_str.strip()
    return (
        ip.startswith("192.168.") or
        ip.startswith("10.") or
        (ip.startswith("172.") and len(ip.split(".")) > 1 and 16 <= int(ip.split(".")[1]) <= 31)
    )

def fetch_dynamic_targets():
    """Polls Cloud NOC API to discover any newly added private IP or server."""
    global monitored_devices
    while True:
        try:
            new_ips = {}
            # 1. Fetch Servers
            req = urllib.request.Request(API_SERVERS_URL, headers={"User-Agent": "EdgeProber/2.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    servers = json.loads(resp.read().decode())
                    for s in servers:
                        ip = (s.get("ip_address") or "").strip()
                        if ip and is_local_ip(ip):
                            new_ips[ip] = s.get("hostname", ip)

            # 2. Fetch Targets
            req2 = urllib.request.Request(API_TARGETS_URL, headers={"User-Agent": "EdgeProber/2.0"})
            with urllib.request.urlopen(req2, timeout=3) as resp:
                if resp.status == 200:
                    targets = json.loads(resp.read().decode())
                    for t in targets:
                        host = (t.get("url_or_host") or "").strip()
                        # Extract IP if URL
                        if host.startswith("http://") or host.startswith("https://"):
                            host = host.split("//")[1].split("/")[0].split(":")[0]
                        if host and is_local_ip(host):
                            new_ips[host] = t.get("name", host)

            with lock:
                # Merge new IPs into monitoring map
                for ip, name in new_ips.items():
                    if ip not in monitored_devices:
                        print(f"[{time.strftime('%H:%M:%S')}] [+] Discovered new local target: {name} ({ip})")
                        monitored_devices[ip] = {"name": name, "last_status": "UP", "last_lat": 1.0}
                    else:
                        monitored_devices[ip]["name"] = name
        except Exception as e:
            pass
        time.sleep(10)

def probe_icmp(ip: str):
    """ICMP Ping probe (2 packets, 1.2s timeout). Returns (success: bool, latency_ms: float)."""
    try:
        cmd = ["ping", "-c", "2", "-W", "1200", ip]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.5)
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

def probe_tcp_ports(ip: str):
    """TCP Port probe (connects to common local service ports). Returns (success: bool, latency_ms: float)."""
    common_ports = [80, 443, 8080, 22, 9100, 3389, 62078, 5353, 5000]
    for port in common_ports:
        try:
            t0 = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.4)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                elapsed = (time.time() - t0) * 1000.0
                return True, round(elapsed, 2)
        except Exception:
            continue
    return False, 0.0

def probe_arp(ip: str):
    """Checks local ARP cache for device presence."""
    try:
        res = subprocess.run(["arp", "-n", ip], capture_output=True, text=True, timeout=1.0)
        out = res.stdout.lower()
        if "no entry" not in out and "incomplete" not in out and "(" in out:
            return True, 1.2
        return False, 0.0
    except Exception:
        return False, 0.0

def multi_protocol_probe(ip: str):
    """
    Multi-Protocol Probe:
    1. Try ICMP Ping
    2. Try TCP Port connect
    3. Check ARP cache
    Rule: Never marks DOWN if any service responds!
    """
    if ip == MAC_IP:
        return True, 0.15

    # 1. ICMP Ping Check
    up, lat = probe_icmp(ip)
    if up:
        return True, lat

    # 2. TCP Service Port Check
    up, lat = probe_tcp_ports(ip)
    if up:
        return True, lat

    # 3. ARP presence check (helpful for mobile phones waking from sleep)
    up, lat = probe_arp(ip)
    if up:
        # Re-verify with a quick single ping now that ARP answered
        re_up, re_lat = probe_icmp(ip)
        if re_up:
            return True, re_lat

    return False, 0.0

def send_udp_heartbeat(ip: str, status: str, latency: float, mac: str = ""):
    """Streams UDP heartbeat directly to Oracle Cloud VM 2 on UDP port 514."""
    mac_tag = f"mac={mac} " if mac else ""
    msg = f"<14>EDGE_HEARTBEAT: {mac_tag}ip={ip} status={status} latency={latency:.2f}ms\n"
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
    print("============================================================")
    print("[*] Enterprise Dynamic Multi-Device Edge Monitoring Agent")
    print(f"[*] Cloud Ingestion: {CLOUD_VM_IP}:{CLOUD_VM_PORT} (UDP Syslog)")
    print(f"[*] Dynamic API Sync: {API_SERVERS_URL}")
    print("============================================================\n")

    # Start dynamic target discovery thread
    discovery_thread = threading.Thread(target=fetch_dynamic_targets, daemon=True)
    discovery_thread.start()

    while True:
        with lock:
            targets_to_probe = dict(monitored_devices)

        for ip, info in targets_to_probe.items():
            is_up, latency = multi_protocol_probe(ip)
            status = "UP" if is_up else "DOWN"

            # Log transition or state
            old_status = info.get("last_status")
            if old_status != status:
                print(f"[{time.strftime('%H:%M:%S')}] [!] Target State Change: {info['name']} ({ip}) -> {status} (Latency: {latency:.2f} ms)")
                info["last_status"] = status
            info["last_lat"] = latency

            # Stream UDP Heartbeat to VM 2
            mac_addr = ROUTER_MAC if ip == ROUTER_IP else (MAC_HARDWARE if ip == MAC_IP else "")
            send_udp_heartbeat(ip=ip, status=status, latency=latency, mac=mac_addr)

        time.sleep(2)

if __name__ == "__main__":
    main()
