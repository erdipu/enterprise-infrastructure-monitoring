#!/usr/bin/env python3
"""
Enterprise Infrastructure Monitoring Platform
24/7 Cloud Server Bandwidth & Data Usage Tracker
Monitors real-time network transfer on Oracle Cloud VM 2 and dispatches
twice-daily Telegram usage reports (12:00 PM IST and 08:00 PM IST).
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

STATE_FILE = "/home/ubuntu/data_tracker_state.json"
CONFIG_FILE = "/home/ubuntu/alert_config.json"
ORACLE_FREE_LIMIT_GB = 10000.0  # 10 TB free outbound bandwidth/month

def get_ist_now():
    return datetime.now(IST)

def format_bytes(num_bytes):
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.2f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"

def read_interface_bytes():
    """Reads cumulative RX and TX bytes from /proc/net/dev for ens3 or primary interface"""
    rx_bytes = 0
    tx_bytes = 0
    target_interface = None

    try:
        with open("/proc/net/dev", "r") as f:
            for line in f:
                parts = line.strip().split()
                if not parts or ":" not in parts[0]:
                    continue
                iface = parts[0].split(":")[0]
                # Look for external public interfaces: ens3, eth0, enp*, or default primary
                if iface in ("ens3", "eth0", "enp0s3", "enp1s0"):
                    target_interface = iface
                    rx_bytes = int(parts[1])
                    tx_bytes = int(parts[9])
                    break
        
        # Fallback to first non-loopback interface if standard name not found
        if not target_interface:
            with open("/proc/net/dev", "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if not parts or ":" not in parts[0]:
                        continue
                    iface = parts[0].split(":")[0]
                    if iface not in ("lo", "docker0") and not iface.startswith(("veth", "br-")):
                        target_interface = iface
                        rx_bytes = int(parts[1])
                        tx_bytes = int(parts[9])
                        break
    except Exception as e:
        print(f"[-] Error reading /proc/net/dev: {e}")
        return None, 0, 0

    return target_interface, rx_bytes, tx_bytes

def update_and_get_state(curr_rx, curr_tx):
    """
    Robust delta accumulator:
    Monotonically tracks bytes across server reboots, midnight IST roll-overs,
    and monthly quota accounting.
    """
    ist_now = get_ist_now()
    today_str = ist_now.strftime("%Y-%m-%d")
    current_month_str = ist_now.strftime("%Y-%m")

    state = {
        "today_date": today_str,
        "current_month": current_month_str,
        "last_raw_rx": curr_rx,
        "last_raw_tx": curr_tx,
        "today_rx": 0,
        "today_tx": 0,
        "month_rx": 0,
        "month_tx": 0,
        "last_updated": time.time()
    }

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                saved = json.load(f)

            prev_raw_rx = saved.get("last_raw_rx", saved.get("daily_baseline_rx", curr_rx))
            prev_raw_tx = saved.get("last_raw_tx", saved.get("daily_baseline_tx", curr_tx))

            # Handle day rollover in IST
            if saved.get("today_date") == today_str:
                state["today_rx"] = saved.get("today_rx", 0)
                state["today_tx"] = saved.get("today_tx", 0)
            else:
                state["today_rx"] = 0
                state["today_tx"] = 0

            # Handle month rollover in IST
            if saved.get("current_month") == current_month_str:
                state["month_rx"] = saved.get("month_rx", 0)
                state["month_tx"] = saved.get("month_tx", 0)
            else:
                state["month_rx"] = 0
                state["month_tx"] = 0

            # Compute deltas since last sample
            if curr_rx >= prev_raw_rx:
                delta_rx = curr_rx - prev_raw_rx
            else:
                # System reboot occurred, counter wrapped/restarted
                delta_rx = curr_rx

            if curr_tx >= prev_raw_tx:
                delta_tx = curr_tx - prev_raw_tx
            else:
                # System reboot occurred, counter wrapped/restarted
                delta_tx = curr_tx

            # Accumulate
            state["today_rx"] += delta_rx
            state["today_tx"] += delta_tx
            state["month_rx"] += delta_rx
            state["month_tx"] += delta_tx
            state["last_raw_rx"] = curr_rx
            state["last_raw_tx"] = curr_tx

        except Exception as e:
            print(f"[-] Warning loading state file: {e}")

    save_state(state)
    return state

def save_state(state):
    state["last_updated"] = time.time()
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[-] Error saving state: {e}")

def send_telegram(message_html):
    token = None
    chat_id = None
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                token = cfg.get("telegram_bot_token")
                chat_id = cfg.get("telegram_chat_id")
        except Exception:
            pass

    if not token or not chat_id:
        print("[-] Telegram credentials not found in alert_config.json")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message_html,
        "parse_mode": "HTML"
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("[+] Telegram report delivered successfully.")
            return True
    except Exception as e:
        print(f"[-] Telegram dispatch error: {e}")
        return False

def sync_only():
    """Silently updates raw byte delta accumulator without sending Telegram notification"""
    iface, curr_rx, curr_tx = read_interface_bytes()
    if not iface:
        print("[-] Could not find network interface.")
        return
    state = update_and_get_state(curr_rx, curr_tx)
    print(f"[+] Synced counters for {iface}: Today In={format_bytes(state['today_rx'])}, Out={format_bytes(state['today_tx'])}")

def generate_report(is_test=False):
    ist_now = get_ist_now()
    iface, curr_rx, curr_tx = read_interface_bytes()

    if not iface:
        print("[-] Could not find network interface.")
        return

    state = update_and_get_state(curr_rx, curr_tx)

    rx_today = state["today_rx"]
    tx_today = state["today_tx"]
    total_today = rx_today + tx_today

    total_month_gb = (state["month_rx"] + state["month_tx"]) / (1024 * 1024 * 1024)

    # Determine report label (12:00 PM or 08:00 PM)
    current_hour = ist_now.hour
    if is_test:
        label = "TEST / INSTANT REPORT"
    elif current_hour < 16:
        label = "12:00 PM MID-DAY REPORT"
    else:
        label = "08:00 PM EVENING REPORT"

    time_str = ist_now.strftime("%I:%M:%S %p IST (%d %b %Y)")

    msg = (
        f"📊 <b>[CLOUD SERVER DATA USAGE — {label}]</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <b>Host:</b> Oracle Cloud VM 2 (<code>80.225.252.145</code>)\n"
        f"🔌 <b>Interface:</b> <code>{iface}</code> (100% Host WAN)\n"
        f"🕒 <b>Report Time:</b> {time_str}\n\n"
        f"📥 <b>Inbound (Download) :</b> <b>{format_bytes(rx_today)}</b>\n"
        f"📤 <b>Outbound (Upload)   :</b> <b>{format_bytes(tx_today)}</b>\n"
        f"📈 <b>Total Data Today    :</b> <b>{format_bytes(total_today)}</b>\n\n"
        f"📅 <b>Month-to-Date Total:</b> {total_month_gb:.2f} GB / 10,000 GB (Free Tier)\n"
        f"⚡ <b>Daily Quota Limit  :</b> Unlimited\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <i>Cloud bandwidth operating normally. Next automated report in scheduled cycle.</i>\n"
        f"📊 <a href=\"http://deepak-monitoring.duckdns.org:8090\">NOC Operations Portal</a> | "
        f"📈 <a href=\"http://deepak-monitoring.duckdns.org:3000\">Grafana</a>"
    )

    print(f"[*] Generated Report:\n{msg}\n")
    send_telegram(msg)

if __name__ == "__main__":
    if "--sync" in sys.argv:
        sync_only()
    else:
        is_test_mode = ("--test" in sys.argv or "--now" in sys.argv)
        generate_report(is_test=is_test_mode)
