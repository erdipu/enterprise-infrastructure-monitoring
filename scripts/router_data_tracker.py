#!/usr/bin/env python3
"""
Enterprise Infrastructure Monitoring Platform
Home Router & Local Wi-Fi Bandwidth Tracker (TP-Link WR845N - Deepak_2112)
Measures Wi-Fi interface throughput, cumulative daily/monthly data transfer,
and dispatches twice-daily Telegram usage reports (12:00 PM IST and 08:00 PM IST).
Automatically detects if PC is connected to Home Wi-Fi or Roaming on an external network.
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(WORKSPACE_DIR, "router_tracker_state.json")
CONFIG_FILE = os.path.join(WORKSPACE_DIR, "alert_config.json")
ROUTER_IP = "192.168.1.7"
ROUTER_SSID = "Deepak_2112"
WIFI_INTERFACE = "en1"

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

def read_interface_bytes(iface=WIFI_INTERFACE):
    """Reads cumulative Inbound (Ibytes) and Outbound (Obytes) via netstat on macOS"""
    rx_bytes = 0
    tx_bytes = 0

    try:
        cmd = ["netstat", "-ib", "-I", iface]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 10 and parts[0] == iface:
                    try:
                        ib = int(parts[6])
                        ob = int(parts[9])
                        if ib > rx_bytes:
                            rx_bytes = ib
                        if ob > tx_bytes:
                            tx_bytes = ob
                    except ValueError:
                        continue
    except Exception as e:
        print(f"[-] Error reading netstat: {e}")

    return rx_bytes, tx_bytes

def ping_router(ip=ROUTER_IP):
    """Pings the TP-Link router to confirm link health and latency"""
    try:
        cmd = ["ping", "-c", "2", "-W", "800", ip]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "round-trip min/avg/max" in line or "round-trip min/avg" in line:
                    avg_ms = float(line.split("=")[1].split("/")[1])
                    return True, avg_ms
            return True, 1.0
        return False, 0.0
    except Exception:
        return False, 0.0

def get_router_mac(ip=ROUTER_IP):
    """Retrieves MAC address from local ARP table"""
    try:
        cmd = ["arp", "-n", ip]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and "at " in res.stdout:
            parts = res.stdout.split("at ")[1].split()
            return parts[0].upper()
    except Exception:
        pass
    return ""

def check_network_presence():
    """Detects if PC is currently connected to the home TP-Link router network"""
    is_up, latency_ms = ping_router(ROUTER_IP)
    mac = get_router_mac(ROUTER_IP) if is_up else ""
    is_home = bool(is_up and mac and mac.upper().startswith("D8:44:89"))
    return is_home, is_up, latency_ms, (mac if mac else "D8:44:89:F5:41:FA")

def update_and_get_state(curr_rx, curr_tx, is_home):
    """
    Robust delta accumulator with network-aware roaming support:
    - If on Home Wi-Fi: accumulates into Home Router data counters.
    - If on External Network (Hotspot/Office): freezes Home counters and tracks Roaming usage.
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
        "roaming_today_rx": 0,
        "roaming_today_tx": 0,
        "last_network": "HOME" if is_home else "ROAMING",
        "last_updated": time.time()
    }

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                saved = json.load(f)

            prev_raw_rx = saved.get("last_raw_rx", curr_rx)
            prev_raw_tx = saved.get("last_raw_tx", curr_tx)

            # Check day rollover in IST
            if saved.get("today_date") == today_str:
                state["today_rx"] = saved.get("today_rx", 0)
                state["today_tx"] = saved.get("today_tx", 0)
                state["roaming_today_rx"] = saved.get("roaming_today_rx", 0)
                state["roaming_today_tx"] = saved.get("roaming_today_tx", 0)
            else:
                state["today_rx"] = 0
                state["today_tx"] = 0
                state["roaming_today_rx"] = 0
                state["roaming_today_tx"] = 0

            # Check month rollover in IST
            if saved.get("current_month") == current_month_str:
                state["month_rx"] = saved.get("month_rx", 0)
                state["month_tx"] = saved.get("month_tx", 0)
            else:
                state["month_rx"] = 0
                state["month_tx"] = 0

            # Delta calculation
            if curr_rx >= prev_raw_rx:
                delta_rx = curr_rx - prev_raw_rx
            else:
                delta_rx = curr_rx

            if curr_tx >= prev_raw_tx:
                delta_tx = curr_tx - prev_raw_tx
            else:
                delta_tx = curr_tx

            # Attribute deltas to Home or Roaming
            if is_home:
                state["today_rx"] += delta_rx
                state["today_tx"] += delta_tx
                state["month_rx"] += delta_rx
                state["month_tx"] += delta_tx
            else:
                state["roaming_today_rx"] += delta_rx
                state["roaming_today_tx"] += delta_tx

            state["last_raw_rx"] = curr_rx
            state["last_raw_tx"] = curr_tx
            state["last_network"] = "HOME" if is_home else "ROAMING"

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
    """Silently updates local network counters without sending Telegram notification"""
    is_home, is_up, latency_ms, mac = check_network_presence()
    curr_rx, curr_tx = read_interface_bytes()
    state = update_and_get_state(curr_rx, curr_tx, is_home)
    net_str = "HOME (Deepak_2112)" if is_home else "EXTERNAL / ROAMING"
    print(f"[+] Synced local counters [{net_str}]: Today Home In={format_bytes(state['today_rx'])}, Out={format_bytes(state['today_tx'])}")

