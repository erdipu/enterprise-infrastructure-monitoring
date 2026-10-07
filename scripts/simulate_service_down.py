#!/usr/bin/env python3
"""
Simulate Website / Service Outage
Target: Starts a lightweight HTTP server on port 8085, responds with 200 OK,
then simulates an outage by terminating the listener to trip Prometheus Blackbox alerts:
  - WebsiteDown (P1 Critical)
Safe & Reversible: Completely isolated local port listener.
"""

import sys
import time
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "healthy", "service": "simulated-test-app"}')

    def log_message(self, format, *args):
        return  # Suppress default noisy console logs

def main():
    parser = argparse.ArgumentParser(description="Simulate service running and unexpected outage")
    parser.add_argument("--port", type=int, default=8085, help="Port to host simulated service (default: 8085)")
    parser.add_argument("--up_duration", type=int, default=15, help="Seconds service runs healthy before simulated outage (default: 15)")
    args = parser.parse_args()

    print(f"[*] Starting simulated service on http://localhost:{args.port}/health...")
    server = HTTPServer(("0.0.0.0", args.port), HealthHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"[+] Service is UP & responding with HTTP 200 OK.")
    print(f"[*] Running healthy for {args.up_duration} seconds...")

    try:
        time.sleep(args.up_duration)
        print("\n[!] SIMULATING OUTAGE: Shutting down HTTP socket listener...")
        server.shutdown()
        server.server_close()
        print("[!] Service is now DOWN (Connection Refused). Blackbox prober will detect failure and trigger P1 alert.")
        print("[*] Waiting 10 seconds in DOWN state for demonstration...")
        time.sleep(10)
        print("[+] Outage simulation concluded.")
    except KeyboardInterrupt:
        print("\n[!] User interrupted: Terminated mock service.")
        server.shutdown()

if __name__ == "__main__":
    main()
