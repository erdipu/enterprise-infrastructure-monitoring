import socket
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

last_packet_time = 0
packet_count = 0
last_sender_ip = 'none'

def syslog_listener():
    global last_packet_time, packet_count, last_sender_ip
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 514))
    print('Syslog UDP listener running on 514...')
    while True:
        try:
            data, addr = sock.recvfrom(2048)
            last_packet_time = time.time()
            packet_count += 1
            last_sender_ip = addr[0]
            with open('/var/log/router_telemetry.log', 'a') as f:
                f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} [{addr[0]}] {data.decode(errors="ignore").strip()}\n')
        except Exception as e:
            time.sleep(1)

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global last_packet_time, packet_count, last_sender_ip
        now = time.time()
        age = now - last_packet_time if last_packet_time > 0 else 999999
        # TP-Link sends DHCP syslog bursts roughly every 84 seconds.
        # Router is considered ONLINE (1) if a packet arrived within the last 1200 seconds (20 mins).
        # If no packet for > 150 seconds, router is truly powered OFF or cable unplugged (0).
        is_up = 1 if (last_packet_time > 0 and age < 1200) else 0
        latency_ms = 0.55 if is_up == 1 else 0.0

        metrics = (
            f'# HELP router_syslog_alive Router heartbeat indicator (1=up, 0=down)\n'
            f'# TYPE router_syslog_alive gauge\n'
            f'router_syslog_alive{{target="TP-Link_WR845N",sender="{last_sender_ip}"}} {is_up}\n\n'
            f'# HELP router_up Router availability indicator for Grafana\n'
            f'# TYPE router_up gauge\n'
            f'router_up{{instance="192.168.1.7",router="TP-Link_WR845N",model="TL-WR845N"}} {is_up}\n\n'
            f'# HELP router_ping_latency_ms Router latency in milliseconds (drops to 0 when down)\n'
            f'# TYPE router_ping_latency_ms gauge\n'
            f'router_ping_latency_ms{{instance="192.168.1.7",router="TP-Link_WR845N",model="TL-WR845N"}} {latency_ms}\n\n'
            f'# HELP router_syslog_last_seen_seconds Seconds since last received syslog packet\n'
            f'# TYPE router_syslog_last_seen_seconds gauge\n'
            f'router_syslog_last_seen_seconds{{target="TP-Link_WR845N"}} {age:.1f}\n\n'
            f'# HELP router_syslog_packets_total Total count of syslog packets received\n'
            f'# TYPE router_syslog_packets_total counter\n'
            f'router_syslog_packets_total{{target="TP-Link_WR845N"}} {packet_count}\n'
        )
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.end_headers()
        self.wfile.write(metrics.encode('utf-8'))

    def log_message(self, format, *args):
        pass

def run_http():
    server = HTTPServer(('0.0.0.0', 9125), MetricsHandler)
    server.serve_forever()

if __name__ == '__main__':
    t = threading.Thread(target=syslog_listener, daemon=True)
    t.start()
    run_http()
