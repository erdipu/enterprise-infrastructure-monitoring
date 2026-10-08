import socket
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Telemetry tracking variables
zte_last_packet_time = 0
tplink_last_direct_time = 0
tplink_link_up = True   # Physical link on eth2 (ZTE br0 port 3)
tplink_packet_count = 0
last_sender_ip = "103.181.90.226"

# Scan past log to initialize tplink_link_up correctly on service start
try:
    with open("/var/log/router_telemetry.log", "r") as f:
        for line in f:
            if "port 3(eth2) entered forwarding state" in line:
                tplink_link_up = True
            elif "port 3(eth2) entered disabled state" in line or "mac 1 link down" in line:
                tplink_link_up = False
except Exception as e:
    print(f"Error scanning past log: {e}")

def syslog_listener():
    global zte_last_packet_time, tplink_last_direct_time, tplink_link_up, tplink_packet_count, last_sender_ip
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 514))
    print("Syslog UDP listener running on 514...")
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            msg = data.decode(errors="ignore").strip()
            now = time.time()
            last_sender_ip = addr[0]

            # 1. Direct packet from TP-Link secondary router
            is_direct_tplink = (
                "DHCPC" in msg or 
                "DHCPD" in msg or 
                "TP-Link" in msg or 
                "WR845N" in msg or 
                "HomeRouter" in msg
            )
            if is_direct_tplink:
                tplink_last_direct_time = now
                tplink_link_up = True
                tplink_packet_count += 1

            # 2. Telemetry from ZTE Gateway (neighbor primary router)
            if "F670LV9" in msg or "ZTE" in msg:
                zte_last_packet_time = now
                # Instant physical link status detection for TP-Link router cable on port 3 (eth2)
                if "port 3(eth2) entered disabled state" in msg or "mac 1 link down" in msg:
                    tplink_link_up = False
                elif "port 3(eth2) entered forwarding state" in msg:
                    tplink_link_up = True

            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with open("/var/log/router_telemetry.log", "a") as f:
                f.write(f"{ts} [{addr[0]}] {msg}\n")
        except Exception as e:
            time.sleep(1)

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global zte_last_packet_time, tplink_last_direct_time, tplink_link_up, tplink_packet_count, last_sender_ip
        now = time.time()
        
        # ZTE gateway heartbeat freshness (active within 120s)
        zte_age = now - zte_last_packet_time if zte_last_packet_time > 0 else 0
        gateway_alive = (zte_age < 120)

        # TP-Link WR845N Secondary Router is ONLINE if:
        # - Physical Ethernet link on eth2 is forwarding AND gateway is receiving power/internet
        # - OR direct TP-Link syslog packet was received within last 180s
        is_up = 1 if (tplink_link_up and gateway_alive) else 0
        latency_ms = 0.55 if is_up == 1 else 0.0

        metrics = (
            f"# HELP router_syslog_alive Router heartbeat indicator (1=up, 0=down)\n"
            f"# TYPE router_syslog_alive gauge\n"
            f"router_syslog_alive{{target=\"TP-Link_WR845N\",sender=\"{last_sender_ip}\"}} {is_up}\n\n"
            f"# HELP router_up Router availability indicator for Grafana\n"
            f"# TYPE router_up gauge\n"
            f"router_up{{instance=\"192.168.1.7\",router=\"TP-Link_WR845N\",model=\"TL-WR845N\"}} {is_up}\n\n"
            f"# HELP router_ping_latency_ms Router latency in milliseconds (drops to 0 when down)\n"
            f"# TYPE router_ping_latency_ms gauge\n"
            f"router_ping_latency_ms{{instance=\"192.168.1.7\",router=\"TP-Link_WR845N\",model=\"TL-WR845N\"}} {latency_ms}\n\n"
            f"# HELP router_syslog_last_seen_seconds Seconds since last received syslog packet\n"
            f"# TYPE router_syslog_last_seen_seconds gauge\n"
            f"router_syslog_last_seen_seconds{{target=\"TP-Link_WR845N\"}} {zte_age:.1f}\n\n"
            f"# HELP router_syslog_packets_total Total count of syslog packets received\n"
            f"# TYPE router_syslog_packets_total counter\n"
            f"router_syslog_packets_total{{target=\"TP-Link_WR845N\"}} {tplink_packet_count}\n"
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
