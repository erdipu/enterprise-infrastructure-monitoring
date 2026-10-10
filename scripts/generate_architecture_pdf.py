import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
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
        
        # Omit header and footer on cover page
        if self._pageNumber > 1:
            # Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(40, 755, "ENTERPRISE INFRASTRUCTURE MONITORING & INCIDENT ESCALATION PLATFORM")
            self.setFont("Helvetica", 8)
            self.drawRightString(612 - 40, 755, "SYSTEM ARCHITECTURE SPECIFICATION")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(40, 747, 612 - 40, 747)

            # Footer
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(40, 42, 612 - 40, 42)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(40, 30, "CONFIDENTIAL & PROPRIETARY — INFRASTRUCTURE OPERATIONS")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(612 - 40, 30, page_text)
            
        self.restoreState()

def build_pdf(output_filename):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=55,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#0F172A")    # Slate 900
    SECONDARY = colors.HexColor("#1E3A8A")  # Blue 900
    ACCENT = colors.HexColor("#2563EB")     # Blue 600
    TEXT_DARK = colors.HexColor("#1E293B")  # Slate 800
    TEXT_MUTED = colors.HexColor("#475569") # Slate 600
    BG_LIGHT = colors.HexColor("#F8FAFC")   # Slate 50
    BORDER_LIGHT = colors.HexColor("#E2E8F0")# Slate 200
    SUCCESS = colors.HexColor("#16A34A")    # Green 600
    CRITICAL = colors.HexColor("#DC2626")   # Red 600

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=ACCENT,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1',
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK,
        spaceAfter=7
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK,
        spaceAfter=7
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=TEXT_DARK
    )

    table_header = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=TEXT_DARK
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=TEXT_DARK
    )

    story = []

    # =========================================================================
    # COVER / HEADER BLOCK
    # =========================================================================
    story.append(Spacer(1, 15))
    story.append(Paragraph("Enterprise Infrastructure Monitoring &amp; Incident Escalation Platform", title_style))
    story.append(Paragraph("Hybrid Cloud Production Architecture &amp; Operations Specification Document", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceBefore=0, spaceAfter=14))

    # Metadata Summary Box
    meta_data = [
        [
            Paragraph("<b>Target Domain:</b> Hybrid Cloud &amp; Edge On-Premises", table_cell),
            Paragraph("<b>Platform Version:</b> v2.4 (Production Active)", table_cell)
        ],
        [
            Paragraph("<b>Core Engine:</b> Python 3.10 / Prometheus / Grafana / OCI", table_cell),
            Paragraph("<b>Deployment Budget:</b> &#8377;0 (Always Free Tier)", table_cell)
        ],
        [
            Paragraph("<b>Notification Stack:</b> Telegram Bot / Gmail SMTP / Fast2SMS", table_cell),
            Paragraph("<b>Escalation Ladder:</b> 7-Stage Multi-Channel Matrix", table_cell)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[265, 265])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 1. EXECUTIVE SUMMARY
    # =========================================================================
    story.append(Paragraph("1. Executive Summary &amp; Business Objective", h1_style))
    story.append(Paragraph(
        "Modern enterprise operations require resilient, uninterrupted observability across geographically separated "
        "cloud nodes and edge infrastructure. When mission-critical edge gateways or cloud services experience hardware faults, "
        "power loss, or network partitions, operations teams require sub-second triage, precise SLA tracking, and multi-channel "
        "escalation while strictly eliminating false-positive alarm storms.",
        body_style
    ))
    story.append(Paragraph(
        "This platform delivers an autonomous, 100% open-source observability and ITIL incident escalation framework deployed "
        "across Oracle Cloud Infrastructure (OCI) and on-premises edge hardware. It operates 24/7 without requiring personal "
        "laptops or local computers to remain running, incurs <b>&#8377;0 recurring charges</b>, and provides guaranteed "
        "sub-15-second outage detection and sub-10-second recovery notifications.",
        body_style
    ))

    # =========================================================================
    # 2. MONITORED TARGETS
    # =========================================================================
    story.append(Spacer(1, 6))
    story.append(Paragraph("2. Monitored Infrastructure Targets", h1_style))
    
    target_data = [
        [
            Paragraph("Target ID", table_header),
            Paragraph("Device Role", table_header),
            Paragraph("Host &amp; Network Address", table_header),
            Paragraph("Telemetry Protocol", table_header),
            Paragraph("SLA Threshold", table_header)
        ],
        [
            Paragraph("<b>Target 1</b>", table_cell_bold),
            Paragraph("Secondary Router<br/>(TP-Link TL-WR845N v4)", table_cell),
            Paragraph("192.168.1.7<br/>MAC: D8:44:89:F5:41:FA<br/>(Edge Private LAN)", table_cell),
            Paragraph("Outbound UDP 514 Syslog<br/>Layer-2 Port 3 Forwarding", table_cell),
            Paragraph("Outage: &lt;15s<br/>Recovery: &lt;10s", table_cell_bold)
        ],
        [
            Paragraph("<b>Target 2</b>", table_cell_bold),
            Paragraph("Cloud Drive Server<br/>(Oracle Cloud VM 1)", table_cell),
            Paragraph("161.118.180.68<br/>deepak-cloud-drive.duckdns.org<br/>(Public Cloud)", table_cell),
            Paragraph("Synthetic HTTPS Blackbox<br/>HTTP 200 OK Probing", table_cell),
            Paragraph("Outage: &lt;15s<br/>Recovery: &lt;10s", table_cell_bold)
        ]
    ]
    t_table = Table(target_data, colWidths=[65, 115, 150, 120, 80])
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (-1,1), colors.white),
        ('BACKGROUND', (0,2), (-1,2), BG_LIGHT),
    ]))
    story.append(t_table)
    story.append(Spacer(1, 12))

    # =========================================================================
    # 3. HIGH-LEVEL TOPOLOGY & CGNAT TRAVERSAL
    # =========================================================================
    story.append(Paragraph("3. Network Topology &amp; Out-of-Band CGNAT Traversal", h1_style))
    story.append(Paragraph(
        "A critical engineering barrier in monitoring on-premises SOHO hardware from the public cloud is "
        "<b>Carrier-Grade NAT (CGNAT)</b>. Residential and branch broadband connections share dynamic public IP pools "
        "(e.g., <code>103.181.90.226</code>), with all inbound ports blocked by the ISP firewall. Standard cloud pollers "
        "are strictly unable to initiate incoming connections to <code>192.168.1.7</code>.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Architectural Solution:</b> Instead of inbound polling, the on-premises primary gateway (ZTE F670LV9) "
        "is configured to stream remote syslog telemetry <b>outbound</b> to Oracle Cloud VM 2 on UDP port 514. "
        "Outbound UDP effortlessly traverses CGNAT state tables. The secondary router is hardwired to physical "
        "<b>Port 3 (eth2)</b> of the gateway's internal bridge (<code>br0</code>). Every physical power cycle, unplug event, "
        "or auto-negotiation reset triggers an immediate sub-second kernel log packet to the cloud.",
        body_style
    ))

    # Highlight Callout
    callout_data = [[
        Paragraph(
            "<b>Key Architectural Benefit:</b> Zero client software or agent daemons are installed on home computers. "
            "Telemetry generation is offloaded 100% to the edge router hardware, enabling true 24/7 autonomous monitoring "
            "even when all local laptops and workstations are powered off.",
            callout_style
        )
    ]]
    callout_table = Table(callout_data, colWidths=[530])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#93C5FD")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 4. 7-STAGE ESCALATION LADDER
    # =========================================================================
    story.append(Paragraph("4. Corporate 7-Stage Escalation Ladder Specification", h1_style))
    story.append(Paragraph(
        "The incident watchdog engine (<code>router_watchdog.py</code>) enforces an exact multi-tier escalation ladder "
        "measured continuously from the precise onset timestamp of an infrastructure outage:",
        body_style
    ))

    ladder_data = [
        [
            Paragraph("Ladder Tier", table_header),
            Paragraph("Elapsed Downtime", table_header),
            Paragraph("Severity Level", table_header),
            Paragraph("Telegram &amp; Email Alert Subject", table_header),
            Paragraph("Operational SLA Action", table_header)
        ],
        [
            Paragraph("<b>Tier 1</b>", table_cell_bold),
            Paragraph("15 seconds", table_cell),
            Paragraph("<font color='#DC2626'><b>Critical</b></font>", table_cell),
            Paragraph("[1/7 OUTAGE] Immediate Outage Detected", table_cell_bold),
            Paragraph("Rapid triage alert dispatched to Telegram, Email, and SMS.", table_cell)
        ],
        [
            Paragraph("<b>Tier 2</b>", table_cell_bold),
            Paragraph("2 minutes (120s)", table_cell),
            Paragraph("<font color='#EA580C'><b>Major</b></font>", table_cell),
            Paragraph("[2/7 OUTAGE] Outage Confirmed", table_cell_bold),
            Paragraph("Confirms sustained outage; eliminates transient boot noise.", table_cell)
        ],
        [
            Paragraph("<b>Tier 3</b>", table_cell_bold),
            Paragraph("10 minutes (600s)", table_cell),
            Paragraph("<font color='#D97706'><b>Sustained</b></font>", table_cell),
            Paragraph("[3/7 OUTAGE] Outage Sustained", table_cell_bold),
            Paragraph("SLA breach warning; triggers engineering triage.", table_cell)
        ],
        [
            Paragraph("<b>Tier 4</b>", table_cell_bold),
            Paragraph("12 hours (43,200s)", table_cell),
            Paragraph("<font color='#B45309'><b>Major Extended</b></font>", table_cell),
            Paragraph("[4/7 OUTAGE] Major Extended Outage", table_cell_bold),
            Paragraph("Escalated notification for extended infrastructure loss.", table_cell)
        ],
        [
            Paragraph("<b>Tier 5</b>", table_cell_bold),
            Paragraph("24 hours (86,400s)", table_cell),
            Paragraph("<font color='#991B1B'><b>Severe Extended</b></font>", table_cell),
            Paragraph("[5/7 OUTAGE] Severe Extended Outage", table_cell_bold),
            Paragraph("Daily executive incident status notification.", table_cell)
        ],
        [
            Paragraph("<b>Tier 6</b>", table_cell_bold),
            Paragraph("1 week (604,800s)", table_cell),
            Paragraph("<font color='#7F1D1D'><b>Prolonged</b></font>", table_cell),
            Paragraph("[6/7 OUTAGE] Prolonged Outage - 1 Week", table_cell_bold),
            Paragraph("Long-term dormant infrastructure operational warning.", table_cell)
        ],
        [
            Paragraph("<b>Tier 7</b>", table_cell_bold),
            Paragraph("1 month (2.59M s)", table_cell),
            Paragraph("<font color='#450A0A'><b>Critical Dormant</b></font>", table_cell),
            Paragraph("[7/7 OUTAGE] Critical Dormant Host - 1 Mo", table_cell_bold),
            Paragraph("Final decommissioning or replacement trigger.", table_cell)
        ]
    ]
    ladder_table = Table(ladder_data, colWidths=[55, 95, 80, 175, 125])
    ladder_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(ladder_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 5. RECOVERY RULES & DEBOUNCING
    # =========================================================================
    story.append(Paragraph("5. Recovery Notification Rules &amp; Debouncing Protocol", h1_style))
    story.append(Paragraph(
        "To prevent alert storms and operator confusion during restoration, the platform enforces strict recovery rules:",
        body_style
    ))
    
    rec_data = [
        [
            Paragraph("Channel", table_header),
            Paragraph("Dispatch Volume", table_header),
            Paragraph("Format Specification &amp; Footer", table_header)
        ],
        [
            Paragraph("<b>Telegram Bot</b>", table_cell_bold),
            Paragraph("Strictly 1 Message", table_cell),
            Paragraph("<b>Header:</b> &#9989; [RESOLVED] INFRASTRUCTURE RECOVERED<br/>"
                      "<b>Metrics:</b> Device, Target, Status, Restored Timestamp, Downtime.<br/>"
                      "<b>Footer:</b> <i>All escalation alerts cleared. System operating normally.</i>", table_cell)
        ],
        [
            Paragraph("<b>Gmail SMTP</b>", table_cell_bold),
            Paragraph("Strictly 2 Emails", table_cell),
            Paragraph("<b>Email 1:</b> &#9989; [RESOLVED 1/2] &lt;Target&gt; Back Online (Immediate)<br/>"
                      "<b>Email 2:</b> &#9989; [RESOLVED 2/2] &lt;Target&gt; Telemetry Restored (+3s delay)", table_cell)
        ],
        [
            Paragraph("<b>Boot Flap Notice</b>", table_cell_bold),
            Paragraph("Transient Debounce", table_cell),
            Paragraph("If an Ethernet renegotiation flap occurs during cold boot (&lt;15s), "
                      "dispatches a clean <code>&#8505;&#65039; [SYSTEM INFO] BOOT LINK STABILIZED</code> notice on Telegram "
                      "with zero redundant emails.", table_cell)
        ]
    ]
    rec_table = Table(rec_data, colWidths=[100, 110, 320])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), SECONDARY),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(rec_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 6. PRODUCTION DEPLOYMENT & COMMANDS
    # =========================================================================
    story.append(Paragraph("6. Production Deployment &amp; Systemd Service Architecture", h1_style))
    story.append(Paragraph(
        "Both core background daemons run on Oracle Cloud VM 2 under native Linux <code>systemd</code> supervisors "
        "configured with automatic restart upon failure:",
        body_style
    ))

    svc_data = [
        [
            Paragraph("Service Name", table_header),
            Paragraph("Executable Path", table_header),
            Paragraph("Port Bindings", table_header),
            Paragraph("Role &amp; Responsibilities", table_header)
        ],
        [
            Paragraph("<code>router-syslog.service</code>", table_cell_bold),
            Paragraph("/home/ubuntu/router_syslog_exporter.py", table_cell),
            Paragraph("UDP 514 (Syslog)<br/>TCP 9125 (Prometheus)", table_cell),
            Paragraph("Ingests UDP syslog packets, parses bridge port states, exports Prometheus metrics.", table_cell)
        ],
        [
            Paragraph("<code>router-watchdog.service</code>", table_cell_bold),
            Paragraph("/home/ubuntu/router_watchdog.py", table_cell),
            Paragraph("Pulls :9125 &amp; :9090<br/>Direct HTTPS Probes", table_cell),
            Paragraph("Multi-target state machine, 7-stage escalation schedule, Telegram/SMTP dispatch.", table_cell)
        ]
    ]
    svc_table = Table(svc_data, colWidths=[130, 140, 110, 150])
    svc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(svc_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # 7. SECURITY & COST VERIFICATION
    # =========================================================================
    story.append(Paragraph("7. Security, Financial Budget &amp; SLA Compliance", h1_style))
    
    sec_data = [
        [
            Paragraph("<b>Total Monthly Cost:</b> &#8377;0.00 (100% Always Free Tier OCI)", table_cell_bold),
            Paragraph("<b>Target 1 Availability SLA:</b> 99.9% Target / Sub-15s Detection", table_cell_bold)
        ],
        [
            Paragraph("<b>Credential Storage:</b> Restricted 0600 JSON store (alert_config.json)", table_cell),
            Paragraph("<b>Target 2 Health Check:</b> Synthetic HTTP 200 OK Probe / 3s Interval", table_cell)
        ],
        [
            Paragraph("<b>Client Host Impact:</b> 0% CPU / Zero software on user laptops", table_cell),
            Paragraph("<b>Repository Status:</b> Synchronized on GitHub main branch", table_cell)
        ]
    ]
    sec_table = Table(sec_data, colWidths=[265, 265])
    sec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_LIGHT),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(sec_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "<i>Document finalized and certified for production infrastructure operations. "
        "Generated autonomously by Antigravity Engineering Systems.</i>",
        ParagraphStyle('Cert', fontName='Helvetica-Oblique', fontSize=8, textColor=TEXT_MUTED, alignment=1)
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {output_filename}")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "ENTERPRISE_SYSTEM_ARCHITECTURE.pdf"
    build_pdf(out)
