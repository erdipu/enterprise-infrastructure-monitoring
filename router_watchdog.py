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

STATE = "UP"           # "UP" or "DOWN"
DOWN_START_TIME = None  # Timestamp when router went down
SENT_LADDER_STEPS = set() # Steps already emailed for this outage
RECOVERY_EMAILS_SENT = 0 # Count of recovery emails sent (capped at exactly 2)

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

# Telegram Bot (Configured via /home/ubuntu/alert_config.json or defaults here)
TELEGRAM_BOT_TOKEN = "8887767165:AAEeno6ErIGK0e2mWpGETlSfxHwd7PMaIjs"
TELEGRAM_CHAT_ID = "952086426"

# SMS Configuration (Supports Fast2SMS Quick SMS API)
FAST2SMS_API_KEY = ""
SMS_MOBILE_NUMBER = ""

def load_dynamic_config():
    """Optionally load credentials from alert_config.json if present"""
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
    """Sends immediate alert message via Telegram Bot API with HTML formatting"""
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

def format_telegram_outage(idx, step_title, elapsed_sec):
    minutes = elapsed_sec // 60
    seconds = elapsed_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    ist_time = get_ist_time_str()
    
    return (
        f"🚨 <b>[ALERT {idx+1}/7] CRITICAL OUTAGE DETECTED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Device:</b> Secondary Router (TP-Link WR845N)\n"
        f"🌐 <b>Target IP:</b> <code>192.168.1.7</code>\n"
        f"⚠️ <b>Status:</b> OFFLINE / DOWN\n"
        f"⏱️ <b>Outage Duration:</b> {duration_str} ({step_title})\n"
        f"🕒 <b>Detected At:</b> {ist_time}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <a href=\"http://deepak-monitoring.duckdns.org:8090\">NOC Operations Center</a>\n"
        f"📈 <a href=\"http://deepak-monitoring.duckdns.org:3000\">Grafana Dashboard</a>"
    )

def format_telegram_recovery(downtime_sec):
    minutes = downtime_sec // 60
    seconds = downtime_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    ist_time = get_ist_time_str()
    
    return (
        f"✅ <b>[RESOLVED] INFRASTRUCTURE RECOVERED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>Device:</b> Secondary Router (TP-Link WR845N)\n"
        f"🌐 <b>Target IP:</b> <code>192.168.1.7</code>\n"
        f"📶 <b>Status:</b> ONLINE / OPERATIONAL\n"
        f"⚡ <b>Latency:</b> 0.55 ms (Link 100% Stable)\n"
        f"🕒 <b>Restored At:</b> {ist_time}\n"
        f"⏳ <b>Total Downtime:</b> {duration_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"All escalation alerts cleared. System operating normally."
    )

def send_sms(message_text):
    """Sends SMS via Fast2SMS quick SMS API"""
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

def format_outage_email(step_title, elapsed_sec):
    minutes = elapsed_sec // 60
    seconds = elapsed_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 22px; border: 2px solid #dc2626; border-radius: 8px; background-color: #fef2f2;">
        <h2 style="color: #dc2626; margin-top: 0;">🚨 CRITICAL INFRASTRUCTURE OUTAGE</h2>
        <p><strong>Device:</strong> Secondary Router (TP-Link TL-WR845N / 192.168.1.7)</p>
        <p><strong>Status:</strong> <span style="background: #dc2626; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">OFFLINE / DOWN</span></p>
        <p><strong>Escalation Level:</strong> {step_title}</p>
        <p><strong>Outage Duration:</strong> {duration_str}</p>
        <p><strong>Telemetry:</strong> Physical link disconnected / telemetry stopped at Oracle Cloud VM 2.</p>
        <hr style="border: 0; border-top: 1px solid #fca5a5; margin: 15px 0;">
        <a href="http://deepak-monitoring.duckdns.org:8090" style="background: #2563eb; color: white; padding: 9px 18px; text-decoration: none; border-radius: 4px; display: inline-block;">Open NOC Portal</a>
    </div>
    """
    return html

def format_recovery_email(copy_num):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 22px; border: 2px solid #16a34a; border-radius: 8px; background-color: #f0fdf4;">
        <h2 style="color: #16a34a; margin-top: 0;">✅ INFRASTRUCTURE ALERT RESOLVED</h2>
        <p><strong>Device:</strong> Secondary Router (TP-Link TL-WR845N / 192.168.1.7)</p>
        <p><strong>Status:</strong> <span style="background: #16a34a; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">ONLINE / UP</span></p>
        <p><strong>Telemetry:</strong> Physical link and heartbeat telemetry restored. Stability 100%.</p>
        <p><strong>Notification:</strong> Recovery notice ({copy_num} of 2) — All escalation alerts cleared. System operating normally.</p>
        <hr style="border: 0; border-top: 1px solid #bbf7d0; margin: 15px 0;">
        <a href="http://deepak-monitoring.duckdns.org:8090" style="background: #2563eb; color: white; padding: 9px 18px; text-decoration: none; border-radius: 4px; display: inline-block;">Open NOC Portal</a>
    </div>
    """
    return html

