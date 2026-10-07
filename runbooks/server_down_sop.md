# Standard Operating Procedure (SOP): Host Outage (Server DOWN)

**Document ID**: SOP-INFRA-004  
**Category**: Critical Infrastructure Availability  
**Alert Trigger**: `HostDown` (`up == 0` for 1m → **P1 Critical**)

---

## 1. Initial Assessment & Triage
1. **P1 Protocol Activation**: Immediate priority! Acknowledge ticket within 5 minutes SLA.
2. **Alertmanager Inhibit Check**: Alertmanager will automatically suppress secondary CPU/Memory/Disk alerts to eliminate alert storming while host is down.

---

## 2. Investigation Steps
1. **Network Connectivity Verification**:
   ```bash
   ping -c 4 <ip_address>
   traceroute <ip_address>
   ```
2. **Port Reachability**:
   ```bash
   nc -zv -w 3 <ip_address> 22    # Linux SSH
   nc -zv -w 3 <ip_address> 3389  # Windows RDP
   ```
3. **Hypervisor / Cloud Console Inspection**:
   - Check VMware vCenter / ESXi console, Proxmox, or AWS/Azure EC2 state.
   - Verify power status (Powered ON vs Powered OFF).
   - Check host CPU/Memory metrics at hypervisor level: Is host kernel panicked, frozen, or blue-screened (BSOD)?
   - Review out-of-band management console (iLO / iDRAC).

---

## 3. Remediation & Recovery Actions
1. **Service Only Failed (Agent Down, OS Healthy)**:
   - If ping succeeds and SSH connects, Node Exporter service may have stopped:
     ```bash
     sudo systemctl status node_exporter
     sudo systemctl restart node_exporter
     ```
2. **OS Hard Freeze**:
   - Issue soft reboot from hypervisor console:
     ```bash
     virsh reboot <vm_name>
     ```
   - If unresponsive after 5 minutes, perform hard power reset:
     ```bash
     virsh reset <vm_name>
     ```
3. **Network Switch / VLAN Partition**:
   - If multiple hosts on same subnet alert simultaneously, escalate immediately to Network Engineering team on-call.

---

## 4. Ticket Closure
1. Wait for Prometheus to scrape target successfully (`up == 1`).
2. Verify Alertmanager emits `status: resolved`.
3. In NOC Portal:
   - Status: `RESOLVED`
   - Document **Root Cause**: e.g., "Hypervisor kernel panic following host migration".
   - Document **Resolution Notes**: e.g., "Hard reset completed via vCenter, filesystem integrity validated, all services operational".
