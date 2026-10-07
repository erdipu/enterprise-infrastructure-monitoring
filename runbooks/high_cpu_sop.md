# Standard Operating Procedure (SOP): High CPU Utilization

**Document ID**: SOP-INFRA-001  
**Category**: Compute / Infrastructure Performance  
**Alert Triggers**: 
- `HostCpuUtilizationCritical` (> 90% for 3 mins → **P1**)
- `HostCpuUtilizationWarning` (> 80% for 5 mins → **P2**)
- `HostHighLoadAverage` (Load > 4.0 for 5 mins → **P3**)

---

## 1. Initial Assessment & Triage
1. **Acknowledge the Incident**: Open the NOC Portal, locate the incident ticket, and change status to `ACKNOWLEDGED`.
2. **Review Metrics Telemetry**:
   - Check Grafana CPU graph: Is CPU pegged at 100% across all cores or a single core?
   - Compare with 1-min, 5-min, and 15-min load averages: Is this a transient spike or sustained saturation?
   - Check iowait percentage: High iowait indicates disk/storage bottleneck rather than user process computation.

---

## 2. Investigation Steps
1. **Connect to Host**:
   - **Linux**: Connect via SSH:
     ```bash
     ssh admin@<hostname>
     ```
   - **Windows**: Connect via RDP or PowerShell Remoting:
     ```powershell
     Enter-PSSession -ComputerName <hostname>
     ```

2. **Identify Top Consuming Processes**:
   - **Linux**:
     ```bash
     # Top CPU consuming processes sorted descending
     top -b -n 1 -o %CPU | head -n 20
     # Or using ps:
     ps aux --sort=-%cpu | head -n 10
     ```
   - **Windows**:
     ```powershell
     Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Id, ProcessName, CPU, WorkingSet
     ```

3. **Check Application Health & Logs**:
   - Verify whether the process is a legitimate critical service (database engine, Java application server, web worker) or a rogue runaway process.
   - Review recent deployments, cron jobs, or batch processing windows.

---

## 3. Remediation & Recovery Actions
1. **Runaway / Zombie Process**:
   - If identified as a hung script or unapproved batch job:
     ```bash
     kill -15 <PID>   # Graceful termination
     sleep 5
     kill -9 <PID>    # Force termination if unresponsive
     ```
2. **Approved Application Under Heavy Load**:
   - Do NOT terminate core production services without authorization.
   - Scale horizontal replicas if containerized.
   - Restart service only with Team Lead approval:
     ```bash
     sudo systemctl restart <service_name>
     ```
3. **Validate Normalization**:
   - Observe CPU utilization drop below 70% for at least 5 consecutive minutes in Grafana.

---

## 4. Ticket Closure & Post-Mortem
1. In the NOC Portal, update the ticket:
   - Status: `RESOLVED`
   - Document **Root Cause**: e.g., "Runaway reporting batch query PID 4128 consuming 98% CPU".
   - Document **Resolution Notes**: e.g., "Killed query process, optimized database index, confirmed CPU stabilized at 24%".
2. Ticket automatically calculates **MTTR**.