def generate_report(is_test=False):
    ist_now = get_ist_now()
    is_home, is_up, latency_ms, mac = check_network_presence()
    curr_rx, curr_tx = read_interface_bytes()
    state = update_and_get_state(curr_rx, curr_tx, is_home)

    rx_today = state["today_rx"]
    tx_today = state["today_tx"]
    total_today = rx_today + tx_today

    total_month_gb = (state["month_rx"] + state["month_tx"]) / (1024 * 1024 * 1024)

    current_hour = ist_now.hour
    if is_test:
        label = "TEST / INSTANT REPORT"
    elif current_hour < 16:
        label = "12:00 PM MID-DAY REPORT"
    else:
        label = "08:00 PM EVENING REPORT"

    time_str = ist_now.strftime("%I:%M:%S %p IST (%d %b %Y)")

    if is_home:
        status_banner = f"🟢 <b>Link Status  :</b> Connected (Latency: {latency_ms:.2f} ms)"
        roaming_section = ""
        footer_note = "✅ <i>Home Wi-Fi telemetry operating normally. Next automated report in scheduled cycle.</i>"
    else:
        status_banner = "⚠️ <b>Link Status  :</b> Roaming (Connected to External Network / Hotspot)"
        roaming_total = state.get("roaming_today_rx", 0) + state.get("roaming_today_tx", 0)
        roaming_section = (
            f"📱 <b>External/Hotspot Today :</b> {format_bytes(roaming_total)}\n"
            f"ℹ️ <i>Home router tracking safely paused while away from home.</i>\n"
        )
        footer_note = "ℹ️ <i>PC currently outside home network. Home counters preserved.</i>"

    msg = (
        f"📶 <b>[HOME ROUTER DATA USAGE — {label}]</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>Access Point :</b> TP-Link TL-WR845N (<code>{ROUTER_SSID}</code>)\n"
        f"🌐 <b>Gateway IP   :</b> <code>{ROUTER_IP}</code> (MAC: <code>{mac}</code>)\n"
        f"💻 <b>Client Device:</b> Mac Workstation (<code>192.168.1.2</code> on <code>{WIFI_INTERFACE}</code>)\n"
        f"{status_banner}\n"
        f"🕒 <b>Report Time  :</b> {time_str}\n\n"
        f"📥 <b>Home Inbound (Download) :</b> <b>{format_bytes(rx_today)}</b>\n"
        f"📤 <b>Home Outbound (Upload)   :</b> <b>{format_bytes(tx_today)}</b>\n"
        f"📈 <b>Total Home Data Today    :</b> <b>{format_bytes(total_today)}</b>\n\n"
        f"{roaming_section}"
        f"📅 <b>Month-to-Date Home Total:</b> {total_month_gb:.2f} GB\n"
        f"⚡ <b>Daily Quota Limit        :</b> Unlimited\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{footer_note}\n"
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
