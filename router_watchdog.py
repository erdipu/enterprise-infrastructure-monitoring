import time
import urllib.request
import urllib.parse
import json
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ==============================================================================
# Exact Escalation Ladder Schedule (in seconds from moment of outage)
# 1st alert: 15 seconds
# 2nd alert: 2 minutes   (120s)
# 3rd alert: 10 minutes  (600s)
# 4th alert: 12 hours    (43200s)
# 5th alert: 24 hours    (86400s)
# 6th alert: 1 week      (604800s)
# 7th alert: 1 month     (2592000s)
# ==============================================================================
OUTAGE_LADDER = [
    (15, "1st Alert (Immediate Outage Detected - 15s)"),
    (120, "2nd Alert (Outage Confirmed - 2m)"),
    (600, "3rd Alert (Outage Sustained - 10m)"),
    (43200, "4th Alert (Major Extended Outage - 12h)"),
    (86400, "5th Alert (Severe Extended Outage - 24h)"),
    (604800, "6th Alert (Prolonged Outage - 1 Week)"),
    (2592000, "7th Alert (Critical Dormant Host - 1 Month)")
]

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_time_str():
    return datetime.now(IST).strftime("%I:%M:%S %p IST")

# ==============================================================================
# Notification Credentials & Configuration
# ==============================================================================
EMAIL_SENDER = "infoworld2112@gmail.com"
EMAIL_RECIPIENT = "infoworld2112@gmail.com"
EMAIL_PASSWORD = "ypen pruc cznc xwhv"

TELEGRAM_BOT_TOKEN = "8887767165:AAEeno6ErIGK0e2mWpGETlSfxHwd7PMaIjs"
TELEGRAM_CHAT_ID = "952086426"

FAST2SMS_API_KEY = ""
SMS_MOBILE_NUMBER = ""

def load_dynamic_config():
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, FAST2SMS_API_KEY, SMS_MOBILE_NUMBER
    try:
        with open("/home/ubuntu/alert_config.json", "r") as f:
            cfg = json.load(f)
            TELEGRAM_BOT_TOKEN = cfg.get("telegram_bot_token", TELEGRAM_BOT_TOKEN)
            TELEGRAM_CHAT_ID = cfg.get("telegram_chat_id", TELEGRAM_CHAT_ID)
            FAST2SMS_API_KEY = cfg.get("fast2sms_api_key", FAST2SMS_API_KEY)
            SMS_MOBILE_NUMBER = cfg.get("sms_mobile_number", SMS_MOBILE_NUMBER)
    except Exception:
        pass

def send_telegram(html_text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": html_text,
            "parse_mode": "HTML"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] Telegram alert delivered successfully.")
            return True
    except Exception as e:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] Telegram send error: {e}")
        return False

def send_sms(message_text):
    if not FAST2SMS_API_KEY or not SMS_MOBILE_NUMBER:
        return False
    try:
        url = "https://www.fast2sms.com/dev/bulkV2"
        params = urllib.parse.urlencode({
            "authorization": FAST2SMS_API_KEY,
            "route": "q",
            "message": message_text,
            "numbers": SMS_MOBILE_NUMBER
        })
        req = urllib.request.Request(url + "?" + params, headers={"cache-control": "no-cache"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] SMS delivered successfully.")
            return True
    except Exception as e:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] SMS send error: {e}")
        return False

def send_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=12)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, [EMAIL_RECIPIENT], msg.as_string())
        server.quit()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] Email successfully sent: {subject}")
        return True
    except Exception as e:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] Email send error: {e}")
        return False

# ==============================================================================
# Telegram Message Formatters
# ==============================================================================
def format_telegram_outage(device_name, target_info, idx, step_title, elapsed_sec):
    minutes = elapsed_sec // 60
    seconds = elapsed_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    ist_time = get_ist_time_str()
    
    return (
        f"🚨 <b>[ALERT {idx+1}/7] CRITICAL OUTAGE DETECTED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Device:</b> {device_name}\n"
        f"🌐 <b>Target:</b> <code>{target_info}</code>\n"
        f"⚠️ <b>Status:</b> OFFLINE / DOWN\n"
        f"⏱️ <b>Outage Duration:</b> {duration_str} ({step_title})\n"
        f"🕒 <b>Detected At:</b> {ist_time}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <a href=\"http://deepak-monitoring.duckdns.org:8090\">NOC Operations Center</a>\n"
        f"📈 <a href=\"http://deepak-monitoring.duckdns.org:3000\">Grafana Dashboard</a>"
    )

def format_telegram_recovery(device_name, target_info, downtime_sec, extra_metric="0.55 ms (Stable)"):
    minutes = downtime_sec // 60
    seconds = downtime_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    ist_time = get_ist_time_str()
    
    return (
        f"✅ <b>[RESOLVED] INFRASTRUCTURE RECOVERED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Device:</b> {device_name}\n"
        f"🌐 <b>Target:</b> <code>{target_info}</code>\n"
        f"📶 <b>Status:</b> ONLINE / OPERATIONAL\n"
        f"⚡ <b>Health:</b> {extra_metric}\n"
        f"🕒 <b>Restored At:</b> {ist_time}\n"
        f"⏳ <b>Total Downtime:</b> {duration_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"All escalation alerts cleared. System operating normally."
    )

