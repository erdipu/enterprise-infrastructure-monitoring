-- ==============================================================================
-- Enterprise Infrastructure Monitoring & Incident Management Platform
-- Database Initialization & Seed Script (init.sql)
-- ==============================================================================

-- 1. Users & RBAC
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'operator', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- 2. Infrastructure Inventory (Servers)
CREATE TABLE IF NOT EXISTS servers (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(100) UNIQUE NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    os_type VARCHAR(20) NOT NULL CHECK (os_type IN ('linux', 'windows')),
    environment VARCHAR(20) NOT NULL DEFAULT 'production' CHECK (environment IN ('production', 'staging', 'development', 'dr')),
    status VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN' CHECK (status IN ('UP', 'DOWN', 'WARNING', 'UNKNOWN')),
    cpu_cores INT NOT NULL DEFAULT 4,
    total_ram_gb NUMERIC(6,2) NOT NULL DEFAULT 16.00,
    total_disk_gb NUMERIC(8,2) NOT NULL DEFAULT 250.00,
    last_check TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_servers_hostname ON servers(hostname);
CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);
CREATE INDEX IF NOT EXISTS idx_servers_os_type ON servers(os_type);

-- 3. Synthetic Probing Targets (Websites, Endpoints & APIs)
CREATE TABLE IF NOT EXISTS monitoring_targets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('host', 'website', 'api')),
    url_or_host VARCHAR(255) NOT NULL,
    port INT,
    check_interval_sec INT NOT NULL DEFAULT 30,
    expected_status_code INT NOT NULL DEFAULT 200,
    status VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN' CHECK (status IN ('UP', 'DOWN', 'UNKNOWN')),
    last_response_time_ms NUMERIC(8,2),
    last_check TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_targets_target_type ON monitoring_targets(target_type);
CREATE INDEX IF NOT EXISTS idx_targets_status ON monitoring_targets(status);

-- 4. Alert Ingestion & History (Direct from Alertmanager)
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    fingerprint VARCHAR(64) NOT NULL,
    alert_name VARCHAR(100) NOT NULL,
    target_name VARCHAR(100) NOT NULL,
    target_type VARCHAR(20) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'warning', 'info')),
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('P1', 'P2', 'P3', 'P4')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('firing', 'resolved')),
    summary TEXT NOT NULL,
    description TEXT,
    metric_value VARCHAR(50),
    threshold_value VARCHAR(50),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_priority ON alerts(priority);
CREATE INDEX IF NOT EXISTS idx_alerts_started_at ON alerts(started_at);

-- 5. ITIL Incident Management
CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    incident_number VARCHAR(30) UNIQUE NOT NULL,
    alert_id INT REFERENCES alerts(id) ON DELETE SET NULL,
    fingerprint VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('P1', 'P2', 'P3', 'P4')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('Critical', 'High', 'Medium', 'Low')),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED')),
    target_system VARCHAR(100) NOT NULL,
    alert_source VARCHAR(50) NOT NULL DEFAULT 'Prometheus',
    assigned_to_user_id INT REFERENCES users(id) ON DELETE SET NULL,
    root_cause TEXT,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    mttr_seconds INT
);

CREATE INDEX IF NOT EXISTS idx_incidents_number ON incidents(incident_number);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(priority);
CREATE INDEX IF NOT EXISTS idx_incidents_target ON incidents(target_system);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);

-- 6. Incident Collaboration & Audit Trail
CREATE TABLE IF NOT EXISTS incident_comments (
    id SERIAL PRIMARY KEY,
    incident_id INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    comment TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comments_incident_id ON incident_comments(incident_id);

-- 7. Notifications Log
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    incident_id INT REFERENCES incidents(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('email', 'telegram', 'local')),
    recipient VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('SENT', 'FAILED', 'PENDING')),
    payload TEXT NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_incident_id ON notifications(incident_id);

-- 8. Platform Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT,
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- ==============================================================================
-- SEED DATA INSERTION
-- ==============================================================================

