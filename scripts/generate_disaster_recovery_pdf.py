#!/usr/bin/env python3
"""
Enterprise Infrastructure Monitoring Platform
Disaster Recovery, Portability & Business Continuity Specification PDF Generator
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
            self.drawRightString(612 - 36, 756, "DISASTER RECOVERY & CONTINUITY PLAN")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(36, 748, 612 - 36, 748)

            # Running Footer
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(36, 40, 612 - 36, 40)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(36, 28, "CONFIDENTIAL & PROPRIETARY — DISASTER RECOVERY SPECIFICATION")
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

    code_style = ParagraphStyle(
        'CodeStyle',
        fontName='Courier',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#0F172A")
    )

    checklist_item = ParagraphStyle(
        'ChecklistStyle',
        fontName='Helvetica',
        fontSize=7.5,
        leading=11,
        textColor=TEXT_DARK
    )

    story = []

    # =========================================================================
    # PAGE 1: TITLE, METADATA, EXECUTIVE OVERVIEW & COMPLETE GITHUB BACKUP
    # =========================================================================
    story.append(Paragraph("Enterprise Disaster Recovery &amp; Business Continuity Plan", title_style))
    story.append(Paragraph("Universal Device &amp; Service Monitoring Platform — Zero-Cost 3-2-1 Architecture", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=0, spaceAfter=8))

    # Metadata Summary Box (Width = 540)
    meta_data = [
        [
            Paragraph("<b>Target Domain:</b> Hybrid Cloud &amp; Edge Network", table_cell),
            Paragraph("<b>Document Version:</b> v1.0.0 (Enterprise Production)", table_cell)
        ],
        [
            Paragraph("<b>Repository:</b> github.com/erdipu/enterprise-infrastructure-monitoring", table_cell),
            Paragraph("<b>Production Host:</b> deepak-monitoring.duckdns.org (80.225.252.145)", table_cell)
        ],
        [
            Paragraph("<b>RTO (Recovery Time):</b> &lt; 15 min (PC) | &lt; 30 min (Cloud)", table_cell),
            Paragraph("<b>RPO (Recovery Point):</b> &lt; 24h (Nightly DB) | Instant (Git)", table_cell)
        ],
        [
            Paragraph("<b>Backup Architecture:</b> 3-2-1 Zero-Cost Storage", table_cell),
            Paragraph("<b>Security Policy:</b> Sanitized — Zero Secrets Committed", table_cell)
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

    story.append(Paragraph("1. Executive Overview &amp; Business Continuity Objectives", h1_style))
    story.append(Paragraph(
        "This specification establishes the authoritative Disaster Recovery Plan (DRP) and business continuity framework "
        "for the Universal Device &amp; Service Monitoring Platform. The objective is to guarantee <b>100% operational restoration "
        "and seamless development resumption</b> even in catastrophic events, including local PC loss, disk formatting, "
        "cloud instance termination, database corruption, or complete loss of AI conversation transcripts.",
        body_style
    ))

    core_obj_data = [
        [
            Paragraph(
                "<b>Guaranteed Recovery Commitments:</b><br/>"
                "• <b>Independent Rebuild:</b> Any engineer can deploy the platform from scratch on a brand-new machine in under 15 minutes.<br/>"
                "• <b>Zero Secrets Leakage:</b> Sensitive API tokens, private SSH keys, and database passwords are never exposed publicly on Git.<br/>"
                "• <b>Zero-Cost 3-2-1 Strategy:</b> Full disaster resilience is achieved using Oracle Cloud Always Free, GitHub, and free cloud storage.<br/>"
                "• <b>Verified Data Persistence:</b> Automated nightly database backups with 30-day retention and automated cryptographic verification.",
                callout_style
            )
        ]
    ]
    core_obj_table = Table(core_obj_data, colWidths=[540])
    core_obj_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BFDBFE")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(core_obj_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("2. Complete GitHub Backup &amp; Resource Inventory", h1_style))
    story.append(Paragraph(
        "All source code, telemetry daemons, database DDLs, monitoring rules, and engineering runbooks are centrally "
        "version-controlled in the repository: <code>https://github.com/erdipu/enterprise-infrastructure-monitoring.git</code>.",
        body_style
    ))

    repo_data = [
        [
            Paragraph("Component", table_header),
            Paragraph("Files / Path", table_header),
            Paragraph("Role &amp; Content", table_header),
            Paragraph("Status", table_header)
        ],
        [
            Paragraph("Backend API", table_cell_bold),
            Paragraph("<code>backend/</code>", table_cell),
            Paragraph("Flask REST API, 8 SQLAlchemy ORM models, auth routes, health endpoints", table_cell),
            Paragraph("100% Backed Up", table_cell_bold)
        ],
        [
            Paragraph("Frontend UI", table_cell_bold),
            Paragraph("<code>frontend/</code>", table_cell),
            Paragraph("HTML5/CSS3/Vanilla JS real-time operations dashboard, incident tables", table_cell),
            Paragraph("100% Backed Up", table_cell_bold)
        ],
        [
            Paragraph("Edge Daemons", table_cell_bold),
            Paragraph("<code>router_syslog_exporter.py<br/>router_watchdog.py</code>", table_cell),
            Paragraph("UDP 514 syslog ingest, :9125 telemetry exporter, 7-stage watchdog engine", table_cell),
            Paragraph("100% Backed Up", table_cell_bold)
        ],
        [
            Paragraph("Database DDL", table_cell_bold),
            Paragraph("<code>database/schema.sql<br/>database/init.sql</code>", table_cell),
            Paragraph("Complete 8-table PostgreSQL DDL, foreign keys, indexes, and seed records", table_cell),
            Paragraph("100% Backed Up", table_cell_bold)
        ],
        [
            Paragraph("Config Templates", table_cell_bold),
            Paragraph("<code>.env.example<br/>alert_config.example.json</code>", table_cell),
            Paragraph("Sanitized parameter templates without real passwords, bot tokens, or keys", table_cell),
            Paragraph("Sanitized", table_cell_bold)
        ],
        [
            Paragraph("Monitoring Stack", table_cell_bold),
            Paragraph("<code>prometheus/<br/>alertmanager/</code>", table_cell),
            Paragraph("Scrape configs, Blackbox probers, relabeling, and alert routing rules", table_cell),
            Paragraph("100% Backed Up", table_cell_bold)
        ],
        [
            Paragraph("DR Scripts", table_cell_bold),
            Paragraph("<code>scripts/*.sh<br/>scripts/*.py</code>", table_cell),
            Paragraph("PostgreSQL backup/restore engines, GZIP/SHA-256 verifiers, and offline packager", table_cell),
            Paragraph("Tested &amp; Verified", table_cell_bold)
        ],
        [
            Paragraph("Documentation", table_cell_bold),
            Paragraph("<code>docs/*.md<br/>README.md</code>", table_cell),
            Paragraph("6 DR guides, 6 ITIL SOP runbooks, setup manual, and system architecture PDF", table_cell),
            Paragraph("Complete", table_cell_bold)
        ]
    ]

    repo_table = Table(repo_data, colWidths=[80, 130, 245, 85])
    repo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(repo_table)

    # =========================================================================
    # PAGE 2: 3-2-1 BACKUP ARCHITECTURE & PC REBUILD GUIDE (<15 MIN)
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("3. 3-2-1 Zero-Cost Backup Architecture", h1_style))
    story.append(Paragraph(
        "To ensure complete resilience against concurrent local and cloud failures without ongoing subscription costs, "
        "the platform strictly adheres to the <b>3-2-1 Backup Rule</b>:",
        body_style
    ))

    strat_data = [
        [
            Paragraph("Storage Tier", table_header),
            Paragraph("Storage Medium", table_header),
            Paragraph("Backup Content &amp; Mechanism", table_header),
            Paragraph("Cost", table_header)
        ],
        [
            Paragraph("<b>Copy 1 (Primary Live)</b>", table_cell),
            Paragraph("OCI Cloud VM 2<br/>(80.225.252.145)", table_cell),
            Paragraph("Live production containers, PostgreSQL volume, automated nightly cron snapshots in <code>/home/ubuntu/.../backups</code>", table_cell),
            Paragraph("INR 0 (Always Free)", table_cell)
        ],
        [
            Paragraph("<b>Copy 2 (Version Control)</b>", table_cell),
            Paragraph("GitHub Remote<br/>(Git Cloud)", table_cell),
            Paragraph("Source code, DDL schemas, configurations, runbooks, documentation, and architecture PDF on branch <code>main</code>", table_cell),
            Paragraph("INR 0 (Free Tier)", table_cell)
        ],
        [
            Paragraph("<b>Copy 3 (Cold Offsite)</b>", table_cell),
            Paragraph("Encrypted Cloud Drive &amp;<br/>Air-Gapped USB", table_cell),
            Paragraph("Offline Git bundles (<code>.bundle</code>), source tarballs, AES-256 encrypted credential vaults, and verified SQL snapshots", table_cell),
            Paragraph("INR 0 (Google Drive 15GB + USB)", table_cell)
        ]
    ]

    strat_table = Table(strat_data, colWidths=[105, 105, 250, 80])
    strat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(strat_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Offline Standalone Packaging Utility", h2_style))
    story.append(Paragraph(
        "Running <code>bash scripts/create_offline_bundle.sh</code> creates a standalone offline package containing a complete "
        "Git bundle (100% history cloneable without internet) and clean source tarball with SHA-256 checksums.",
        body_style
    ))

    bundle_code = [
        [Paragraph("<b># Generate Standalone Offline Bundles (Runs on macOS, Linux, or Cloud VM):</b><br/>"
                   "bash scripts/create_offline_bundle.sh<br/>"
                   "<b># Output generated in dist_backups/:</b><br/>"
                   "• enterprise_monitoring_git_&lt;TIMESTAMP&gt;.bundle (Full Git history)<br/>"
                   "• enterprise_monitoring_full_&lt;TIMESTAMP&gt;.tar.gz (Clean source tree)<br/>"
                   "• *.sha256 (Cryptographic verification signatures)", code_style)]
    ]
    bundle_table = Table(bundle_code, colWidths=[540])
    bundle_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CODE_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(bundle_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("4. Step-by-Step PC Rebuild Guide (&lt; 15 Minutes RTO)", h1_style))
    story.append(Paragraph(
        "If your computer is formatted, damaged, or replaced with a completely new workstation, follow this exact sequence "
        "to restore access and resume engineering operations:",
        body_style
    ))

    steps_data = [
        [
            Paragraph("Phase", table_header),
            Paragraph("Action &amp; Commands", table_header),
            Paragraph("Execution Target", table_header)
        ],
        [
            Paragraph("<b>1. Base Tools</b>", table_cell),
            Paragraph("<b>macOS:</b> <code>brew install git python3 docker</code><br/>"
                      "<b>Windows:</b> Install Git for Windows, Docker Desktop, Python 3.11+<br/>"
                      "<b>Ubuntu:</b> <code>sudo apt update &amp;&amp; sudo apt install -y git python3 docker.io docker-compose-v2</code>", table_cell),
            Paragraph("New Local PC", table_cell)
        ],
        [
            Paragraph("<b>2. Clone Repo</b>", table_cell),
            Paragraph("<code>git clone https://github.com/erdipu/enterprise-infrastructure-monitoring.git<br/>cd enterprise-infrastructure-monitoring</code>", table_cell),
            Paragraph("Terminal / Shell", table_cell)
        ],
        [
            Paragraph("<b>3. Config Setup</b>", table_cell),
            Paragraph("<code>cp .env.example .env &amp;&amp; cp alert_config.example.json alert_config.json</code><br/>"
                      "Populate API tokens and passwords from Bitwarden Vault or encrypted backup.", table_cell),
            Paragraph("Repo Root", table_cell)
        ],
        [
            Paragraph("<b>4. Cloud SSH Key</b>", table_cell),
            Paragraph("Copy backed-up <code>ssh-key-2026-10-08.key</code> into <code>~/.ssh/</code> and run:<br/>"
                      "<code>chmod 600 ~/.ssh/ssh-key-2026-10-08.key</code>", table_cell),
            Paragraph("~/.ssh/ directory", table_cell)
        ],
        [
            Paragraph("<b>5. Verify Cloud</b>", table_cell),
            Paragraph("<code>ssh -i ~/.ssh/ssh-key-2026-10-08.key ubuntu@80.225.252.145 \"docker ps\"</code><br/>"
                      "Confirms production server connectivity and verifies 7 containers are healthy.", table_cell),
            Paragraph("Remote OCI VM", table_cell)
        ],
        [
            Paragraph("<b>6. Local Stack</b>", table_cell),
            Paragraph("<code>docker compose up -d</code><br/>"
                      "Spins up local PostgreSQL, Prometheus, Grafana, Alertmanager, and Backend API.", table_cell),
            Paragraph("Local Docker", table_cell)
        ]
    ]

    steps_table = Table(steps_data, colWidths=[80, 370, 90])
    steps_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(steps_table)

    # =========================================================================
    # PAGE 3: CATASTROPHIC FAILURE PROTOCOLS & DATABASE RECOVERY
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("5. Disaster Recovery Scenarios &amp; Action Matrix", h1_style))
    story.append(Paragraph(
        "Standard operating remediation procedures for catastrophic infrastructure and hardware failure scenarios:",
        body_style
    ))

    scen_data = [
        [
            Paragraph("Failure Scenario", table_header),
            Paragraph("Business Impact", table_header),
            Paragraph("Standard Recovery Action Plan", table_header),
            Paragraph("RTO", table_header)
        ],
        [
            Paragraph("<b>A. PC Destroyed / Lost</b>", table_cell_bold),
            Paragraph("Zero local code or tools", table_cell),
            Paragraph("Acquire new PC, follow Section 4 Rebuild Guide, clone GitHub repo, restore SSH key from Bitwarden.", table_cell),
            Paragraph("&lt; 15 min", table_cell)
        ],
        [
            Paragraph("<b>B. Cloud VM Terminated</b>", table_cell_bold),
            Paragraph("Production server down", table_cell),
            Paragraph("Launch new Ubuntu VM on Oracle/AWS, follow <code>docs/PROJECT_SETUP_GUIDE.md</code>, restore database snapshot using <code>scripts/restore_database.sh</code>.", table_cell),
            Paragraph("&lt; 30 min", table_cell)
        ],
        [
            Paragraph("<b>C. Database Corrupted</b>", table_cell_bold),
            Paragraph("Table data or schemas lost", table_cell),
            Paragraph("Execute <code>./scripts/restore_database.sh backups/eim_db_backup_latest.sql.gz</code>. Takes automatic pre-restore safety dump, drops locks, and restores 8 tables.", table_cell),
            Paragraph("&lt; 2 min", table_cell)
        ],
        [
            Paragraph("<b>D. GitHub Unavailable</b>", table_cell_bold),
            Paragraph("Remote repo inaccessible", table_cell),
            Paragraph("Clone from offline Git bundle: <code>git clone dist_backups/enterprise_monitoring_git_*.bundle repo</code>. All branches and commits are restored immediately.", table_cell),
            Paragraph("&lt; 3 min", table_cell)
        ],
        [
            Paragraph("<b>E. Secrets / Key Lost</b>", table_cell_bold),
            Paragraph("Loss of cloud access", table_cell),
            Paragraph("Access Bitwarden Vault or decrypt <code>platform_secrets_backup.enc</code>. Regenerate SSH key via Oracle Cloud Console Serial Console if needed.", table_cell),
            Paragraph("&lt; 10 min", table_cell)
        ],
        [
            Paragraph("<b>F. AI History Deleted</b>", table_cell_bold),
            Paragraph("Lost chat transcript", table_cell),
            Paragraph("100% of architecture, commands, and operations are preserved inside <code>README.md</code>, <code>docs/</code>, and this specification document.", table_cell),
            Paragraph("0 min", table_cell)
        ]
    ]

    scen_table = Table(scen_data, colWidths=[105, 95, 280, 60])
    scen_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(scen_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("6. Database Backup, Retention &amp; Resilient Restoration", h1_style))
    story.append(Paragraph(
        "The production database <code>monitoring_db</code> runs on PostgreSQL 15 and hosts 8 mission-critical tables: "
        "<code>users</code>, <code>servers</code>, <code>monitoring_targets</code>, <code>incidents</code>, <code>alerts</code>, "
        "<code>incident_comments</code>, <code>audit_logs</code>, and <code>notifications</code>.",
        body_style
    ))

    story.append(Paragraph("Automated Nightly Snapshotting &amp; Retention", h2_style))
    story.append(Paragraph(
        "An automated cron daemon executes nightly at 02:00 AM UTC on Cloud VM 2: "
        "<code>0 2 * * * /home/ubuntu/.../scripts/backup_database.sh &gt;&gt; /home/ubuntu/.../backups/backup.log 2&gt;&amp;1</code>. "
        "Backups are compressed with gzip and automatically purged after 30 days.",
        body_style
    ))

    db_ops_code = [
        [Paragraph(
            "<b># 1. Verify Backup Integrity (GZIP Decompression, 4/4 SQL Keywords, SHA-256):</b><br/>"
            "python3 scripts/verify_backup_integrity.py backups/eim_db_backup_20261010_121711.sql.gz<br/>"
            "<i>[+] File size: 8.60 KB | GZIP: Valid | Keywords: 4/4 Found | SHA-256: 5db8d5... | PASSED</i><br/><br/>"
            "<b># 2. Resilient Database Restoration (Includes Auto-Safety Backup &amp; Lock Release):</b><br/>"
            "./scripts/restore_database.sh backups/eim_db_backup_20261010_121711.sql.gz<br/>"
            "<i>[*] Auto-creates safety snapshot: backups/safety_snapshots/pre_restore_safety_&lt;ts&gt;.sql.gz<br/>"
            "[*] Terminates active client connections gracefully via pg_terminate_backend<br/>"
            "[*] Rebuilds schema &amp; imports data | Table count verified: 8 tables active</i>",
            code_style
        )]
    ]
    db_ops_table = Table(db_ops_code, colWidths=[540])
    db_ops_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CODE_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(db_ops_table)

    # =========================================================================
    # PAGE 4: CREDENTIALS VAULT, EMERGENCY CHECKLIST & AUDIT SIGNOFF
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("7. Credentials Vault &amp; Administrative Access Recovery", h1_style))
    story.append(Paragraph(
        "To protect infrastructure against credential theft while ensuring zero permanent lockouts:",
        body_style
    ))

    cred_data = [
        [
            Paragraph("Credential Item", table_header),
            Paragraph("Purpose &amp; Service", table_header),
            Paragraph("Secure Storage Location", table_header),
            Paragraph("Disaster Recovery Protocol", table_header)
        ],
        [
            Paragraph("<b>OCI SSH Private Key</b>", table_cell_bold),
            Paragraph("ssh-key-2026-10-08.key<br/>Access to Oracle VM 2", table_cell),
            Paragraph("Bitwarden Secure Note &amp;<br/>Encrypted USB flash drive", table_cell),
            Paragraph("Restore key text to <code>~/.ssh/</code>, set <code>chmod 600</code>. Or access via OCI Cloud Web Serial Console.", table_cell)
        ],
        [
            Paragraph("<b>Telegram Bot Token</b>", table_cell_bold),
            Paragraph("@my_infrastructure_alert_bot<br/>Real-time incident alerts", table_cell),
            Paragraph("Bitwarden Secure Note &amp;<br/><code>alert_config.json</code>", table_cell),
            Paragraph("Query Telegram <code>@BotFather</code> with <code>/token</code> to view or revoke/regenerate immediately.", table_cell)
        ],
        [
            Paragraph("<b>GitHub Access Token</b>", table_cell_bold),
            Paragraph("Personal Access Token (PAT)<br/>Git push authentication", table_cell),
            Paragraph("Bitwarden Password Manager", table_cell),
            Paragraph("Sign in to GitHub via 2FA authenticator app, go to Settings &gt; Developer Settings &gt; Tokens to generate new PAT.", table_cell)
        ],
        [
            Paragraph("<b>DuckDNS Token &amp; SMS</b>", table_cell_bold),
            Paragraph("Dynamic DNS updates &amp;<br/>Fast2SMS API engine", table_cell),
            Paragraph("Bitwarden Secure Note", table_cell),
            Paragraph("Log in to duckdns.org or fast2sms.com via email OTP to retrieve API keys instantly.", table_cell)
        ]
    ]

    cred_table = Table(cred_data, colWidths=[105, 120, 130, 185])
    cred_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(cred_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Encrypted Offline Secret Archive Command", h2_style))
    story.append(Paragraph(
        "To back up sensitive files into an AES-256 encrypted archive for USB cold storage: "
        "<code>tar -czf - .env alert_config.json | openssl enc -aes-256-cbc -pbkdf2 -salt -out platform_secrets.enc</code>. "
        "Decrypt anytime using: <code>openssl enc -d -aes-256-cbc -pbkdf2 -in platform_secrets.enc | tar -xzf -</code>.",
        body_style
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("8. Emergency Disaster Checklist &amp; Verification Drills", h1_style))
    story.append(Paragraph(
        "Print or maintain this action checklist for emergency recovery operations:",
        body_style
    ))

    checklist_data = [
        [
            Paragraph(
                "[  ] <b>1. CLONE REPOSITORY:</b> <code>git clone https://github.com/erdipu/enterprise-infrastructure-monitoring.git</code><br/>"
                "[  ] <b>2. RESTORE ENVIRONMENT:</b> Copy <code>.env.example</code> to <code>.env</code> and <code>alert_config.example.json</code> to <code>alert_config.json</code><br/>"
                "[  ] <b>3. RETRIEVE SECRETS:</b> Retrieve API tokens and bot credentials from Bitwarden or decrypt <code>platform_secrets.enc</code><br/>"
                "[  ] <b>4. RESTORE SSH KEY:</b> Place <code>ssh-key-2026-10-08.key</code> in <code>~/.ssh/</code> and run <code>chmod 600 ~/.ssh/ssh-key-2026-10-08.key</code><br/>"
                "[  ] <b>5. VERIFY PRODUCTION VM:</b> <code>ssh -i ~/.ssh/ssh-key-2026-10-08.key ubuntu@80.225.252.145 \"docker ps &amp;&amp; crontab -l\"</code><br/>"
                "[  ] <b>6. VERIFY TELEGRAM ALERTS:</b> Check alert endpoints at <code>http://deepak-monitoring.duckdns.org:9093/#/alerts</code><br/>"
                "[  ] <b>7. VERIFY LOCAL ENGINE:</b> Run <code>docker compose up -d</code> to verify local development stack",
                checklist_item
            )
        ]
    ]

    check_table = Table(checklist_data, colWidths=[540])
    check_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(check_table)
    story.append(Spacer(1, 10))

    # Audit sign-off box (Width = 540)
    signoff_data = [
        [
            Paragraph("<b>Prepared By:</b> Lead SRE / Infrastructure Operations", table_cell),
            Paragraph("<b>Classification:</b> Confidential — Engineering Operations", table_cell)
        ],
        [
            Paragraph("<b>Status:</b> Production Active &amp; Live Tested", table_cell),
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
    print(f"[SUCCESS] Disaster Recovery Plan PDF generated: {output_filename}")

if __name__ == "__main__":
    output = "DISASTER_RECOVERY_AND_BACKUP_PLAN.pdf"
    if len(sys.argv) > 1:
        output = sys.argv[1]
    build_pdf(output)
