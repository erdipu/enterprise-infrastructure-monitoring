#!/usr/bin/env python3
"""
Simulate Alertmanager Webhook Ingestion
Target: Sends Prometheus Alertmanager JSON payloads directly to the FastAPI Backend
to demonstrate instant incident creation, deduplication, priority mapping, and auto-resolution.
"""

import sys
import json
import argparse
import urllib.request
from datetime import datetime

def send_alert_webhook(backend_url, alertname, instance, priority, severity, status, summary):
    payload = {
        "version": "4",
        "groupKey": f"alertname:{alertname}:instance:{instance}",
        "status": status,
        "receiver": "fastapi_incident_webhook",
        "alerts": [
            {
                "status": status,
                "labels": {
                    "alertname": alertname,
                    "instance": instance,
                    "priority": priority,
                    "severity": severity,
                    "target_type": "host"
                },
                "annotations": {
                    "summary": summary,
                    "description": f"Simulated test alert for {alertname} on {instance} with priority {priority}."
                },
                "startsAt": datetime.utcnow().isoformat() + "Z",
                "endsAt": (datetime.utcnow().isoformat() + "Z") if status == "resolved" else None,
                "fingerprint": f"fp-sim-{alertname.lower()}-{instance.lower()}"
            }
        ]
    }

    req = urllib.request.Request(
        f"{backend_url}/api/v1/alerts/webhook",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = response.read().decode("utf-8")
            print(f"[+] Successfully delivered {status.upper()} webhook for {alertname} ({priority}) to {backend_url}")
            print(f"    Backend Response: {res_data}")
    except Exception as e:
        print(f"[!] Failed to deliver webhook: {e}")

def main():
    parser = argparse.ArgumentParser(description="Simulate Alertmanager webhook dispatch to backend")
    parser.add_argument("--url", default="http://localhost:8090", help="Backend URL (default: http://localhost:8090)")
    parser.add_argument("--alert", default="HostDown", help="Alert name (default: HostDown)")
    parser.add_argument("--instance", default="srv-linux-prod-01", help="Target instance (default: srv-linux-prod-01)")
    parser.add_argument("--priority", default="P1", help="Priority P1, P2, P3, P4 (default: P1)")
    parser.add_argument("--severity", default="critical", help="Severity critical, warning, info (default: critical)")
    parser.add_argument("--status", default="firing", choices=["firing", "resolved"], help="Alert status (default: firing)")
    args = parser.parse_args()

    summary = f"Simulated {args.alert} on {args.instance} ({args.priority})"
    send_alert_webhook(args.url, args.alert, args.instance, args.priority, args.severity, args.status, summary)

if __name__ == "__main__":
    main()
