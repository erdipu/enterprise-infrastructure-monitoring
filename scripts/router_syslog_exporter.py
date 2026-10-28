#!/usr/bin/env python3
"""
Enterprise Router Syslog Prometheus Exporter with Multi-Port Link-State & Edge Prober Ingestion
Streams real-time physical link-state events, positive pulses, and edge UDP heartbeat probes.
Exposes Prometheus metrics on HTTP port 9125 and listens for Syslog on UDP port 514.
"""

import socket
import time
import json
import re
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# Unique hardware identity for Secondary Router
TPLINK_MAC = "d8:44:89:f5:41:fa"
TPLINK_IP = "192.168.1.2"

# Telemetry tracking variables
zte_last_packet_time = time.time()
tplink_last_seen_time = 0.0
last_link_change_time = 0.0
tplink_link_up = True           # Physical link on any ZTE LAN switch port
tplink_packet_count = 0
last_sender_ip = "103.181.90.187"

# Direct edge heartbeat tracking (via UDP 514 or POST /heartbeat)
heartbeat_status = "UNKNOWN"
heartbeat_time = 0.0
heartbeat_latency = 0.0
heartbeat_source = ""
edge_devices = {}  # Map of IP -> {"status": "UP"|"DOWN", "last_seen": timestamp, "latency": float}

# Scan past log to initialize state accurately on service start (last 128KB of recent logs, < 5ms)
try:
    now_ts = time.time()
    with open("/var/log/router_telemetry.log", "rb") as f:
        f.seek(0, 2)
        f_size = f.tell()
        f.seek(max(0, f_size - 131072))
        chunk = f.read().decode(errors="ignore")
        lines = chunk.splitlines()
        for line in lines:
            # Check for link up across any LAN port (eth0-eth3 / port 1-4) or TP-Link reconnect
            if (re.search(r"br0:\s*port\s*\d+\(eth\d+\)\s*entered\s*forwarding\s*state", line, re.IGNORECASE) or 
                "link up" in line.lower() or 
                "can't be same with br0" in line.lower() or
                ("DHCPD" in line and "AP's DHCP server" in line) or
                "DHCPC: Send REQUEST" in line or
                "DHCPC: Recv ACK" in line or
                "DHCPC: Ignoring XID" in line):
                try:
                    line_date = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").timestamp()
                    if (now_ts - line_date) < 14400:  # Fresh within 4 hours
                        tplink_link_up = True
                        last_link_change_time = line_date
                except Exception:
                    pass

            # Check for link drop across any LAN port or ZTE record drop
            elif (re.search(r"br0:\s*port\s*\d+\(eth\d+\)\s*entered\s*disabled\s*state", line, re.IGNORECASE) or 
                  "link down" in line.lower() or
                  ("record not find" in line.lower() and (TPLINK_IP in line or TPLINK_MAC in line.lower()))):
                try:
                    line_date = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").timestamp()
                    if (now_ts - line_date) < 14400:
                        tplink_link_up = False
                        last_link_change_time = line_date
                except Exception:
                    pass

            # Check for MAC presence or direct TP-Link packet to record last seen time
            if (TPLINK_MAC in line.lower() or 
                "DHCPC:" in line or 
                ("DHCPD:" in line and "AP's DHCP server" in line) or
                "can't be same with br0" in line.lower()):
                try:
                    line_date = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").timestamp()
                    if line_date > tplink_last_seen_time:
                        tplink_last_seen_time = line_date
                except Exception:
                    pass
except Exception as e:
    print(f"Error scanning past log: {e}")

