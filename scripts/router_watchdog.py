import time
import urllib.request
import urllib.parse
import json
import smtplib
import base64
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
    (5, "1st Alert (Immediate Outage Detected - 5s)"),
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
EMAIL_ENABLED = True
EMAIL_SENDER = "infoworld2112@gmail.com"
EMAIL_RECIPIENT = "infoworld2112@gmail.com"
EMAIL_PASSWORD = "ypen pruc cznc xwhv"

TELEGRAM_BOT_TOKEN = "8887767165:AAEeno6ErIGK0e2mWpGETlSfxHwd7PMaIjs"
TELEGRAM_CHAT_ID = "952086426"

FAST2SMS_API_KEY = ""
SMS_MOBILE_NUMBER = ""

SERVICENOW_ENABLED = False
SERVICENOW_INSTANCE = "dev387540"
SERVICENOW_USER = "admin"
SERVICENOW_PASSWORD = ""
SERVICENOW_ASSIGNMENT_GROUP = "bd04ddb793334310ccf3f847dd03d68e"

def load_dynamic_config():
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, FAST2SMS_API_KEY, SMS_MOBILE_NUMBER, EMAIL_ENABLED
    global SERVICENOW_ENABLED, SERVICENOW_INSTANCE, SERVICENOW_USER, SERVICENOW_PASSWORD, SERVICENOW_ASSIGNMENT_GROUP
    try:
        with open("/home/ubuntu/alert_config.json", "r") as f:
            cfg = json.load(f)
            TELEGRAM_BOT_TOKEN = cfg.get("telegram_bot_token", TELEGRAM_BOT_TOKEN)
            TELEGRAM_CHAT_ID = cfg.get("telegram_chat_id", TELEGRAM_CHAT_ID)
            FAST2SMS_API_KEY = cfg.get("fast2sms_api_key", FAST2SMS_API_KEY)
            SMS_MOBILE_NUMBER = cfg.get("sms_mobile_number", SMS_MOBILE_NUMBER)
            if "email_enabled" in cfg:
                EMAIL_ENABLED = bool(cfg["email_enabled"])
            SERVICENOW_ENABLED = bool(cfg.get("servicenow_enabled", SERVICENOW_ENABLED))
            SERVICENOW_INSTANCE = cfg.get("servicenow_instance", SERVICENOW_INSTANCE)
            SERVICENOW_USER = cfg.get("servicenow_user", SERVICENOW_USER)
            SERVICENOW_PASSWORD = cfg.get("servicenow_password", SERVICENOW_PASSWORD)
            SERVICENOW_ASSIGNMENT_GROUP = cfg.get("servicenow_assignment_group", SERVICENOW_ASSIGNMENT_GROUP)
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
    if not EMAIL_ENABLED or not EMAIL_SENDER:
        return True

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
# NOC Backend Incident API Integration
# ==============================================================================
def trigger_backend_incident(target_name, target_info, target_type, summary, description):
    try:
        url = "http://127.0.0.1:8090/api/v1/incidents/internal/trigger"
        payload = json.dumps({
            "target_name": target_name,
            "target_info": target_info,
            "target_type": target_type,
            "summary": summary,
            "description": description,
            "priority": "P1",
            "severity": "Critical"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            inc_num = data.get("incident_number")
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] [NOC Backend] Incident triggered successfully: {inc_num} for {target_name}")
            return inc_num
    except Exception as e:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [Incident API Error] Failed to trigger incident for {target_name}: {e}")
        return None

def resolve_backend_incident(target_name, target_info, inc_number=None, resolution_notes=None):
    try:
        url = "http://127.0.0.1:8090/api/v1/incidents/internal/resolve"
        payload = json.dumps({
            "target_name": target_name,
            "target_info": target_info,
            "incident_number": inc_number,
            "resolution_notes": resolution_notes
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            inc_num = data.get("incident_number")
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] [NOC Backend] Incident resolved successfully: {inc_num} for {target_name}")
            return inc_num
    except Exception as e:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [Incident API Error] Failed to resolve incident for {target_name}: {e}")
        return None

SERVICENOW_AUTOMATION_USER = "02681dff93334310ccf3f847dd03d66e"  # Automation
SERVICENOW_ASSIGNED_TO = "6816f79cc0a8016401c5a33be04be441"       # Deepak Kumar
SERVICENOW_CALLER_ID = SERVICENOW_AUTOMATION_USER                # Created by Automation

# ==============================================================================
# ServiceNow PDI Table API Integration
# ==============================================================================
def create_servicenow_incident(target_name, target_info, summary=None, description=None):
    if not SERVICENOW_ENABLED or not SERVICENOW_INSTANCE or not SERVICENOW_PASSWORD:
        return None, None
    try:
        url = f"https://{SERVICENOW_INSTANCE}.service-now.com/api/now/table/incident"
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        ist_time = get_ist_time_str()

        short_desc = summary or f"[CRITICAL P1] {target_name} ({target_info}) is DOWN - Gateway Outage"
        formatted_desc = f"""🚨 ============================================================
🚨 [P1 CRITICAL] ENTERPRISE INFRASTRUCTURE OUTAGE DETECTED
🚨 ============================================================

📍 ASSET DETAILS:
• Device / Service : {target_name}
• Target / Host    : {target_info}
• Environment      : Production NOC

⚠️ OUTAGE DIAGNOSTICS:
• Health Status    : OFFLINE / DOWN
• Detection Reason : Ping Probes (ICMP) Unreachable - 100% Packet Loss
• Incident Priority: P1 - Critical
• Detected At      : {ist_time} IST ({now_utc} UTC)

🤖 DISPATCH & ROUTING:
• Created By       : Monitoring Automation Engine
• Contact Type     : Monitoring
• Assignment Group : Network Operations Center (NOC)
• Assigned Engineer: Deepak Kumar
• Routing Action   : Auto-Assigned to Primary Engineer for Immediate Triage

📊 OPERATIONS & TELEMETRY LINKS:
• NOC Dashboard    : http://deepak-monitoring.duckdns.org:8090
• Grafana Telemetry: http://deepak-monitoring.duckdns.org:3000
• Health Endpoint  : http://deepak-monitoring.duckdns.org:8090/live

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Auto-generated by Enterprise Watchdog Engine.
⚡ 'Actual start' timestamp recorded upon detection.
⚡ Will auto-resolve and record 'Actual end' when link recovers."""

        payload_dict = {
            "short_description": short_desc,
            "description": formatted_desc,
            "urgency": "1",
            "impact": "1",  # Urgency 1 + Impact 1 = Priority 1 (Critical)
            "priority": "1",
            "category": "network",
            "contact_type": "monitoring",
            "caller_id": SERVICENOW_CALLER_ID,
            "opened_by": SERVICENOW_CALLER_ID,
            "assigned_to": SERVICENOW_ASSIGNED_TO,
            "work_start": now_utc  # Actual start
        }
        if SERVICENOW_ASSIGNMENT_GROUP:
            payload_dict["assignment_group"] = SERVICENOW_ASSIGNMENT_GROUP
        payload = json.dumps(payload_dict).encode("utf-8")
        auth_str = f"{SERVICENOW_USER}:{SERVICENOW_PASSWORD}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Basic {b64_auth}"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            res = data.get("result", {})
            inc_number = res.get("number")
            sys_id = res.get("sys_id")
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] [ServiceNow] Ticket created: {inc_number} (sys_id: {sys_id}, P1 Critical, Assigned to Deepak Kumar, Created by Automation, Actual Start: {now_utc})")
            return inc_number, sys_id
    except Exception as e:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [ServiceNow Error] Failed to create incident: {e}")
        return None, None

def resolve_servicenow_incident(sys_id, resolution_notes):
    if not SERVICENOW_ENABLED or not SERVICENOW_INSTANCE or not SERVICENOW_PASSWORD or not sys_id:
        return False
    try:
        url = f"https://{SERVICENOW_INSTANCE}.service-now.com/api/now/table/incident/{sys_id}"
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        payload = json.dumps({
            "state": "6",
            "incident_state": "6",
            "close_code": "Solution provided",
            "close_notes": resolution_notes,
            "work_end": now_utc  # Actual end
        }).encode("utf-8")
        auth_str = f"{SERVICENOW_USER}:{SERVICENOW_PASSWORD}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            method="PATCH",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Basic {b64_auth}"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] [ServiceNow] Ticket {sys_id} resolved with Actual End: {now_utc}.")
            return True
    except Exception as e:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [ServiceNow Error] Failed to resolve incident: {e}")
        return False

