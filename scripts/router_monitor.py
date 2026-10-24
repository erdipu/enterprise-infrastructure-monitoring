#!/usr/bin/env python3
"""
Enterprise Dynamic Multi-Device Edge Monitoring Agent (Parallel Threaded Engine)
Architectural Guarantees:
1. Dedicated 1-second pulse for Secondary Router (192.168.1.2) - never blocked by other devices.
2. Dedicated 2-second heartbeat for Mac Prober Host (192.168.1.3).
3. Concurrent asynchronous prober for dynamic LAN targets (Mobile, etc.) with fast timeouts.
4. Continuous dynamic sync with Cloud NOC API.
5. UDP Telemetry directly streamed to Oracle Cloud VM 2 (UDP 514).
"""

import time
import subprocess
import socket
import urllib.request
import json
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

CLOUD_VM_IP = "80.225.252.145"
CLOUD_VM_PORT = 514
API_SERVERS_URL = f"http://{CLOUD_VM_IP}:8090/api/v1/servers/"
API_TARGETS_URL = f"http://{CLOUD_VM_IP}:8090/api/v1/targets/"

ROUTER_IP = "192.168.1.2"
ROUTER_MAC = "d8:44:89:f5:41:fa"
MAC_IP = "192.168.1.3"
MAC_HARDWARE = "ac:29:3a:e7:8a:ec"

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Dynamic target registry for secondary devices (excluding router and Mac host)
inventory_devices = {
    "192.168.1.5": {"name": "Mobile Phone", "last_status": "UP", "last_lat": 3.0}
}
lock = threading.Lock()
running = True

def is_local_ip(ip_str: str) -> bool:
    """Checks if an IP belongs to local RFC1918 subnet."""
    ip = ip_str.strip()
    return (
        ip.startswith("192.168.") or
        ip.startswith("10.") or
        (ip.startswith("172.") and len(ip.split(".")) > 1 and 16 <= int(ip.split(".")[1]) <= 31)
    )

def send_udp_heartbeat(ip: str, status: str, latency: float, mac: str = ""):
    """Streams UDP heartbeat packet to Oracle Cloud VM 2 on UDP port 514."""
    mac_tag = f"mac={mac} " if mac else ""
    msg = f"<14>EDGE_HEARTBEAT: {mac_tag}ip={ip} status={status} latency={latency:.2f}ms\n"
    try:
        udp_sock.sendto(msg.encode("utf-8"), (CLOUD_VM_IP, CLOUD_VM_PORT))
    except Exception:
        pass

# ==============================================================================
# Worker 1: Dedicated Router Pulse Worker (1-Second Strict Cadence)
# ==============================================================================
def router_pulse_worker():
    """
    Independent dedicated thread that probes 192.168.1.2 every 1 second.
    Completely isolated so that slow or offline devices never delay router telemetry.
    """
    print("[*] Router Pulse Worker active (1s cadence)")
    while running:
        t0 = time.time()
        try:
            res = subprocess.run(["ping", "-c", "1", "-W", "800", ROUTER_IP], capture_output=True, text=True, timeout=1.2)
            if res.returncode == 0:
                lat = 0.85
                for line in res.stdout.splitlines():
                    if "time=" in line:
                        parts = line.split("time=")[1].split()
                        lat = float(parts[0])
                        break
                send_udp_heartbeat(ROUTER_IP, "UP", lat, mac=ROUTER_MAC)
            else:
                send_udp_heartbeat(ROUTER_IP, "DOWN", 0.0, mac=ROUTER_MAC)
        except Exception:
            send_udp_heartbeat(ROUTER_IP, "DOWN", 0.0, mac=ROUTER_MAC)

        elapsed = time.time() - t0
        sleep_dur = max(0.1, 1.0 - elapsed)
        time.sleep(sleep_dur)

# ==============================================================================
# Worker 2: Dedicated Mac Host Worker (2-Second Cadence)
# ==============================================================================
def mac_host_worker():
    print("[*] Mac Host Heartbeat Worker active (2s cadence)")
    while running:
        send_udp_heartbeat(MAC_IP, "UP", 0.15, mac=MAC_HARDWARE)
        time.sleep(2)

