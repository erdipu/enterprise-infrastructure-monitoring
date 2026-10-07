# Enterprise Infrastructure Monitoring Platform: NOC Operations Guide

## 1. NOC Shift Engineer Workflow

As a Network Operations Center (NOC) Engineer, Infrastructure Specialist, or Monitoring Administrator, your primary duty is maintaining high system availability, enforcing SLAs, and driving fast Mean Time to Resolution (MTTR).

---

## 2. ITIL Incident Lifecycle & SLAs

```text
[ALERT FIRING] ──> [OPEN] ──> [ACKNOWLEDGED] ──> [IN PROGRESS] ──> [RESOLVED]
                     │
                     └── Auto-Resolution on Prometheus metric recovery
```

### 2.1 SLA Priority Matrix

| Priority | Criticality Level | Target Acknowledgment Time | Target Resolution Time (MTTR) | Typical Trigger |
|---|---|---|---|---|
| **P1** | **Critical Outage** | **< 5 minutes** | **< 60 minutes** | Host completely DOWN, Production Web Portal Down, Database Offline |
| **P2** | **High Degradation** | **< 15 minutes** | **< 120 minutes** | CPU > 80%, RAM > 85%, Disk > 85%, Redundant power supply failure |
| **P3** | **Medium Performance** | **< 30 minutes** | **< 4 hours** | Synthetic HTTP Latency > 1.5s, Load average elevated, packet drops |
| **P4** | **Low / Informational** | **< 2 hours** | **< 24 hours** | Non-critical service warnings, maintenance window reminders |

---

## 3. Step-by-Step Incident Handling Procedure

### Step 1: Detect & Acknowledge
1. Receive incoming incident via sound alert, Telegram notification, or NOC Portal screen.
2. Open the **NOC Web Portal** ([http://localhost:8000](http://localhost:8000)).
3. Navigate to **Incidents Queue**.
4. Click **Triage** on the incoming ticket.
5. Click **Acknowledge**:
   - This records the exact acknowledgment timestamp for SLA tracking and prevents duplicate escalations.

### Step 2: Correlate Metrics & Runbooks
1. Open the **Grafana Dashboard** ([http://localhost:3000](http://localhost:3000)).
2. Locate the affected host or URL.
3. Review related metrics to isolate the fault domain (CPU vs Memory vs Network vs Storage).
4. Open the matching Standard Operating Procedure (SOP) in `runbooks/`:
   - [high_cpu_sop.md](file:///Users/deepak_mamta/.gemini/antigravity/scratch/enterprise-infrastructure-monitoring/runbooks/high_cpu_sop.md)
   - [high_memory_sop.md](file:///Users/deepak_mamta/.gemini/antigravity/scratch/enterprise-infrastructure-monitoring/runbooks/high_memory_sop.md)
   - [high_disk_sop.md](file:///Users/deepak_mamta/.gemini/antigravity/scratch/enterprise-infrastructure-monitoring/runbooks/high_disk_sop.md)
   - [server_down_sop.md](file:///Users/deepak_mamta/.gemini/antigravity/scratch/enterprise-infrastructure-monitoring/runbooks/server_down_sop.md)
   - [website_down_sop.md](file:///Users/deepak_mamta/.gemini/antigravity/scratch/enterprise-infrastructure-monitoring/runbooks/website_down_sop.md)

### Step 3: Investigate & Document
1. Set incident status to **In Progress**.
2. Add diagnostic notes via the **Triage Comments** box:
   - Example: *"Logged into srv-linux-prod-01, observed batch query PID 2109 consuming 98% CPU. Contacted Database Team on-call."*
3. Execute approved remediation actions following the runbook.

### Step 4: Validate & Resolve
1. Confirm metric normalization on Grafana for at least 5 minutes.
2. In the NOC Portal incident modal:
   - Fill in **Root Cause Analysis (RCA)**: e.g., *"Unindexed batch query triggered runaway CPU lockup."*
   - Fill in **Resolution Notes**: e.g., *"Killed query PID 2109, added index idx_orders_created, CPU restored to 18%."*
3. Click **Resolve Incident**:
   - Status changes to `RESOLVED`.
   - Exact **MTTR** is computed and committed to PostgreSQL.
   - Outbound resolution notification is dispatched.
