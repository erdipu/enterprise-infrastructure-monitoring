#!/usr/bin/env python3
"""
Enterprise Infrastructure Monitoring Platform
Antigravity AI Cold-Start Handover & Reconnection Specification PDF Generator
Produces a publication-grade, professional technical PDF manual.
"""

import os
import sys

# Support user site-packages if running on macOS or custom python environments
user_site = os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages")
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.append(user_site)

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Omit header and footer on cover page if desired, or show consistently
        if self._pageNumber > 1:
            # Running Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(36, 756, "ENTERPRISE INFRASTRUCTURE MONITORING & ESCALATION PLATFORM")
            self.setFont("Helvetica", 8)
            self.drawRightString(612 - 36, 756, "ANTIGRAVITY AI COLD-START HANDOVER")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(36, 748, 612 - 36, 748)

            # Running Footer
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(36, 40, 612 - 36, 40)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(36, 28, "CONFIDENTIAL & PROPRIETARY — AI HANDOVER SPECIFICATION")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(612 - 36, 28, page_text)
            
        self.restoreState()

def build_pdf(output_filename):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Custom Corporate Palette
    PRIMARY = colors.HexColor("#0F172A")    # Slate 900
    SECONDARY = colors.HexColor("#1E3A8A")  # Blue 900
    ACCENT = colors.HexColor("#2563EB")     # Blue 600
    TEXT_DARK = colors.HexColor("#1E293B")  # Slate 800
    TEXT_MUTED = colors.HexColor("#475569") # Slate 600
    BG_LIGHT = colors.HexColor("#F8FAFC")   # Slate 50
    BORDER_LIGHT = colors.HexColor("#E2E8F0")# Slate 200
    CODE_BG = colors.HexColor("#F1F5F9")    # Slate 100
    PROMPT_BG = colors.HexColor("#F8FAFC")  # Off-white / light slate

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=ACCENT,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'Heading1',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=SECONDARY,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=TEXT_DARK,
        spaceAfter=5
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=11,
        textColor=TEXT_DARK
    )

    table_header = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=7,
        leading=9.5,
        textColor=TEXT_DARK
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9.5,
        textColor=TEXT_DARK
    )

    prompt_style = ParagraphStyle(
        'PromptStyle',
        fontName='Courier',
        fontSize=6.8,
        leading=9.2,
        textColor=colors.HexColor("#0F172A")
    )

    story = []

    # =========================================================================
    # PAGE 1: TITLE, METADATA, PURPOSE & WHAT IS REQUIRED FROM USER
    # =========================================================================
    story.append(Paragraph("Antigravity AI Cold-Start Handover Specification", title_style))
    story.append(Paragraph("Zero-Context AI Reconnection, Project Onboarding & Autonomous Development Prompt", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=0, spaceAfter=8))

    # Metadata Box (Width = 540)
    meta_data = [
        [
            Paragraph("<b>Target Domain:</b> AI Continuity &amp; Project Handover", table_cell),
            Paragraph("<b>Specification Version:</b> v1.0.0 (Production)", table_cell)
        ],
        [
            Paragraph("<b>Repository:</b> github.com/erdipu/enterprise-infrastructure-monitoring", table_cell),
            Paragraph("<b>Production Host:</b> deepak-monitoring.duckdns.org (80.225.252.145)", table_cell)
        ],
        [
            Paragraph("<b>Cold-Start Onboarding Time:</b> &lt; 2 Minutes", table_cell),
            Paragraph("<b>AI Model Compatibility:</b> Antigravity 2.0 / Gemini Pro Coding Agent", table_cell)
        ],
        [
            Paragraph("<b>Required User Action:</b> Copy &amp; Paste Master Prompt", table_cell),
            Paragraph("<b>Security Policy:</b> Zero Secrets Exposed / Full Parameterization", table_cell)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("1. Purpose &amp; Cold-Start Resilience Principles", h1_style))
    story.append(Paragraph(
        "If you format your computer, lose this conversation, or start a completely fresh AI coding session in Google Antigravity, "
        "the agent starts with zero memory of past chats. However, because our entire platform architecture, database schemas, "
        "edge daemons, and disaster runbooks are fully committed to GitHub, <b>Antigravity can onboard autonomously and resume "
        "development immediately</b> when provided with the structured handover prompt on Page 2.",
        body_style
    ))

    # Callout Box
    resilience_callout = [
        [
            Paragraph(
                "<b>Why This Guarantees 100% Continuity:</b><br/>"
                "• <b>Self-Documenting Codebase:</b> All 7 Docker services, 2 edge daemons, and 8 database tables are version-controlled.<br/>"
                "• <b>Deterministic Onboarding:</b> The prompt commands Antigravity to clone the repository, read the architecture guides, and inspect git status.<br/>"
                "• <b>Zero Risk of Secret Leakage:</b> Sensitive passwords and private keys are never passed into public repositories.",
                callout_style
            )
        ]
    ]
    resilience_table = Table(resilience_callout, colWidths=[540])
    resilience_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BFDBFE")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(resilience_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. What Is Required From Your Side (Prerequisites Checklist)", h1_style))
    story.append(Paragraph(
        "Before pasting the master prompt into a new Antigravity session on a freshly formatted PC, ensure you have these 4 items ready:",
        body_style
    ))

    req_data = [
        [
            Paragraph("Prerequisite Item", table_header),
            Paragraph("What You Need To Have Ready", table_header),
            Paragraph("Where To Place It / How To Provide It", table_header)
        ],
        [
            Paragraph("<b>1. GitHub Account &amp; Access</b>", table_cell_bold),
            Paragraph("GitHub username (<code>erdipu</code>) and Personal Access Token (PAT) with <code>repo</code> write scope, or SSH key configured on GitHub.", table_cell),
            Paragraph("Run <code>git clone https://github.com/erdipu/enterprise-infrastructure-monitoring.git</code> or sign in via Git credential helper.", table_cell)
        ],
        [
            Paragraph("<b>2. Cloud Server SSH Key</b>", table_cell_bold),
            Paragraph("Private key file <code>ssh-key-2026-10-08.key</code> (obtained from your Bitwarden Vault or encrypted USB cold storage).", table_cell),
            Paragraph("Place in <code>~/.ssh/ssh-key-2026-10-08.key</code> on your PC and run: <code>chmod 600 ~/.ssh/ssh-key-2026-10-08.key</code>.", table_cell)
        ],
        [
            Paragraph("<b>3. Secrets &amp; Bot Tokens</b>", table_cell_bold),
            Paragraph("• Telegram Bot Token &amp; Chat ID (<code>@my_infrastructure_alert_bot</code>)<br/>"
                      "• Fast2SMS API Key &amp; Phone Number<br/>"
                      "• Gmail SMTP App Password &amp; DuckDNS Token", table_cell),
            Paragraph("Preserved safely in Bitwarden Password Manager or encrypted vault <code>platform_secrets_backup.enc</code>.", table_cell)
        ],
        [
            Paragraph("<b>4. Development Tools</b>", table_cell_bold),
            Paragraph("Installed on your fresh PC:<br/>"
                      "• Git, Python 3.10+, and Docker Desktop<br/>"
                      "• Google Antigravity IDE / CLI", table_cell),
            Paragraph("Installed via <code>brew install git python3 docker</code> (macOS) or package managers on Windows/Ubuntu.", table_cell)
        ]
    ]

    req_table = Table(req_data, colWidths=[120, 230, 190])
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(req_table)

    # =========================================================================
    # PAGE 2: THE MASTER COLD-START PROMPT FOR ANTIGRAVITY
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("3. The Master Cold-Start Prompt for Antigravity", h1_style))
    story.append(Paragraph(
        "Copy the prompt text below and paste it as your <b>very first prompt to Antigravity</b>. "
        "Replace the bracketed text at the bottom with your specific desired change or feature request:",
        body_style
    ))

    master_prompt_text = (
        "<b>Hello Antigravity. I am the lead engineer for the Universal Device &amp; Service Monitoring Platform. "
        "My PC was formatted / my previous conversation was cleared, and I need you to onboard onto this project, "
        "inspect its codebase and live hybrid cloud deployment, and assist me with developing and updating it.</b><br/><br/>"
        "<b>1. PROJECT OVERVIEW &amp; REPOSITORY</b><br/>"
        "• GitHub Repository: https://github.com/erdipu/enterprise-infrastructure-monitoring.git<br/>"
        "• Production Host: http://deepak-monitoring.duckdns.org (Oracle Cloud OCI VM 2: 80.225.252.145)<br/>"
        "• Local Workspace: Clone or open 'enterprise-infrastructure-monitoring' in your scratch workspace.<br/><br/>"
        "<b>2. ARCHITECTURE &amp; TECHNOLOGY STACK</b><br/>"
        "• Edge Network (On-Premises): TP-Link TL-WR845N (Target 1: 192.168.1.7, AP Mode) hardwired to ZTE F670LV9 Gateway.<br/>"
        "  Transmits UDP 514 Syslog telemetry through CGNAT to Cloud VM 2.<br/>"
        "• Telemetry Daemons:<br/>"
        "  - router_syslog_exporter.py: UDP 514 syslog receiver &amp; Prometheus metrics exporter on port :9125.<br/>"
        "  - router_watchdog.py: 7-stage multi-target escalation engine (Telegram, SMS, Email).<br/>"
        "• Core Observability Stack (Docker Compose):<br/>"
        "  - PostgreSQL 15 (monitoring_db with 8 tables: users, servers, monitoring_targets, incidents, alerts, comments, audit_logs, notifications).<br/>"
        "  - Prometheus (:9090), Alertmanager (:9093), Grafana (:3000), Node Exporter (:9100), Blackbox Exporter (:9115).<br/>"
        "  - Backend API (:5000) &amp; Custom NOC Portal Frontend (:8090).<br/>"
        "• Production Server Daemons: Running 24/7 on Ubuntu 22.04 (ubuntu@80.225.252.145) under systemd.<br/><br/>"
        "<b>3. KEY DOCUMENTATION TO READ FIRST</b><br/>"
        "Please read the following documents in docs/ before making changes:<br/>"
        "1. README.md - Master portfolio documentation and emergency checklist.<br/>"
        "2. docs/ENTERPRISE_SYSTEM_ARCHITECTURE.md - Live hybrid cloud architecture and CGNAT traversal.<br/>"
        "3. docs/DISASTER_RECOVERY_PLAN.md - Master DRP and 3-2-1 backup strategy.<br/>"
        "4. docs/PROJECT_SETUP_GUIDE.md - Complete server and local deployment instructions.<br/>"
        "5. docs/DATABASE_RECOVERY_GUIDE.md - PostgreSQL schema and backup/restore scripts.<br/><br/>"
        "<b>4. STRICT SAFETY &amp; ENGINEERING RULES</b><br/>"
        "1. Never commit secrets: Never commit private keys (*.key, *.pem), passwords, or API tokens to Git.<br/>"
        "2. Zero-downtime on Production: Do not restart or modify production containers or daemons without verifying locally first.<br/>"
        "3. Always take pre-change backups: If modifying the database, run scripts/backup_database.sh before running migrations.<br/>"
        "4. Synchronize GitHub and Cloud: Any changes committed to GitHub must be cleanly pulled onto Cloud VM via SSH.<br/><br/>"
        "<b>5. MY IMMEDIATE REQUEST</b><br/>"
        "Please first verify that you have cloned or navigated to the repository, inspect git status and the directory layout, "
        "verify your understanding of the architecture, and then help me with:<br/>"
        "<b>[DESCRIBE YOUR DESIRED CHANGE OR TASK HERE]</b>"
    )

    prompt_box = [
        [Paragraph(master_prompt_text, prompt_style)]
    ]
    prompt_table = Table(prompt_box, colWidths=[540])
    prompt_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), PROMPT_BG),
        ('BOX', (0,0), (-1,-1), 1.2, ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(prompt_table)

    # =========================================================================
    # PAGE 3: AI EXECUTION PROTOCOL, TASK EXAMPLES & CONTINUITY SIGN-OFF
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("4. Antigravity AI Autonomous Execution Protocol", h1_style))
    story.append(Paragraph(
        "When Antigravity receives this prompt in a new conversation, it automatically follows this 5-stage protocol:",
        body_style
    ))

    proto_data = [
        [
            Paragraph("Stage", table_header),
            Paragraph("AI Action &amp; Tool Execution", table_header),
            Paragraph("Verification Criteria", table_header)
        ],
        [
            Paragraph("<b>1. Workspace Discovery</b>", table_cell_bold),
            Paragraph("Checks local directory. If empty, runs <code>git clone https://github.com/erdipu/enterprise-infrastructure-monitoring.git</code>.", table_cell),
            Paragraph("Clean Git tree on branch <code>main</code>.", table_cell)
        ],
        [
            Paragraph("<b>2. Architectural Ingestion</b>", table_cell_bold),
            Paragraph("Reads <code>README.md</code>, <code>ENTERPRISE_SYSTEM_ARCHITECTURE.md</code>, and Docker Compose configurations.", table_cell),
            Paragraph("Maps 8 PostgreSQL tables, 7 containers, 2 daemons.", table_cell)
        ],
        [
            Paragraph("<b>3. Cloud &amp; Safety Verification</b>", table_cell_bold),
            Paragraph("Verifies SSH key <code>~/.ssh/ssh-key-2026-10-08.key</code> and tests cloud connectivity: <code>ssh ubuntu@80.225.252.145 \"docker ps\"</code>.", table_cell),
            Paragraph("Production containers active and healthy.", table_cell)
        ],
        [
            Paragraph("<b>4. Implementation &amp; Testing</b>", table_cell_bold),
            Paragraph("Edits project files, scripts, or schemas. Runs local test suites and verifies changes before touching production.", table_cell),
            Paragraph("Zero broken dependencies or syntax errors.", table_cell)
        ],
        [
            Paragraph("<b>5. Dual-Sync Deployment</b>", table_cell_bold),
            Paragraph("Commits changes to GitHub with <code>git push origin main</code> and pulls cleanly on VM 2 via SSH.", table_cell),
            Paragraph("GitHub and Cloud VM 2 in 100% lockstep.", table_cell)
        ]
    ]

    proto_table = Table(proto_data, colWidths=[105, 275, 160])
    proto_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(proto_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("5. Example Change Requests You Can Attach to the Prompt", h1_style))
    story.append(Paragraph(
        "Replace <code>[DESCRIBE YOUR DESIRED CHANGE OR TASK HERE]</code> in Section 5 of the prompt with any of these sample tasks:",
        body_style
    ))

    tasks_data = [
        [
            Paragraph("Objective", table_header),
            Paragraph("Ready-to-Use Prompt Snippet", table_header)
        ],
        [
            Paragraph("<b>Add New Monitoring Target</b>", table_cell_bold),
            Paragraph("<i>\"Add an HTTP health check prober for https://api.mycompany.com in prometheus/blackbox.yml and add a P2 alert rule in prometheus/alert.rules.yml if response time exceeds 500ms.\"</i>", table_cell)
        ],
        [
            Paragraph("<b>Modify Alert Thresholds</b>", table_cell_bold),
            Paragraph("<i>\"Change the router watchdog offline threshold from 3 missed pings to 5 missed pings, and adjust the Telegram notification cooldown from 5 minutes to 15 minutes.\"</i>", table_cell)
        ],
        [
            Paragraph("<b>Update Frontend Dashboard</b>", table_cell_bold),
            Paragraph("<i>\"Add a new metric card in frontend/index.html that displays 24-hour resolved incident counts and real-time router link latency graphs.\"</i>", table_cell)
        ],
        [
            Paragraph("<b>Perform Full Production Audit</b>", table_cell_bold),
            Paragraph("<i>\"SSH into 80.225.252.145, check Docker container health, review systemd logs for router-watchdog.service, and verify that the nightly cron backup ran successfully.\"</i>", table_cell)
        ],
        [
            Paragraph("<b>Database Schema Migration</b>", table_cell_bold),
            Paragraph("<i>\"Create an automated safety backup using scripts/backup_database.sh, then add an 'ip_address' column to the monitoring_targets table in schema.sql and backend models.\"</i>", table_cell)
        ]
    ]

    tasks_table = Table(tasks_data, colWidths=[130, 410])
    tasks_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(tasks_table)
    story.append(Spacer(1, 10))

    # Formal Sign-off Table
    signoff_data = [
        [
            Paragraph("<b>Document Title:</b> Antigravity AI Cold-Start Handover Specification", table_cell),
            Paragraph("<b>Classification:</b> Confidential — Engineering Operations", table_cell)
        ],
        [
            Paragraph("<b>Author:</b> Lead SRE / Infrastructure Operations", table_cell),
            Paragraph("<b>Audit Date:</b> October 10, 2026", table_cell)
        ]
    ]
    signoff_table = Table(signoff_data, colWidths=[270, 270])
    signoff_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(signoff_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] Handover Prompt PDF generated: {output_filename}")

if __name__ == "__main__":
    output = "ANTIGRAVITY_COLD_START_HANDOVER.pdf"
    if len(sys.argv) > 1:
        output = sys.argv[1]
    build_pdf(output)
