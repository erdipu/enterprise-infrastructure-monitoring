# Standard Operating Procedure (SOP): Filesystem & High Disk Space Utilization

**Document ID**: SOP-INFRA-003  
**Category**: Storage & Filesystem Health  
**Alert Triggers**:
- `HostDiskUtilizationCritical` (> 95% for 2 mins → **P1**)
- `HostDiskUtilizationWarning` (> 85% for 5 mins → **P2**)

---

## 1. Initial Assessment & Triage
1. **Acknowledge Ticket**: Mark incident as `ACKNOWLEDGED`.
2. **Review Metrics**:
   - In Grafana, check which mountpoint is saturating (`/`, `/var/log`, `/data`, `D:\`).
   - If disk reaches 100%, databases and logging services crash immediately.

---

## 2. Investigation Steps
1. **Connect to Host**:
   ```bash
   ssh admin@<hostname>
   ```

2. **Identify Saturated Filesystem & Inodes**:
   ```bash
   # Check disk space per partition
   df -h
   # Check inode exhaustion (too many zero-byte files)
   df -i
   ```

3. **Locate Largest Directories & Files**:
   ```bash
   # Find top 10 largest folders under the affected mount (e.g., /var):
   sudo du -xh /var | sort -rh | head -n 10

   # Find single files larger than 500MB:
   sudo find /var/log -type f -size +500M -exec ls -lh {} +
   ```

4. **Check for Deleted Files Still Held Open by Processes**:
   ```bash
   sudo lsof +L1
   ```

---

## 3. Remediation & Recovery Actions
1. **Purge Rotated / Old Application Logs**:
   ```bash
   # Remove archived gz logs older than 14 days:
   sudo find /var/log -type f -name "*.gz" -mtime +14 -delete
   # Vacuum systemd journal logs to retain max 500MB:
   sudo journalctl --vacuum-size=500M
   ```
2. **Clear Package Cache & Temporary Directories**:
   ```bash
   sudo apt-get clean || sudo yum clean all
   sudo rm -rf /tmp/*.tmp /var/tmp/*.tmp
   ```
3. **Truncate Runaway Active Log (Do NOT delete directly if process is writing)**:
   ```bash
   # Safely zero out an active log without breaking file descriptor:
   sudo truncate -s 0 /var/log/application_trace.log
   ```

---

## 4. Ticket Closure
1. Verify `df -h` shows utilization dropped below 80%.
2. Update incident in NOC Portal:
   - Status: `RESOLVED`
   - Document **Root Cause**: e.g., "Unrotated debug trace log accumulated 42GB in /var/log".
   - Document **Resolution Notes**: e.g., "Truncated trace log, verified logrotate configuration, free space restored to 34%".
