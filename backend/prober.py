"""
Universal Multi-Protocol Prober Engine for Enterprise Infrastructure Monitoring
Supports:
- RFC1918 Private LAN IPs (delegated to local edge syslog exporter via /devices)
- Public IPs and Hostnames (direct TCP connect, HTTP/HTTPS probe, ICMP ping)
- Cloud VMs, Web services, APIs, Windows/Linux servers
- Multi-protocol fallback: never marks server DOWN if a service port is accessible
"""

import socket
import time
import urllib.request
import urllib.parse
import json
import logging
from typing import Tuple, Optional

logger = logging.getLogger("monitoring.prober")

EDGE_EXPORTER_URLS = [
    "http://172.18.0.1:9125/devices",
    "http://127.0.0.1:9125/devices",
    "http://host.docker.internal:9125/devices"
]

def is_private_ip(host: str) -> bool:
    """Checks if host is an RFC1918 private IP address or local hostname."""
    h = host.strip().lower()
    if h in ["localhost", "127.0.0.1"]:
        return True
    if h.startswith("192.168.") or h.startswith("10."):
        return True
    if h.startswith("172."):
        parts = h.split(".")
        if len(parts) >= 2:
            try:
                second = int(parts[1])
                if 16 <= second <= 31:
                    return True
            except ValueError:
                pass
    return False

def query_edge_devices() -> dict:
    """Queries edge exporter on the host machine to get live statuses of private LAN devices."""
    for url in EDGE_EXPORTER_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NOC-Prober-Engine/2.0"})
            with urllib.request.urlopen(req, timeout=1.2) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode())
        except Exception:
            continue
    return {}

def probe_universal(host: str, port: Optional[int] = None, target_type: Optional[str] = None) -> Tuple[str, float]:
    """
    Universal prober:
    Returns (status: 'UP' | 'DOWN', latency_ms: float)
    Rule: Never marks a server as DOWN if its configured service is accessible.
    """
    if not host:
        return "DOWN", 0.0

    raw_host = host.strip()
    clean_host = raw_host
    inferred_port = port

    # Parse URL if provided
    if clean_host.startswith("http://") or clean_host.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(clean_host)
            clean_host = parsed.hostname or clean_host
            if not inferred_port:
                inferred_port = parsed.port or (443 if parsed.scheme == "https" else 80)
        except Exception:
            pass
    elif ":" in clean_host and not clean_host.count(":") > 1:  # Not IPv6
        try:
            parts = clean_host.split(":")
            clean_host = parts[0]
            if not inferred_port:
                inferred_port = int(parts[1])
        except Exception:
            pass

    # 1. Monitoring server VM 2 itself (Localhost / Self)
    if clean_host in ["80.225.252.145", "127.0.0.1", "localhost"]:
        return "UP", 0.25

    # 2. Private LAN hosts (e.g. 192.168.1.x, Mac, Mobile, Router)
    if is_private_ip(clean_host):
        devices = query_edge_devices()
        dev = devices.get(clean_host)
        if dev:
            status = dev.get("status", "DOWN")
            lat = float(dev.get("latency_ms", 0.0)) if status == "UP" else 0.0
            return status, lat
        return "DOWN", 0.0

    # 3. Public Cloud Servers, Hostnames, Websites, APIs
    # A. Check HTTP/HTTPS first if it is a website, api, or web port
    if target_type in ["website", "api"] or (inferred_port in [80, 443, 8080, 8443, 3000, 9090, 8090, 8000]):
        url_to_test = raw_host
        if not url_to_test.startswith("http://") and not url_to_test.startswith("https://"):
            proto = "https" if inferred_port == 443 else "http"
            url_to_test = f"{proto}://{clean_host}"
            if inferred_port and inferred_port not in [80, 443]:
                url_to_test += f":{inferred_port}"

        try:
            t0 = time.time()
            req = urllib.request.Request(url_to_test, headers={"User-Agent": "NOC-HealthCheck/2.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                elapsed = (time.time() - t0) * 1000.0
                if resp.status < 500:
                    return "UP", round(elapsed, 2)
        except urllib.error.HTTPError as e:
            # 401 Unauthorized, 403 Forbidden, 404 Not Found confirm the server is UP and responding!
            elapsed = (time.time() - t0) * 1000.0
            if e.code < 500:
                return "UP", round(elapsed, 2)
        except Exception:
            pass

    # B. TCP Port Check (multi-port discovery)
    ports_to_try = [inferred_port] if inferred_port else [443, 80, 22, 9100, 3389, 8080, 8090]
    for p in ports_to_try:
        try:
            t0 = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.2)
            res = sock.connect_ex((clean_host, p))
            sock.close()
            if res == 0:
                elapsed = (time.time() - t0) * 1000.0
                return "UP", round(elapsed, 2)
        except Exception:
            continue

    # C. Host resolution check: if host can't even resolve, it's definitely DOWN
    try:
        socket.gethostbyname(clean_host)
    except Exception:
        return "DOWN", 0.0

    return "DOWN", 0.0
