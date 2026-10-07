# Enterprise Infrastructure Monitoring Platform: Configuration Guide

## 1. Adding New Infrastructure Monitoring Targets

### 1.1 Adding a New Linux or Windows Server
To monitor a new server running `node_exporter` (Linux) or `windows_exporter` (Windows):
1. Open `prometheus/prometheus.yml`.
2. Locate the `node_exporter` scrape job.
3. Append the new host to `static_configs`:
   ```yaml
   - job_name: 'node_exporter'
     scrape_interval: 15s
     static_configs:
       - targets: ['192.168.10.35:9100']
         labels:
           instance: 'srv-linux-billing-01'
           os_type: 'linux'
           environment: 'production'
           tier: 'database'
   ```
4. Reload Prometheus configuration without restarting the container:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```

---

### 1.2 Adding a New Website or API Endpoint
To monitor a new website or REST endpoint using synthetic Blackbox probing:
1. Open `prometheus/prometheus.yml`.
2. Locate the `blackbox_http` job.
3. Append the URL to the target list:
   ```yaml
   - job_name: 'blackbox_http'
     metrics_path: /probe
     params:
       module: [http_2xx]
     static_configs:
       - targets:
           - 'https://api.yourcompany.com/v1/health'
         labels:
           target_type: 'api'
           environment: 'production'
           service_name: 'Billing-REST-API'
   ```
4. Reload Prometheus: `curl -X POST http://localhost:9090/-/reload`.

---

## 2. Threshold Tuning & Custom Alert Rules

Alert rules are defined in `prometheus/alert.rules.yml`. Thresholds can be customized per environment tier.

### 2.1 Adjusting CPU Thresholds
To adjust the warning threshold from 80% to 85%:
```yaml
- alert: HostCpuUtilizationWarning
  expr: (100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 85
  for: 5m
  labels:
    severity: warning
    priority: P2
    target_type: host
  annotations:
    summary: "High CPU Utilization > 85% on {{ $labels.instance }}"
    description: "Host {{ $labels.instance }} CPU utilization is at {{ $value | printf \"%.2f\" }}%."
```

### 2.2 Adjusting Disk Thresholds
By default, the disk rule alerts when free space drops below 15% (85% utilized) or below 5% (95% utilized). To change the critical threshold to 90%:
```yaml
- alert: HostDiskUtilizationCritical
  expr: ((1 - (node_filesystem_free_bytes{fstype=~"ext4|xfs|ntfs"} / node_filesystem_size_bytes{fstype=~"ext4|xfs|ntfs"})) * 100) > 90
  for: 2m
  labels:
    severity: critical
    priority: P1
```

---

## 3. Configuring Alertmanager Routing & Notifications

Alertmanager configuration is maintained in `alertmanager/alertmanager.yml`.

### 3.1 Timing Controls
- `group_wait`: How long to wait before sending the first notification for a group of alerts (Default: `10s`).
- `group_interval`: How long to wait before sending a notification about new alerts in an existing group (Default: `30s`).
- `repeat_interval`: How long to wait before resending an unacknowledged alert notification (Default: `1h`).

### 3.2 Notification Channel Activation
Set environment variables in `.env` to enable real-time dispatch:

#### Telegram Setup
1. Create a bot using `@BotFather` and retrieve the token.
2. Obtain your chat ID using `@userinfobot`.
3. In `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRstuVWXyz"
   TELEGRAM_CHAT_ID="987654321"
   ```

#### Email (SMTP) Setup
1. In `.env`:
   ```bash
   SMTP_HOST="smtp.gmail.com"
   SMTP_PORT=587
   SMTP_USERNAME="alerts@yourdomain.com"
   SMTP_PASSWORD="app_specific_password_here"
   SMTP_FROM_EMAIL="alerts@yourdomain.com"
   ```
Restart the backend container to apply changes:
```bash
docker compose restart backend
```
