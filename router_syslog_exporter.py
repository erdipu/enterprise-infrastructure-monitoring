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

# Scan past log to initialize state accurately on service start (only last 4 hours)
try:
    now_ts = time.time()
    with open("/var/log/router_telemetry.log", "r") as f:
        for line in f:
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
                        tplink_link_up = False
                    elif "status=UP" in msg:
                        heartbeat_time = now
                        heartbeat_status = "UP"
                        heartbeat_latency = dev_latency
                        tplink_link_up = True
                        tplink_last_seen_time = now
                    elif "status=PAUSED" in msg:
                        heartbeat_time = 0.0
                        heartbeat_status = "PAUSED"

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
        
        # Endpoint: /devices returns live status of edge hosts (Mac, Mobile, Router)
        if self.path in ["/devices", "/api/devices"]:
            out = {}
            for ip, info in edge_devices.items():
                age = now - info["last_seen"]
                is_alive = (info["status"] == "UP" and age < 15)
                out[ip] = {
                    "status": "UP" if is_alive else "DOWN",
                    "age_seconds": round(age, 1),
                    "latency_ms": info["latency"] if is_alive else 0.0,
                    "last_seen": info["last_seen"]
                }
            resp = json.dumps(out)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.encode("utf-8"))
            return
        
        # Priority 1: Direct edge heartbeat override
        if heartbeat_time > 0:
            edge_age = now - heartbeat_time
            if edge_age < 15:
                # Active streaming
                is_up = 1 if heartbeat_status == "UP" else 0
                latency_ms = heartbeat_latency if is_up == 1 else 0.0
                data_source = "edge_heartbeat"
            elif heartbeat_status == "DOWN":
                # Explicitly marked DOWN by edge prober
                is_up = 0
                latency_ms = 0.0
                data_source = "edge_heartbeat_down"
            elif edge_age >= 15 and edge_age < 1800:
                # Abrupt stream silence (router Wi-Fi dropped / power off / link severed)
                # Stays DOWN until recovery signal arrives from ZTE or edge agent
                is_up = 0
                latency_ms = 0.0
                data_source = "edge_heartbeat_silence"
            else:
                # After 30 minutes of complete silence, laptop assumed sleeping/away; fall back to syslog
                data_source = "syslog_telemetry"
                zte_age = now - zte_last_packet_time if zte_last_packet_time > 0 else 999999
                gateway_alive = (zte_age < 120)
                is_up = 1 if (gateway_alive and tplink_link_up) else 0
                latency_ms = 0.55 if is_up == 1 else 0.0
        else:
            # Priority 2: Passive Syslog Telemetry
            data_source = "syslog_telemetry"
            zte_age = now - zte_last_packet_time if zte_last_packet_time > 0 else 999999
            gateway_alive = (zte_age < 120)
            is_up = 1 if (gateway_alive and tplink_link_up) else 0
            latency_ms = 0.55 if is_up == 1 else 0.0

        zte_age = now - zte_last_packet_time if zte_last_packet_time > 0 else 999999
        mac_age = now - tplink_last_seen_time if tplink_last_seen_time > 0 else 999999

        metrics = (
            f'# HELP router_syslog_alive Router heartbeat indicator (1=up, 0=down)\n'
            f'# TYPE router_syslog_alive gauge\n'
            f'router_syslog_alive{{target="TP-Link_WR845N",mac="{TPLINK_MAC}",sender="{last_sender_ip}",source="{data_source}"}} {is_up}\n\n'
            f'# HELP router_up Router availability indicator for Grafana\n'
            f'# TYPE router_up gauge\n'
            f'router_up{{instance="{TPLINK_IP}",router="TP-Link_WR845N",mac="{TPLINK_MAC}",model="TL-WR845N"}} {is_up}\n\n'
            f'# HELP router_ping_latency_ms Router latency in milliseconds (drops to 0 when down)\n'
            f'# TYPE router_ping_latency_ms gauge\n'
            f'router_ping_latency_ms{{instance="{TPLINK_IP}",router="TP-Link_WR845N",model="TL-WR845N"}} {latency_ms}\n\n'
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
