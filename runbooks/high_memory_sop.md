# Standard Operating Procedure (SOP): High Memory Utilization & OOM Risk

**Document ID**: SOP-INFRA-002  
**Category**: Memory / Capacity Management  
**Alert Triggers**:
- `HostMemoryUtilizationCritical` (> 92% for 2 mins → **P1**)
- `HostMemoryUtilizationWarning` (> 85% for 3 mins → **P2**)

---

## 1. Initial Assessment & Triage
1. **Acknowledge Ticket**: Mark incident as `ACKNOWLEDGED` in NOC Portal.
2. **Review Metrics**:
   - Check Grafana Memory panel: Is available memory decreasing monotonically (classic memory leak)?
   - Check Swap activity: High swap in/out indicates severe memory pressure, causing host thrashing.
   - Inspect dmesg/kernel logs for OOM-killer executions.

---

## 2. Investigation Steps
1. **Connect to Host**:
   ```bash
   ssh admin@<hostname>
   ```

2. **Inspect Memory Distribution**:
   - **Linux**:
     ```bash
     free -m
     # Check top processes sorted by Resident Set Size (RSS memory):
     ps aux --sort=-%mem | head -n 10
     ```
   - **Windows**:
     ```powershell
     Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Id, ProcessName, @{Name="RAM(MB)";Expression={[math]::Round($_.WorkingSet64/1MB,2)}}
     ```

3. **Check for OOM Killer Invocations**:
   ```bash
   dmesg -T | grep -i -E "oom-killer|out of memory|killed process"
   journalctl -k | grep -i oom
   ```

---

## 3. Remediation & Recovery Actions
1. **Immediate Pressure Relief**:
   - Drop system caches if buffers/cache are holding memory without dirty pages:
     ```bash
     sync; echo 3 | sudo tee /proc/sys/vm/drop_caches
     ```
2. **Application Memory Leaks**:
   - If a specific worker process is bloated, gracefully cycle the service worker pool:
     ```bash
     sudo systemctl reload <service_name>
     # Or restart if reload is unsupported:
     sudo systemctl restart <service_name>
     ```
3. **Long-Term Mitigation**:
   - Adjust JVM `-Xmx` heap limits or Python worker concurrency count.
   - Open capacity planning change request for RAM upgrade if baseline usage exceeds sizing.

---

## 4. Ticket Closure
1. Update incident in NOC Portal:
   - Status: `RESOLVED`
   - Document **Root Cause**: e.g., "JVM heap leak in customer indexing worker pool".
   - Document **Resolution Notes**: e.g., "Restarted worker service, applied heap bounds, memory stabilized at 48%".