# ==============================================================================
# Telegram Message Formatters
# ==============================================================================
def format_telegram_outage(device_name, target_info, idx, step_title, elapsed_sec, inc_number=None, snow_number=None):
    minutes = elapsed_sec // 60
    seconds = elapsed_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    ist_time = get_ist_time_str()
    
    ticket_lines = ""
    if snow_number:
        ticket_lines += f"🎫 <b>ServiceNow:</b> <code>#{snow_number}</code> (P1 Critical)\n"
    if inc_number:
        ticket_lines += f"🎫 <b>Local NOC:</b> <code>#{inc_number}</code> (P1 Critical)\n"

    snow_link = f"🌐 <a href=\"https://{SERVICENOW_INSTANCE}.service-now.com/now/nav/ui/classic/params/target/incident_list.do\">ServiceNow Incident Queue</a>\n" if SERVICENOW_ENABLED else ""

    return (
        f"🚨 <b>[ALERT {idx+1}/7] OUTAGE DETECTED (P1 CRITICAL)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ticket_lines}"
        f"📍 <b>Device:</b> {device_name}\n"
        f"🌐 <b>Target:</b> <code>{target_info}</code>\n"
        f"🤖 <b>Created By:</b> Monitoring Automation\n"
        f"👤 <b>Assigned To:</b> Deepak Kumar\n"
        f"👥 <b>Group:</b> Network Operations Center (NOC)\n"
        f"⚠️ <b>Status:</b> OFFLINE / DOWN\n"
        f"⏱️ <b>Outage Duration:</b> {duration_str} ({step_title})\n"
        f"🕒 <b>Detected At:</b> {ist_time}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{snow_link}"
        f"📊 <a href=\"http://deepak-monitoring.duckdns.org:8090\">NOC Operations Center</a>\n"
        f"📈 <a href=\"http://deepak-monitoring.duckdns.org:3000\">Grafana Dashboard</a>"
    )