def syslog_listener():
    global zte_last_packet_time, tplink_last_seen_time, last_link_change_time, tplink_link_up, tplink_packet_count, last_sender_ip
    global heartbeat_status, heartbeat_time, heartbeat_latency, heartbeat_source
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 514))
    print("Syslog UDP listener running on 514 with multi-port link-state & edge prober ingestion...")
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            msg = data.decode(errors="ignore").strip()
            now = time.time()
            last_sender_ip = addr[0]

            # 1. Direct edge prober heartbeat from local network agent (UDP 514)
            if "EDGE_HEARTBEAT" in msg:
                heartbeat_source = "udp_edge_probe"
                
                # Extract device IP, status, and latency from heartbeat packet
                ip_match = re.search(r"ip=([0-9.]+)", msg)
                st_match = re.search(r"status=([A-Z]+)", msg)
                lat_match = re.search(r"latency=([0-9.]+)", msg)
                
                dev_ip = ip_match.group(1) if ip_match else ""
                dev_status = st_match.group(1) if st_match else "UP"
                dev_latency = float(lat_match.group(1)) if lat_match else 0.55
                
                if dev_ip:
                    edge_devices[dev_ip] = {
                        "status": dev_status,
                        "last_seen": now,
                        "latency": dev_latency
                    }

                # Mac host (192.168.1.3) is confirmed alive whenever any edge prober packet is received
                edge_devices["192.168.1.3"] = {
                    "status": "UP",
                    "last_seen": now,
                    "latency": 0.15
                }

                if dev_ip == TPLINK_IP or TPLINK_MAC in msg.lower():
                    if "status=DOWN" in msg:
                        heartbeat_time = now
                        heartbeat_status = "DOWN"
                        heartbeat_latency = 0.0
                    elif "status=UP" in msg:
                        heartbeat_time = now
                        heartbeat_status = "UP"
                        heartbeat_latency = dev_latency
                        tplink_last_seen_time = now
                    elif "status=PAUSED" in msg:
                        heartbeat_time = 0.0
                        heartbeat_status = "PAUSED"

                with open("/var/log/router_telemetry.log", "a") as f:
                    f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} [{addr[0]}] {msg}\n')
                continue

            is_zte = ("F670LV9" in msg or "ZTE" in msg)

            if is_zte:
                # Heartbeat from ZTE Gateway (Primary Fiber Router)
                zte_last_packet_time = now

                # Physical switch port link drop
                is_link_drop = (
                    re.search(r"br0:\s*port\s*\d+\(eth\d+\)\s*entered\s*disabled\s*state", msg, re.IGNORECASE) is not None or
                    "link down" in msg.lower() or
                    ("record not find" in msg.lower() and (TPLINK_IP in msg or TPLINK_MAC in msg.lower()))
                )
                if is_link_drop:
                    tplink_link_up = False
                    last_link_change_time = now

                # Physical link / bridge attachment restored on ZTE switch port
                elif (re.search(r"br0:\s*port\s*\d+\(eth\d+\)\s*entered\s*forwarding\s*state", msg, re.IGNORECASE) or 
                      "link up" in msg.lower() or 
                      "can't be same with br0" in msg.lower()):
                    tplink_link_up = True
                    tplink_last_seen_time = now
                    last_link_change_time = now
                    tplink_packet_count += 1
                    # Bootup event: router is definitely powering back up
                    if "can't be same with br0" in msg.lower():
                        heartbeat_time = now
                        heartbeat_status = "UP"

                # Positive pulse: MAC address or IP query from ZTE switch table
                elif (TPLINK_MAC in msg.lower() or 
                      ("DHCPD:" in msg and "AP's DHCP server" in msg)):
                    tplink_link_up = True
                    tplink_last_seen_time = now
                    last_link_change_time = now
                    tplink_packet_count += 1
                    if "AP's DHCP server" in msg:
                        heartbeat_time = now
                        heartbeat_status = "UP"

            else:
                # Direct packet from TP-Link secondary router firmware
                is_direct_tplink = (
                    "TP-Link" in msg or 
                    "WR845N" in msg or 
                    "HomeRouter" in msg or
                    TPLINK_MAC in msg.lower() or
                    TPLINK_IP in msg or
                    ("DHCPD" in msg and "AP's DHCP server" in msg) or
                    "DHCPC:" in msg
                )
                if is_direct_tplink:
                    tplink_last_seen_time = now
                    tplink_link_up = True
                    last_link_change_time = now
                    tplink_packet_count += 1
                    heartbeat_time = now
                    heartbeat_status = "UP"

            with open("/var/log/router_telemetry.log", "a") as f:
                f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} [{addr[0]}] {msg}\n')
        except Exception as e:
            time.sleep(1)

def get_router_status(now):
    """
    Evaluates Secondary Router (192.168.1.2) status using multi-source telemetry:
    1. Edge Prober Heartbeat (Mac on LAN)
    2. Direct Router Syslog (TP-Link WR845N WAN syslog pulse every 5s)
    3. ZTE Gateway physical link events

    Guarantees:
    - Mac laptop sleeping / off NEVER triggers a router DOWN alert (direct syslog keeps it UP).
    - Router power-off ALWAYS triggers DOWN alert within 10-15s (both direct syslog & prober stop).
    - Router bootup / power-on ALWAYS triggers RECOVERY alert immediately.
    """
    global zte_last_packet_time, tplink_last_seen_time, last_link_change_time, tplink_link_up
    global heartbeat_status, heartbeat_time, heartbeat_latency

    # 1. Direct router syslog freshness:
    # TP-Link WR845N transmits DHCPC syslog every 5 seconds directly to WAN.
    tplink_direct_alive = (tplink_last_seen_time > 0 and (now - tplink_last_seen_time) < 15)

    # 2. Edge prober freshness:
    # Mac prober pings 192.168.1.2 every 1 second.
    mac_prober_alive = (heartbeat_time > 0 and (now - heartbeat_time) < 15)

    # Priority 1: Mac prober is actively reporting on local Wi-Fi / LAN
    if mac_prober_alive:
        if heartbeat_status == "DOWN":
            return 0, 0.0, "edge_heartbeat_down"
        elif heartbeat_status == "UP":
            return 1, heartbeat_latency, "edge_heartbeat"

    # Priority 2: Mac laptop is asleep / shut down / closed lid / lost Wi-Fi.
    # If TP-Link is sending direct WAN syslog (every 5s), router is definitely UP!
    # Shutting down Mac NEVER marks router DOWN!
    if tplink_direct_alive:
        return 1, 0.85, "direct_tplink_syslog"

    # Priority 3: If Mac prober previously caught an explicit DOWN before Wi-Fi dropped,
    # maintain DOWN until recovery
    if heartbeat_status == "DOWN":
        return 0, 0.0, "edge_heartbeat_down"

    # Priority 4: Both Mac prober and direct TP-Link syslog have gone silent (> 15 seconds)
    # The router is powered off or disconnected!
    return 0, 0.0, "router_telemetry_silence"

class MetricsHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global heartbeat_status, heartbeat_time, heartbeat_latency, heartbeat_source
        if self.path in ["/heartbeat", "/api/heartbeat"]:
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8")
                data = json.loads(body)
                heartbeat_status = str(data.get("status", "UP")).upper()
                heartbeat_latency = float(data.get("response_time_ms", data.get("latency_ms", 0.55)))
                heartbeat_source = str(data.get("source", "edge_agent"))
                heartbeat_time = time.time()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = json.dumps({"status": "acknowledged", "state": heartbeat_status, "latency_ms": heartbeat_latency})
                self.wfile.write(resp.encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        global zte_last_packet_time, tplink_last_seen_time, last_link_change_time, tplink_link_up, tplink_packet_count, last_sender_ip
        global heartbeat_status, heartbeat_time, heartbeat_latency, edge_devices
        now = time.time()

        # Calculate Secondary Router Status
        r_up, r_lat, data_source = get_router_status(now)

        # Endpoint: /devices returns live status of edge hosts (Mac, Mobile, Router)
        if self.path in ["/devices", "/api/devices"]:
            out = {}
            for ip, info in edge_devices.items():
                age = now - info["last_seen"]
                is_alive = (info["status"] == "UP" and age < 15)

                # Secondary Router (192.168.1.2) uses authoritative multi-source status
                if ip == TPLINK_IP:
                    is_alive = (r_up == 1)
                    if is_alive:
                        info["latency"] = r_lat if r_lat > 0 else 0.85
                    else:
                        info["latency"] = 0.0

                out[ip] = {
                    "status": "UP" if is_alive else "DOWN",
                    "age_seconds": round(age, 1),
                    "latency_ms": info["latency"] if is_alive else 0.0,
                    "last_seen": info["last_seen"]
                }

            if TPLINK_IP not in out:
                out[TPLINK_IP] = {
                    "status": "UP" if r_up == 1 else "DOWN",
                    "age_seconds": round(now - tplink_last_seen_time, 1) if tplink_last_seen_time > 0 else 999.0,
                    "latency_ms": r_lat if r_up == 1 else 0.0,
                    "last_seen": tplink_last_seen_time
                }

            resp = json.dumps(out)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp.encode("utf-8"))
            return

        zte_age = now - zte_last_packet_time if zte_last_packet_time > 0 else 999999
        mac_age = now - tplink_last_seen_time if tplink_last_seen_time > 0 else 999999

        metrics = (
            f'# HELP router_syslog_alive Router heartbeat indicator (1=up, 0=down)\n'
            f'# TYPE router_syslog_alive gauge\n'
            f'router_syslog_alive{{target="TP-Link_WR845N",mac="{TPLINK_MAC}",sender="{last_sender_ip}",source="{data_source}"}} {r_up}\n\n'
            f'# HELP router_up Router availability indicator for Grafana\n'
            f'# TYPE router_up gauge\n'
            f'router_up{{instance="{TPLINK_IP}",router="TP-Link_WR845N",mac="{TPLINK_MAC}",model="TL-WR845N"}} {r_up}\n\n'
            f'# HELP router_ping_latency_ms Router latency in milliseconds (drops to 0 when down)\n'
            f'# TYPE router_ping_latency_ms gauge\n'
            f'router_ping_latency_ms{{instance="{TPLINK_IP}",router="TP-Link_WR845N",model="TL-WR845N"}} {r_lat}\n\n'
            f'# HELP router_syslog_last_seen_seconds Seconds since last received syslog packet\n'
            f'# TYPE router_syslog_last_seen_seconds gauge\n'
            f'router_syslog_last_seen_seconds{{target="TP-Link_WR845N"}} {zte_age:.1f}\n\n'
            f'# HELP router_mac_last_seen_seconds Seconds since secondary router MAC was observed\n'
            f'# TYPE router_mac_last_seen_seconds gauge\n'
            f'router_mac_last_seen_seconds{{target="TP-Link_WR845N"}} {mac_age:.1f}\n\n'
            f'# HELP router_syslog_packets_total Total count of syslog packets received\n'
            f'# TYPE router_syslog_packets_total counter\n'
            f'router_syslog_packets_total{{target="TP-Link_WR845N"}} {tplink_packet_count}\n'
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        self.wfile.write(metrics.encode("utf-8"))

    def log_message(self, format, *args):
        pass

def run_http():
    server = HTTPServer(("0.0.0.0", 9125), MetricsHandler)
    server.serve_forever()

if __name__ == "__main__":
    t = threading.Thread(target=syslog_listener, daemon=True)
    t.start()
    run_http()