-- Seed Users (Passwords use SHA256 / PBKDF2 hash formats compatible with FastAPI auth)
-- Password for admin: AdminPassword123!
-- Password for operator: OperatorPassword123!
-- Password for viewer: ViewerPassword123!
INSERT INTO users (username, email, hashed_password, full_name, role)
VALUES 
    ('admin', 'admin@monitoring.local', 'pbkdf2:sha256:260000$adminSalt$9f8352b21cf56b8e88e8940fe1c841804f5eecbbd1558c73d9c79e6022e03c2a', 'Infrastructure Admin', 'admin'),
    ('operator', 'noc@monitoring.local', 'pbkdf2:sha256:260000$opSalt$e67b2d354bfa3516584283842c388ef4d79ce9f35905d6e279f0fbdfcb4081c7', 'NOC Shift Engineer', 'operator'),
    ('viewer', 'stakeholder@monitoring.local', 'pbkdf2:sha256:260000$viewSalt$79a7852f08a506bf44b41a76c8c7d67f7e9140b9044ec3cceac49969695cf64d', 'Executive Viewer', 'viewer')
ON CONFLICT (username) DO NOTHING;

-- Seed Monitored Server Inventory
INSERT INTO servers (hostname, ip_address, os_type, environment, status, cpu_cores, total_ram_gb, total_disk_gb, last_check)
VALUES
    ('srv-linux-prod-01', '192.168.10.11', 'linux', 'production', 'UP', 8, 32.00, 500.00, CURRENT_TIMESTAMP),
    ('srv-linux-prod-02', '192.168.10.12', 'linux', 'production', 'UP', 8, 32.00, 500.00, CURRENT_TIMESTAMP),
    ('srv-win-ad-01', '192.168.10.21', 'windows', 'production', 'UP', 4, 16.00, 250.00, CURRENT_TIMESTAMP),
    ('srv-win-app-02', '192.168.10.22', 'windows', 'staging', 'WARNING', 4, 16.00, 250.00, CURRENT_TIMESTAMP)
ON CONFLICT (hostname) DO NOTHING;

-- Seed Synthetic Probing Targets
INSERT INTO monitoring_targets (name, target_type, url_or_host, port, check_interval_sec, expected_status_code, status, last_response_time_ms, last_check)
VALUES
    ('Production Web Portal', 'website', 'http://localhost:8000/health', 8000, 15, 200, 'UP', 185.40, CURRENT_TIMESTAMP),
    ('Core Payments REST API', 'api', 'http://localhost:8000/api/v1/health', 8000, 15, 200, 'UP', 92.10, CURRENT_TIMESTAMP),
    ('Customer Checkout Service', 'website', 'http://localhost:8000/api/v1/servers', 8000, 30, 200, 'UP', 210.00, CURRENT_TIMESTAMP)
ON CONFLICT (name) DO NOTHING;

-- Seed Historical Incidents for Immediate Dashboard & MTTR Metrics
INSERT INTO incidents (incident_number, fingerprint, title, description, priority, severity, status, target_system, alert_source, created_at, acknowledged_at, resolved_at, mttr_seconds, root_cause, resolution_notes)
VALUES
    ('INC-2026-0001', 'fp-disk-winapp02', 'Disk Space Utilization > 90% on D: Volume', 'High disk usage on srv-win-app-02 log drive exceeding 90% threshold', 'P2', 'High', 'RESOLVED', 'srv-win-app-02', 'Prometheus', CURRENT_TIMESTAMP - INTERVAL '2 hours', CURRENT_TIMESTAMP - INTERVAL '105 minutes', CURRENT_TIMESTAMP - INTERVAL '60 minutes', 2700, 'Accumulation of uncompressed application trace logs', 'Purged archive logs older than 14 days and restarted log compression agent.'),
    ('INC-2026-0002', 'fp-cpu-lnxprod01', 'High CPU Utilization > 85%', 'Host srv-linux-prod-01 sustained CPU load > 85% for 10 minutes', 'P3', 'Medium', 'RESOLVED', 'srv-linux-prod-01', 'Prometheus', CURRENT_TIMESTAMP - INTERVAL '5 hours', CURRENT_TIMESTAMP - INTERVAL '280 minutes', CURRENT_TIMESTAMP - INTERVAL '240 minutes', 2400, 'Batch reporting job concurrency spike', 'Adjusted cron job thread limits to 4 worker processes.'),
    ('INC-2026-0003', 'fp-mem-winad01', 'Memory Utilization Critical > 92%', 'Host srv-win-ad-01 available memory dropped below 8%', 'P2', 'High', 'ACKNOWLEDGED', 'srv-win-ad-01', 'Prometheus', CURRENT_TIMESTAMP - INTERVAL '25 minutes', CURRENT_TIMESTAMP - INTERVAL '15 minutes', NULL, NULL, 'Investigating memory leak in authentication caching pool', NULL);