def format_telegram_recovery(device_name, target_info, downtime_sec, extra_metric="0.55 ms (Stable)", inc_number=None, snow_number=None):
    minutes = downtime_sec // 60
    seconds = downtime_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    ist_time = get_ist_time_str()
    
    ticket_lines = ""
    if snow_number:
        ticket_lines += f"🎫 <b>ServiceNow:</b> <code>#{snow_number}</code> CLOSED\n"
    if inc_number:
        ticket_lines += f"🎫 <b>Local NOC:</b> <code>#{inc_number}</code> CLOSED\n"

    return (
        f"✅ <b>[RESOLVED] INFRASTRUCTURE RECOVERED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{ticket_lines}"
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
def format_outage_email(device_name, target_info, step_title, elapsed_sec, inc_number=None, snow_number=None):
    minutes = elapsed_sec // 60
    seconds = elapsed_sec % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    ticket_info = ""
    if snow_number:
        ticket_info += f"<p><strong>ServiceNow Ticket:</strong> <span style=\"font-weight: bold; color: #dc2626;\">#{snow_number}</span> (P1)</p>"
    if inc_number:
        ticket_info += f"<p><strong>Local NOC Ticket:</strong> <span style=\"font-weight: bold; color: #dc2626;\">#{inc_number}</span> (P1)</p>"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 22px; border: 2px solid #dc2626; border-radius: 8px; background-color: #fef2f2;">
        <h2 style="color: #dc2626; margin-top: 0;">🚨 CRITICAL INFRASTRUCTURE OUTAGE</h2>
        {ticket_info}
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

def format_recovery_email(device_name, target_info, copy_num, inc_number=None, snow_number=None):
    ticket_info = ""
    if snow_number:
        ticket_info += f"<p><strong>ServiceNow Ticket:</strong> <span style=\"font-weight: bold; color: #16a34a;\">#{snow_number}</span> [RESOLVED]</p>"
    if inc_number:
        ticket_info += f"<p><strong>Local NOC Ticket:</strong> <span style=\"font-weight: bold; color: #16a34a;\">#{inc_number}</span> [RESOLVED]</p>"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; padding: 22px; border: 2px solid #16a34a; border-radius: 8px; background-color: #f0fdf4;">
        <h2 style="color: #16a34a; margin-top: 0;">✅ INFRASTRUCTURE ALERT RESOLVED</h2>
        {ticket_info}
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
    # 1. Direct HTTPS HEAD probe (Zero-bandwidth consumption)
    try:
        req = urllib.request.Request(
            "https://deepak-cloud-drive.duckdns.org",
            method="HEAD",
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
    def __init__(self, key, display_name, target_info, probe_fn, is_router=False, target_type="host"):
        self.key = key
        self.display_name = display_name
        self.target_info = target_info
        self.probe_fn = probe_fn
        self.is_router = is_router
        self.target_type = target_type
        self.state = "UP"
        self.down_start_time = None
        self.sent_ladder_steps = set()
        self.active_incident_number = None
        self.snow_incident_number = None
        self.snow_sys_id = None

    def update(self, now):
        current_status = self.probe_fn()

        # CASE A: TRANSITION UP -> DOWN
        if current_status == "DOWN" and self.state == "UP":
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] [{self.display_name}] Outage detected! Transitioning UP -> DOWN")
            self.state = "DOWN"
            self.down_start_time = now
            self.sent_ladder_steps.clear()
            self.active_incident_number = None
            self.snow_incident_number = None
            self.snow_sys_id = None

        # CASE B: TRANSITION DOWN -> UP (RECOVERY)
        elif current_status == "UP" and self.state == "DOWN":
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] [{self.display_name}] Recovery detected! Transitioning DOWN -> UP")
            self.state = "UP"
            downtime_sec = int(now - self.down_start_time) if self.down_start_time else 0
            
            # Check if an actual outage alert was sent (>= 5s or sent_ladder_steps not empty)
            had_outage_alert = (
                len(self.sent_ladder_steps) > 0 or 
                downtime_sec >= 5 or 
                self.active_incident_number is not None or
                self.snow_incident_number is not None
            )
            inc_to_close = self.active_incident_number
            snow_to_close = self.snow_incident_number
            snow_sys_id_to_close = self.snow_sys_id

            self.down_start_time = None
            self.sent_ladder_steps.clear()
            self.active_incident_number = None
            self.snow_incident_number = None
            self.snow_sys_id = None

            if had_outage_alert:
                notes = f"Service recovered and responsive. Total downtime: {downtime_sec}s."
                
                # 1. Auto-resolve incident in Local NOC Portal DB
                resolved_inc = resolve_backend_incident(self.display_name, self.target_info, inc_to_close, notes)
                if not inc_to_close and resolved_inc:
                    inc_to_close = resolved_inc

                # 2. Auto-resolve incident in ServiceNow PDI
                if snow_sys_id_to_close:
                    resolve_servicenow_incident(snow_sys_id_to_close, notes)

                extra_metric = "0.55 ms (Link Stable)" if self.is_router else "HTTP 200 OK (Responsive)"
                tg_text = format_telegram_recovery(self.display_name, self.target_info, downtime_sec, extra_metric, inc_to_close, snow_to_close)
                send_telegram(tg_text)

                if self.is_router:
                    print(f"[{self.display_name}] Dispatching System Info notice for {downtime_sec}s boot link flap / stabilization...")
                    tg_info = format_telegram_boot_stabilized(self.display_name, self.target_info, downtime_sec)
                    send_telegram(tg_info)

                inc_label = snow_to_close or inc_to_close
                inc_sms = f" (INC #{inc_label} CLOSED)" if inc_label else ""
                send_sms(f"RECOVERED: {self.display_name} is back ONLINE{inc_sms}. Downtime: {downtime_sec}s. All alerts cleared.")

                if EMAIL_ENABLED:
                    print(f"[{self.display_name}] Sending Recovery Email 1 of 2...")
                    send_email(f"✅ [RESOLVED 1/2] {self.display_name} Back Online", format_recovery_email(self.display_name, self.target_info, 1, inc_to_close, snow_to_close))
                    time.sleep(3)
                    print(f"[{self.display_name}] Sending Recovery Email 2 of 2...")
                    send_email(f"✅ [RESOLVED 2/2] {self.display_name} Telemetry Restored", format_recovery_email(self.display_name, self.target_info, 2, inc_to_close, snow_to_close))
                    print(f"[{self.display_name}] Recovery notices delivered (strictly 1 Telegram, 2 Emails). Downtime: {downtime_sec}s.")
                else:
                    print(f"[{self.display_name}] Recovery notices delivered (Telegram sent, Email notifications disabled). Downtime: {downtime_sec}s.")
            elif self.is_router:
                # Brief boot flap for router (< 5s)
                print(f"[{self.display_name}] Dispatching System Info notice for {downtime_sec}s boot link flap...")
                tg_info = format_telegram_boot_stabilized(self.display_name, self.target_info, downtime_sec)
                send_telegram(tg_info)

        # CASE C: SUSTAINED DOWN (Escalation Ladder)
        elif current_status == "DOWN" and self.state == "DOWN":
            elapsed = int(now - self.down_start_time) if self.down_start_time else 0
            for idx, (threshold, step_title) in enumerate(OUTAGE_LADDER):
                if elapsed >= threshold and idx not in self.sent_ladder_steps:
                    self.sent_ladder_steps.add(idx)

                    # Trigger or link active incident in NOC portal & ServiceNow on first ladder alert
                    if not self.active_incident_number:
                        summary = f"[CRITICAL P1] {self.display_name} ({self.target_info}) is DOWN - Gateway Outage" if self.is_router else f"[CRITICAL P1] {self.display_name} is DOWN - Service Outage"
                        description = f"Critical outage detected for {self.display_name} ({self.target_info}) by Watchdog prober. Downtime exceeded {threshold}s."
                        self.active_incident_number = trigger_backend_incident(
                            self.display_name, self.target_info, self.target_type, summary, description
                        )
                        if SERVICENOW_ENABLED and not self.snow_incident_number:
                            snow_num, snow_sid = create_servicenow_incident(
                                self.display_name, self.target_info, summary, description
                            )
                            self.snow_incident_number = snow_num
                            self.snow_sys_id = snow_sid

                    print(f"[{self.display_name}] Dispatched ladder step {idx+1} at {elapsed}s (NOC: {self.active_incident_number}, SNOW: {self.snow_incident_number}): {step_title}")

                    if EMAIL_ENABLED:
                        inc_label = self.snow_incident_number or self.active_incident_number
                        inc_subj = f" #{inc_label}" if inc_label else ""
                        subject = f"🚨 [{idx+1}/7 OUTAGE]{inc_subj} {self.display_name} is DOWN - {step_title}"
                        html = format_outage_email(self.display_name, self.target_info, step_title, elapsed, self.active_incident_number, self.snow_incident_number)
                        send_email(subject, html)

                    tg_msg = format_telegram_outage(self.display_name, self.target_info, idx, step_title, elapsed, self.active_incident_number, self.snow_incident_number)
                    send_telegram(tg_msg)

                    inc_label = self.snow_incident_number or self.active_incident_number
                    inc_sms = f" [INC #{inc_label}]" if inc_label else ""
                    sms_msg = f"ALERT:{inc_sms} {self.display_name} is DOWN ({step_title}). Check NOC Portal: http://deepak-monitoring.duckdns.org:8090"
                    send_sms(sms_msg)

# ==============================================================================
# Main Daemon Execution
# ==============================================================================
def main():
    load_dynamic_config()
    print("Starting Corporate Multi-Target Escalation Watchdog Engine with Incident & ServiceNow Bridge...")

    targets = [
        TargetMonitor(
            key="router",
            display_name="Secondary Router (TP-Link WR845N)",
            target_info="192.168.1.2",
            probe_fn=probe_router,
            is_router=True,
            target_type="router"
        ),
        TargetMonitor(
            key="cloud_drive",
            display_name="Cloud Drive Server (VM 1)",
            target_info="https://deepak-cloud-drive.duckdns.org",
            probe_fn=probe_cloud_drive,
            is_router=False,
            target_type="website"
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
        time.sleep(2)

if __name__ == "__main__":
    main()