# ==============================================================================
# Worker 3: Dynamic Cloud API Discovery Worker
# ==============================================================================
def api_discovery_worker():
    print("[*] Cloud API Target Discovery Worker active (10s cadence)")
    while running:
        try:
            new_ips = {}
            # 1. Fetch Servers from NOC
            req = urllib.request.Request(API_SERVERS_URL, headers={"User-Agent": "EdgeProber/2.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    servers = json.loads(resp.read().decode())
                    for s in servers:
                        ip = (s.get("ip_address") or "").strip()
                        if ip and is_local_ip(ip) and ip not in [ROUTER_IP, MAC_IP, "192.168.1.7"]:
                            new_ips[ip] = s.get("hostname", ip)

            # 2. Fetch Targets from NOC
            req2 = urllib.request.Request(API_TARGETS_URL, headers={"User-Agent": "EdgeProber/2.0"})
            with urllib.request.urlopen(req2, timeout=3) as resp:
                if resp.status == 200:
                    targets = json.loads(resp.read().decode())
                    for t in targets:
                        host = (t.get("url_or_host") or "").strip()
                        if host.startswith("http://") or host.startswith("https://"):
                            host = host.split("//")[1].split("/")[0].split(":")[0]
                        if host and is_local_ip(host) and host not in [ROUTER_IP, MAC_IP, "192.168.1.7"]:
                            new_ips[host] = t.get("name", host)

            with lock:
                # Add any newly discovered devices
                for ip, name in new_ips.items():
                    if ip not in inventory_devices:
                        print(f"[{time.strftime('%H:%M:%S')}] [+] Discovered new local target: {name} ({ip})")
                        inventory_devices[ip] = {"name": name, "last_status": "UP", "last_lat": 1.0}
                    else:
                        inventory_devices[ip]["name"] = name
        except Exception:
            pass
        time.sleep(10)

# ==============================================================================
# Worker 4: Concurrent Multi-Device Prober Worker (Mobile & Dynamic LAN Hosts)
# ==============================================================================
def probe_single_device(ip: str):
    """Multi-protocol check for a single dynamic LAN host with fast timeouts."""
    # 1. Quick ICMP ping (1 packet, 800ms timeout)
    try:
        res = subprocess.run(["ping", "-c", "1", "-W", "800", ip], capture_output=True, text=True, timeout=1.0)
        if res.returncode == 0:
            lat = 3.0
            for line in res.stdout.splitlines():
                if "time=" in line:
                    parts = line.split("time=")[1].split()
                    lat = float(parts[0])
                    break
            return True, lat
    except Exception:
        pass

    # 2. TCP Port connect fallback (80, 443, 62078)
    for p in [80, 443, 62078]:
        try:
            t0 = time.time()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            res = s.connect_ex((ip, p))
            s.close()
            if res == 0:
                elapsed = (time.time() - t0) * 1000.0
                return True, round(elapsed, 2)
        except Exception:
            continue

    # 3. ARP cache fallback
    try:
        res = subprocess.run(["arp", "-n", ip], capture_output=True, text=True, timeout=0.5)
        out = res.stdout.lower()
        if "no entry" not in out and "incomplete" not in out and "(" in out:
            return True, 5.0
    except Exception:
        pass

    return False, 0.0

def inventory_probe_worker():
    print("[*] Dynamic Inventory Prober Worker active (2s cadence)")
    executor = ThreadPoolExecutor(max_workers=4)

    while running:
        with lock:
            devices_to_probe = dict(inventory_devices)

        if devices_to_probe:
            futures = {executor.submit(probe_single_device, ip): (ip, info) for ip, info in devices_to_probe.items()}
            for f in futures:
                ip, info = futures[f]
                try:
                    is_up, lat = f.result(timeout=1.5)
                    st = "UP" if is_up else "DOWN"
                    old_st = info.get("last_status")
                    if old_st != st:
                        print(f"[{time.strftime('%H:%M:%S')}] [!] State Change: {info['name']} ({ip}) -> {st} ({lat:.1f} ms)")
                        info["last_status"] = st
                    info["last_lat"] = lat
                    send_udp_heartbeat(ip, st, lat)
                except Exception:
                    send_udp_heartbeat(ip, "DOWN", 0.0)

        time.sleep(2)

def handle_exit(signum, frame):
    global running
    running = False
    try:
        udp_sock.sendto(b"<14>EDGE_HEARTBEAT: mac=" + ROUTER_MAC.encode() + b" status=PAUSED\n", (CLOUD_VM_IP, CLOUD_VM_PORT))
    except Exception:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    print("============================================================")
    print("[*] Enterprise Parallel Dynamic Edge Monitoring Agent")
    print(f"[*] Cloud Ingestion: {CLOUD_VM_IP}:{CLOUD_VM_PORT} (UDP Syslog)")
    print("============================================================\n")

    t1 = threading.Thread(target=router_pulse_worker, daemon=True)
    t2 = threading.Thread(target=mac_host_worker, daemon=True)
    t3 = threading.Thread(target=api_discovery_worker, daemon=True)
    t4 = threading.Thread(target=inventory_probe_worker, daemon=True)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    while running:
        time.sleep(1)

if __name__ == "__main__":
    main()