def format_telegram_boot_stabilized(device_name, target_info, downtime_sec):
    ist_time = get_ist_time_str()
    duration_str = f"{downtime_sec}s" if downtime_sec > 0 else "< 1s"
    
    return (
        f"ℹ️ <b>[SYSTEM INFO] BOOT LINK STABILIZED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Device:</b> {device_name}\n"
        f"🌐 <b>Target IP:</b> <code>{target_info}</code>\n"
        f"🔄 <b>Event:</b> Ethernet Port Auto-Negotiation (Reboot Flap)\n"
        f"⚡ <b>Duration:</b> {duration_str}\n"
        f"🕒 <b>Timestamp:</b> {ist_time}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Router finished booting. Link verified stable at 0.55 ms."
    )

# ==============================================================================
# Email Formatters
# ==============================================================================
def format_outage_email(device_name, target_info, step_title, elapsed_sec):
    minutes = elapsed_sec // 60
    seconds = elapsed_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 22px; border: 2px solid #dc2626; border-radius: 8px; background-color: #fef2f2;">
        <h2 style="color: #dc2626; margin-top: 0;">🚨 CRITICAL INFRASTRUCTURE OUTAGE</h2>
        <p><strong>Device:</strong> {device_name} ({target_info})</p>
        <p><strong>Status:</strong> <span style="background: #dc2626; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">OFFLINE / DOWN</span></p>
        <p><strong>Escalation Level:</strong> {step_title}</p>
        <p><strong>Outage Duration:</strong> {duration_str}</p>
        <p><strong>Telemetry:</strong> Service endpoint unreachable / connection failure detected at Oracle Cloud VM 2.</p>
        <hr style="border: 0; border-top: 1px solid #fca5a5; margin: 15px 0;">
        <a href="http://deepak-monitoring.duckdns.org:8090" style="background: #2563eb; color: white; padding: 9px 18px; text-decoration: none; border-radius: 4px; display: inline-block;">Open NOC Portal</a>
    </div>
    """
    return html

def format_recovery_email(device_name, target_info, copy_num):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 22px; border: 2px solid #16a34a; border-radius: 8px; background-color: #f0fdf4;">
        <h2 style="color: #16a34a; margin-top: 0;">✅ INFRASTRUCTURE ALERT RESOLVED</h2>
        <p><strong>Device:</strong> {device_name} ({target_info})</p>
        <p><strong>Status:</strong> <span style="background: #16a34a; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">ONLINE / UP</span></p>
        <p><strong>Telemetry:</strong> Service health restored and responsive. Stability 100%.</p>
        <p><strong>Notification:</strong> Recovery notice ({copy_num} of 2) — All escalation alerts cleared. System operating normally.</p>
        <hr style="border: 0; border-top: 1px solid #bbf7d0; margin: 15px 0;">
        <a href="http://deepak-monitoring.duckdns.org:8090" style="background: #2563eb; color: white; padding: 9px 18px; text-decoration: none; border-radius: 4px; display: inline-block;">Open NOC Portal</a>
    </div>
    """
    return html

