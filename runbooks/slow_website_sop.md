# Standard Operating Procedure (SOP): High Latency & Slow Endpoint Degradation

**Document ID**: SOP-INFRA-006  
**Category**: Application & Synthetic Availability  
**Alert Trigger**: `EndpointHighLatency` (`probe_duration_seconds > 1.5` for 2m → **P3 Medium**)

---

## 1. Initial Assessment & Triage
1. **Acknowledge Ticket**: Mark as `ACKNOWLEDGED`.
2. **Review Metrics**:
   - Check Grafana Probe Latency graph: What is current latency (e.g., 2.4s vs normal 200ms)?
   - Identify breakdown: Is delay in DNS resolution, TCP handshake, TLS negotiation, or TTFB (Time to First Byte)?

---

## 2. Investigation Steps
1. **Execute Detailed Curl Timing Breakdown**:
   ```bash
   curl -w "\nLookup: %{time_namelookup}s\nConnect: %{time_connect}s\nAppConnect: %{time_appconnect}s\nPreTransfer: %{time_pretransfer}s\nStartTransfer (TTFB): %{time_starttransfer}s\nTotal: %{time_total}s\n" -o /dev/null -s https://<target_url>
   ```
2. **Interpret Results**:
   - High `time_namelookup`: DNS server sluggishness or resolver failure.
   - High `time_starttransfer`: Backend application code, database query latency, or third-party API timeout.

3. **Check Database Query Performance**:
   - Check active database queries:
     ```sql
     SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
     FROM pg_stat_activity 
     WHERE state != 'idle' ORDER BY duration DESC LIMIT 5;
     ```

---

## 3. Remediation & Recovery Actions
1. **Slow Database Queries**:
   - Terminate blocking lock or hung query:
     ```sql
     SELECT pg_terminate_backend(<pid>);
     ```
2. **Worker Pool Exhaustion**:
   - Scale application concurrency or restart saturated worker threads.

---

## 4. Ticket Closure
1. Validate `time_total` returns below 500ms.
2. In NOC Portal, document root cause and resolve ticket.
