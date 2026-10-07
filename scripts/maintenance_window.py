#!/usr/bin/env python3
"""
Enterprise Maintenance Window Automation Script
Creates an Alertmanager silence for a specific server or service during scheduled maintenance/patching
to prevent false-positive P1 incidents from waking up on-call teams.
"""

import sys
import json
import argparse
import urllib.request
from datetime import datetime, timedelta

def create_silence(alertmanager_url, instance, alertname, duration_hours, comment, author):
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=duration_hours)

    matchers = []
    if instance:
        matchers.append({"name": "instance", "value": instance, "isRegex": False})
    if alertname:
        matchers.append({"name": "alertname", "value": alertname, "isRegex": False})

    payload = {
        "matchers": matchers,
        "startsAt": start_time.isoformat() + "Z",
        "endsAt": end_time.isoformat() + "Z",
        "createdBy": author,
        "comment": comment
    }

    req = urllib.request.Request(
        f"{alertmanager_url}/api/v2/silences",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = response.read().decode("utf-8")
            silence_id = json.loads(res_data).get("silenceID")
            print("=" * 70)
            print(" [✓] CORPORATE MAINTENANCE SILENCE CREATED SUCCESSFULLY")
            print("=" * 70)
            print(f" Silence ID     : {silence_id}")
            print(f" Target Instance: {instance or 'ALL'}")
            print(f" Target Alert   : {alertname or 'ALL'}")
            print(f" Duration       : {duration_hours} Hour(s)")
            print(f" Start Time     : {start_time.isoformat()}Z")
            print(f" End Time       : {end_time.isoformat()}Z")
            print(f" Authorized By  : {author}")
            print(f" Change Reason  : {comment}")
            print("=" * 70)
            print(" Alertmanager will suppress alert dispatches while telemetry continues collecting.")
    except Exception as e:
        print(f"[!] Failed to create Alertmanager silence: {e}")

def main():
    parser = argparse.ArgumentParser(description="Create corporate maintenance window in Alertmanager")
    parser.add_argument("--url", default="http://localhost:9093", help="Alertmanager URL (default: http://localhost:9093)")
    parser.add_argument("--instance", help="Hostname or IP to silence (e.g., srv-linux-prod-01)")
    parser.add_argument("--alertname", help="Specific alert to silence (leave blank for all alerts on instance)")
    parser.add_argument("--duration_hours", type=float, default=2.0, help="Duration in hours (default: 2.0)")
    parser.add_argument("--comment", default="Scheduled corporate maintenance window per approved Change Request", help="Reason / Ticket #")
    parser.add_argument("--author", default="NOC-Operations", help="Author name")
    args = parser.parse_args()

    if not args.instance and not args.alertname:
        print("[!] Error: You must specify at least --instance or --alertname to silence.")
        sys.exit(1)

    create_silence(args.url, args.instance, args.alertname, args.duration_hours, args.comment, args.author)

if __name__ == "__main__":
    main()
