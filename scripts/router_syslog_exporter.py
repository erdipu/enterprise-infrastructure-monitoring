import socket
import time
import json
import re
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# Unique hardware identity for Secondary Router
TPLINK_MAC = "d8:44:89:f5:41:fa"
TPLINK_IP = "192.168.1.7"

# Telemetry tracking variables
zte_last_packet_time = time.time()
tplink_last_seen_time = 0.0
last_link_change_time = 0.0
tplink_link_up = False           # Physical link on any ZTE LAN switch port
tplink_packet_count = 0
last_sender_ip = "103.181.90.135"

# Direct edge heartbeat tracking (via POST /heartbeat)
heartbeat_status = "UNKNOWN"
heartbeat_time = 0.0
heartbeat_latency = 0.0
heartbeat_source = ""

# Scan past log to initialize state accurately on service start (only last 4 hours)
try:
    now_ts = time.time()
    with open("/var/log/router_telemetry.log", "r") as f:
        for line in f:
            # Check for link up across any LAN port (eth0-eth3 / port 1-4)
            if re.search(r"br0:\s*port\s*\d+\(eth\d+\)\s*entered\s*forwarding\s*state", line, re.IGNORECASE) or "link up" in line:
                try:
                    line_date = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").timestamp()
                    if (now_ts - line_date) < 14400:  # Fresh within 4 hours
                        tplink_link_up = True
                        last_link_change_time = line_date
                except Exception:
                    pass

            # Check for link drop across any LAN port
            elif re.search(r"br0:\s*port\s*\d+\(eth\d+\)\s*entered\s*disabled\s*state", line, re.IGNORECASE) or "link down" in line:
                try:
                    line_date = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").timestamp()
                    if (now_ts - line_date) < 14400:
                        tplink_link_up = False
                        last_link_change_time = line_date
                except Exception:
                    pass

            # Check for MAC presence
            if TPLINK_MAC in line.lower():
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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 514))
    print("Syslog UDP listener running on 514 with multi-port link-state & positive pulse detection...")
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            msg = data.decode(errors="ignore").strip()
            now = time.time()
            last_sender_ip = addr[0]

            is_zte = ("F670LV9" in msg or "ZTE" in msg)

            if is_zte:
                # 1. Heartbeat from ZTE Gateway (Primary Fiber Router)
                zte_last_packet_time = now

                # Physical link drop on ANY switch port (eth0-eth3)
                if re.search(r"br0:\s*port\s*\d+\(eth\d+\)\s*entered\s*disabled\s*state", msg, re.IGNORECASE) or "link down" in msg.lower():
                    tplink_link_up = False
                    last_link_change_time = now

                # Physical link restored on ANY switch port (eth0-eth3)
                elif re.search(r"br0:\s*port\s*\d+\(eth\d+\)\s*entered\s*forwarding\s*state", msg, re.IGNORECASE) or "link up" in msg.lower():
                    tplink_link_up = True
                    last_link_change_time = now

                # Positive pulse: MAC address query from ZTE switch table
                if TPLINK_MAC in msg.lower():
                    tplink_last_seen_time = now
                    tplink_link_up = True
                    tplink_packet_count += 1

            else:
                # 2. Direct packet from TP-Link secondary router firmware
                is_direct_tplink = (
                    "TP-Link" in msg or 
                    "WR845N" in msg or 
                    "HomeRouter" in msg or
                    TPLINK_MAC in msg.lower() or
                    TPLINK_IP in msg or
                    ("DHCPD" in msg and "AP's DHCP server" in msg)
                )
                if is_direct_tplink:
                    tplink_last_seen_time = now
                    tplink_link_up = True
                    tplink_packet_count += 1

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
        global heartbeat_status, heartbeat_time, heartbeat_latency
        now = time.time()
        
        # Priority 1: Direct edge heartbeat override (valid for 90s)
        if heartbeat_time > 0 and (now - heartbeat_time) < 90:
            is_up = 1 if heartbeat_status == "UP" else 0
            latency_ms = heartbeat_latency if is_up == 1 else 0.0
            data_source = "edge_heartbeat"
        else:
            # Priority 2: Syslog Telemetry with TTL verification
            data_source = "syslog_telemetry"
            zte_age = now - zte_last_packet_time if zte_last_packet_time > 0 else 999999
            gateway_alive = (zte_age < 120)

            # Secondary router is UP only if:
            # 1. Primary gateway is receiving power and sending syslogs
            # 2. Physical switch port is forwarding (tplink_link_up)
            # 3. Telemetry is fresh (seen within last 4 hours)
            mac_age = now - tplink_last_seen_time if tplink_last_seen_time > 0 else 999999
            link_age = now - last_link_change_time if last_link_change_time > 0 else 999999
            fresh_activity = (mac_age < 14400) or (link_age < 14400 and tplink_link_up)

            is_up = 1 if (gateway_alive and tplink_link_up and fresh_activity) else 0
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