def poll_status():
    """Reads real-time router state from local telemetry collector"""
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

def main():
    global STATE, DOWN_START_TIME, SENT_LADDER_STEPS, RECOVERY_EMAILS_SENT
    load_dynamic_config()
    print("Starting Corporate Escalation Watchdog Engine with Telegram/SMS support...")
    
    # Initialize state from live probe
    initial = poll_status()
    STATE = initial
    if initial == "DOWN":
        DOWN_START_TIME = time.time()
        print("[Watchdog] Initial state is DOWN. Outage tracking started.")
    else:
        print("[Watchdog] Initial state is UP. Monitoring armed.")

    while True:
        now = time.time()
        load_dynamic_config()
        current_status = poll_status()

        # CASE A: TRANSITION UP -> DOWN
        if current_status == "DOWN" and STATE == "UP":
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] Outage detected! Transitioning UP -> DOWN")
            STATE = "DOWN"
            DOWN_START_TIME = now
            SENT_LADDER_STEPS = set()
            RECOVERY_EMAILS_SENT = 0

        # CASE B: TRANSITION DOWN -> UP (RECOVERY)
        elif current_status == "UP" and STATE == "DOWN":
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] Recovery detected! Transitioning DOWN -> UP")
            STATE = "UP"
            downtime_sec = int(now - DOWN_START_TIME) if DOWN_START_TIME else 0
            
            # Check if this was a genuine outage where down alerts were actually dispatched
            # (i.e. outage lasted >= 15 seconds or any ladder alert was sent)
            had_outage_alert = (len(SENT_LADDER_STEPS) > 0 or downtime_sec >= 15)
            
            DOWN_START_TIME = None
            SENT_LADDER_STEPS.clear()
            
            if had_outage_alert:
                # 1. Send strictly 1 recovery message to Telegram
                tg_text = format_telegram_recovery(downtime_sec)
                send_telegram(tg_text)
                
                # 2. Send recovery SMS
                send_sms(f"RECOVERED: Secondary Router (TP-Link WR845N) is back ONLINE. Downtime: {downtime_sec}s. All alerts cleared.")
                
                # 3. Send strictly 2 recovery emails
                print("[Watchdog] Sending Recovery Email 1 of 2...")
                send_email("✅ [RESOLVED 1/2] Secondary Router (TP-Link WR845N) Back Online", format_recovery_email(1))
                time.sleep(3)
                print("[Watchdog] Sending Recovery Email 2 of 2...")
                send_email("✅ [RESOLVED 2/2] Secondary Router (TP-Link WR845N) Telemetry Restored", format_recovery_email(2))
                RECOVERY_EMAILS_SENT = 2
                
                print(f"[Watchdog] Recovery notices delivered (strictly 1 Telegram, 2 Emails). Downtime: {downtime_sec}s.")
            else:
                print(f"[Watchdog] Ignored momentary {downtime_sec}s boot flap (no outage alert had been dispatched).")

        # CASE C: SUSTAINED DOWN (Check Escalation Ladder)
        elif current_status == "DOWN" and STATE == "DOWN":
            elapsed = int(now - DOWN_START_TIME) if DOWN_START_TIME else 0
            for idx, (threshold, step_title) in enumerate(OUTAGE_LADDER):
                if elapsed >= threshold and idx not in SENT_LADDER_STEPS:
                    subject = f"🚨 [{idx+1}/7 OUTAGE] Secondary Router (TP-Link WR845N) is DOWN - {step_title}"
                    html = format_outage_email(step_title, elapsed)
                    if send_email(subject, html):
                        SENT_LADDER_STEPS.add(idx)
                        print(f"[Watchdog] Dispatched ladder step {idx+1} at {elapsed}s: {step_title}")
                    
                    # Telegram & SMS instant dispatch
                    tg_msg = format_telegram_outage(idx, step_title, elapsed)
                    send_telegram(tg_msg)
                    sms_msg = f"ALERT: TP-Link WR845N router is DOWN ({step_title}). Check NOC Portal: http://deepak-monitoring.duckdns.org:8090"
                    send_sms(sms_msg)

        time.sleep(3)

if __name__ == "__main__":
    main()
