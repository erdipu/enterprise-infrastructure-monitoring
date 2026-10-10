import time
import urllib.request
import smtplib
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

def send_email(subject, html_body):
    sender = "infoworld2112@gmail.com"
    recipient = "infoworld2112@gmail.com"
    password = "ypen pruc cznc xwhv"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=12)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, [recipient], msg.as_string())
        server.quit()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Email successfully sent: {subject}")
        return True
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Email send error: {e}")
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
        <p><strong>Telemetry:</strong> Heartbeat stream stopped at Oracle Cloud VM 2.</p>
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
        <p><strong>Telemetry:</strong> Heartbeat telemetry restored. Link stability 100%.</p>
        <p><strong>Notification:</strong> Recovery notice ({copy_num} of 2) — All outage alerts canceled.</p>
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
    print("Starting Corporate Escalation Watchdog Engine...")
    
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
        current_status = poll_status()

        # CASE A: TRANSITION UP -> DOWN
        if current_status == "DOWN" and STATE == "UP":
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Outage detected! Transitioning UP -> DOWN")
            STATE = "DOWN"
            DOWN_START_TIME = now
            SENT_LADDER_STEPS = set()
            RECOVERY_EMAILS_SENT = 0

        # CASE B: TRANSITION DOWN -> UP (RECOVERY)
        elif current_status == "UP" and STATE == "DOWN":
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Recovery detected! Transitioning DOWN -> UP")
            STATE = "UP"
            DOWN_START_TIME = None
            SENT_LADDER_STEPS.clear()
            
            # Send exactly 2 recovery emails and stop
            print("[Watchdog] Sending Recovery Email 1 of 2...")
            send_email("✅ [RESOLVED 1/2] Secondary Router (TP-Link WR845N) Back Online", format_recovery_email(1))
            time.sleep(3)
            print("[Watchdog] Sending Recovery Email 2 of 2...")
            send_email("✅ [RESOLVED 2/2] Secondary Router (TP-Link WR845N) Telemetry Restored", format_recovery_email(2))
            RECOVERY_EMAILS_SENT = 2
            print("[Watchdog] Both recovery emails delivered. Pending down alerts stopped.")

        # CASE C: SUSTAINED DOWN (Check Escalation Ladder)
        elif current_status == "DOWN" and STATE == "DOWN":
            elapsed = int(now - DOWN_START_TIME)
            for idx, (threshold, step_title) in enumerate(OUTAGE_LADDER):
                if elapsed >= threshold and idx not in SENT_LADDER_STEPS:
                    subject = f"🚨 [{idx+1}/7 OUTAGE] Secondary Router (TP-Link WR845N) is DOWN - {step_title}"
                    html = format_outage_email(step_title, elapsed)
                    if send_email(subject, html):
                        SENT_LADDER_STEPS.add(idx)
                        print(f"[Watchdog] Dispatched ladder step {idx+1} at {elapsed}s: {step_title}")

        time.sleep(3)

if __name__ == "__main__":
    main()