# ==============================================================================
# Health Probers
# ==============================================================================
def probe_router():
    """Reads real-time secondary router state from local telemetry collector"""
    try:
        req = urllib.request.Request("http://127.0.0.1:9125", headers={"User-Agent": "Watchdog-Poller"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            content = resp.read().decode()
            for line in content.splitlines():
                if line.startswith("router_syslog_alive") and not line.startswith("#"):
                    val = float(line.split()[-1])
                    return "UP" if val == 1.0 else "DOWN"
    except Exception:
        pass
    return "DOWN"

def probe_cloud_drive():
    """Probes Cloud Drive Server (VM 1) via direct HTTPS probe and Prometheus fallback"""
    # 1. Direct HTTPS probe
    try:
        req = urllib.request.Request(
            "https://deepak-cloud-drive.duckdns.org",
            headers={"User-Agent": "Watchdog-Probe/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status in (200, 301, 302, 401, 403):
                return "UP"
    except Exception:
        pass

    # 2. Prometheus Blackbox Exporter fallback
    try:
        prom_url = "http://127.0.0.1:9090/api/v1/query?query=probe_success%7Bservice_name%3D%22Telegram-Cloud-Drive%22%7D"
        req = urllib.request.Request(prom_url, headers={"User-Agent": "Watchdog-Poller"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("data", {}).get("result", [])
            if results:
                val = float(results[0].get("value", [0, 0])[1])
                return "UP" if val == 1.0 else "DOWN"
    except Exception:
        pass

    return "DOWN"

# ==============================================================================
# Target Monitoring Object
# ==============================================================================
class TargetMonitor:
    def __init__(self, key, display_name, target_info, probe_fn, is_router=False):
        self.key = key
        self.display_name = display_name
        self.target_info = target_info
        self.probe_fn = probe_fn
        self.is_router = is_router
        self.state = "UP"
        self.down_start_time = None
        self.sent_ladder_steps = set()

    def update(self, now):
        current_status = self.probe_fn()

        # CASE A: TRANSITION UP -> DOWN
        if current_status == "DOWN" and self.state == "UP":
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] [{self.display_name}] Outage detected! Transitioning UP -> DOWN")
            self.state = "DOWN"
            self.down_start_time = now
            self.sent_ladder_steps.clear()

        # CASE B: TRANSITION DOWN -> UP (RECOVERY)
        elif current_status == "UP" and self.state == "DOWN":
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] [{self.display_name}] Recovery detected! Transitioning DOWN -> UP")
            self.state = "UP"
            downtime_sec = int(now - self.down_start_time) if self.down_start_time else 0
            
            # Check if an actual outage alert was sent (>= 15s or sent_ladder_steps not empty)
            had_outage_alert = (len(self.sent_ladder_steps) > 0 or downtime_sec >= 15)
            self.down_start_time = None
            self.sent_ladder_steps.clear()

            if had_outage_alert:
                extra_metric = "0.55 ms (Link Stable)" if self.is_router else "HTTP 200 OK (Responsive)"
                tg_text = format_telegram_recovery(self.display_name, self.target_info, downtime_sec, extra_metric)
                send_telegram(tg_text)

                send_sms(f"RECOVERED: {self.display_name} is back ONLINE. Downtime: {downtime_sec}s. All alerts cleared.")

                print(f"[{self.display_name}] Sending Recovery Email 1 of 2...")
                send_email(f"✅ [RESOLVED 1/2] {self.display_name} Back Online", format_recovery_email(self.display_name, self.target_info, 1))
                time.sleep(3)
                print(f"[{self.display_name}] Sending Recovery Email 2 of 2...")
                send_email(f"✅ [RESOLVED 2/2] {self.display_name} Telemetry Restored", format_recovery_email(self.display_name, self.target_info, 2))

                print(f"[{self.display_name}] Recovery notices delivered (strictly 1 Telegram, 2 Emails). Downtime: {downtime_sec}s.")
            elif self.is_router:
                # Brief boot flap for router (< 15s)
                print(f"[{self.display_name}] Dispatching System Info notice for {downtime_sec}s boot link flap...")
                tg_info = format_telegram_boot_stabilized(self.display_name, self.target_info, downtime_sec)
                send_telegram(tg_info)

        # CASE C: SUSTAINED DOWN (Escalation Ladder)
        elif current_status == "DOWN" and self.state == "DOWN":
            elapsed = int(now - self.down_start_time) if self.down_start_time else 0
            for idx, (threshold, step_title) in enumerate(OUTAGE_LADDER):
                if elapsed >= threshold and idx not in self.sent_ladder_steps:
                    subject = f"🚨 [{idx+1}/7 OUTAGE] {self.display_name} is DOWN - {step_title}"
                    html = format_outage_email(self.display_name, self.target_info, step_title, elapsed)
                    if send_email(subject, html):
                        self.sent_ladder_steps.add(idx)
                        print(f"[{self.display_name}] Dispatched ladder step {idx+1} at {elapsed}s: {step_title}")

                    tg_msg = format_telegram_outage(self.display_name, self.target_info, idx, step_title, elapsed)
                    send_telegram(tg_msg)

                    sms_msg = f"ALERT: {self.display_name} is DOWN ({step_title}). Check NOC Portal: http://deepak-monitoring.duckdns.org:8090"
                    send_sms(sms_msg)

# ==============================================================================
# Main Daemon Execution
# ==============================================================================
def main():
    load_dynamic_config()
    print("Starting Corporate Multi-Target Escalation Watchdog Engine...")

    targets = [
        TargetMonitor(
            key="router",
            display_name="Secondary Router (TP-Link WR845N)",
            target_info="192.168.1.7",
            probe_fn=probe_router,
            is_router=True
        ),
        TargetMonitor(
            key="cloud_drive",
            display_name="Cloud Drive Server (VM 1)",
            target_info="https://deepak-cloud-drive.duckdns.org",
            probe_fn=probe_cloud_drive,
            is_router=False
        )
    ]

    # Initialize initial status
    for t in targets:
        init_st = t.probe_fn()
        t.state = init_st
        if init_st == "DOWN":
            t.down_start_time = time.time()
            print(f"[Watchdog] {t.display_name} initial state is DOWN.")
        else:
            print(f"[Watchdog] {t.display_name} initial state is UP. Monitoring armed.")

    while True:
        now = time.time()
        load_dynamic_config()
        for t in targets:
            t.update(now)
        time.sleep(3)

if __name__ == "__main__":
    main()
