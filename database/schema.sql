-- ==============================================================================
-- Enterprise Infrastructure Monitoring & Incident Management Platform
-- PostgreSQL Relational Schema DDL
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
