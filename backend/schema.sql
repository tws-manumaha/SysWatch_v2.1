-- SysWatch v2.1 - Complete Database Schema
-- MySQL 8.0+ / MariaDB 10.6+
-- InnoDB engine, utf8mb4 charset

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- USERS & AUTHENTICATION
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    name            VARCHAR(200) DEFAULT '',
    password_hash   VARCHAR(255) NOT NULL,
    role            ENUM('viewer','operator','admin') NOT NULL DEFAULT 'viewer',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    last_login      TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS api_keys (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT,
    key_hash        VARCHAR(255) NOT NULL UNIQUE,
    key_prefix      VARCHAR(20) NOT NULL,
    name            VARCHAR(100) NOT NULL,
    last_used       TIMESTAMP NULL,
    expires_at      TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_api_keys_hash (key_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    expires_at      TIMESTAMP NOT NULL,
    revoked         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_tokens_hash (token_hash),
    INDEX idx_tokens_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS login_attempts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    ip_address      VARCHAR(45) NOT NULL,
    username        VARCHAR(255),
    user_agent      VARCHAR(500),
    success         BOOLEAN NOT NULL DEFAULT FALSE,
    attempted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_login_ip (ip_address),
    INDEX idx_login_user (username),
    INDEX idx_login_time (attempted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- HOSTS & HOST GROUPS
-- ============================================================
CREATE TABLE IF NOT EXISTS host_groups (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS hosts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    hostname        VARCHAR(255) NOT NULL,
    ip              VARCHAR(45) NOT NULL,
    os_type         ENUM('linux','windows','macos','freebsd','other') NOT NULL DEFAULT 'linux',
    status          ENUM('UP','DOWN','WARNING','UNREACHABLE','PENDING') NOT NULL DEFAULT 'PENDING',
    cpu_count       INT DEFAULT 0,
    memory_total_mb BIGINT DEFAULT 0,
    disk_total_gb   DECIMAL(10,2) DEFAULT 0,
    agent_version   VARCHAR(20),
    agent_key_hash  VARCHAR(255),
    ssh_port        INT DEFAULT 22,
    ssh_user        VARCHAR(100),
    ssh_password_enc TEXT,
    ssh_password_iv VARCHAR(64),
    ssh_key_enc     TEXT,
    ssh_key_iv      VARCHAR(64),
    winrm_port      INT DEFAULT 5985,
    winrm_user      VARCHAR(100),
    snmp_community  VARCHAR(100),
    snmp_port       INT DEFAULT 161,
    snmp_version    ENUM('v1','v2c','v3') DEFAULT 'v2c',
    group_id        INT,
    agent_installed BOOLEAN NOT NULL DEFAULT FALSE,
    ssh_accessible  BOOLEAN NOT NULL DEFAULT FALSE,
    winrm_accessible BOOLEAN NOT NULL DEFAULT FALSE,
    last_seen       TIMESTAMP NULL,
    discovered_by   VARCHAR(50),
    discovery_time  TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_hostname (hostname),
    INDEX idx_hosts_ip (ip),
    INDEX idx_hosts_status (status),
    INDEX idx_hosts_group (group_id),
    FOREIGN KEY (group_id) REFERENCES host_groups(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS host_credentials (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    host_id         INT NOT NULL,
    cred_type       ENUM('ssh_key','ssh_password','winrm','snmp_v3') NOT NULL,
    username        VARCHAR(100),
    encrypted_secret TEXT NOT NULL,
    encryption_iv   VARCHAR(64) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (host_id) REFERENCES hosts(id) ON DELETE CASCADE,
    INDEX idx_creds_host (host_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agent_keys (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    hostname        VARCHAR(255) NOT NULL,
    key_hash        VARCHAR(255) NOT NULL UNIQUE,
    key_prefix      VARCHAR(20) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used       TIMESTAMP NULL,
    INDEX idx_agent_keys_host (hostname)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- METRICS
-- ============================================================
CREATE TABLE IF NOT EXISTS metrics (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    hostname        VARCHAR(255) NOT NULL,
    cpu             DECIMAL(5,2) DEFAULT 0,
    memory          DECIMAL(5,2) DEFAULT 0,
    disk            DECIMAL(5,2) DEFAULT 0,
    net_in          BIGINT DEFAULT 0,
    net_out         BIGINT DEFAULT 0,
    load_1          DECIMAL(8,2) DEFAULT 0,
    load_5          DECIMAL(8,2) DEFAULT 0,
    load_15         DECIMAL(8,2) DEFAULT 0,
    processes       INT DEFAULT 0,
    uptime_seconds  BIGINT DEFAULT 0,
    swap_used       DECIMAL(5,2) DEFAULT 0,
    temperature     DECIMAL(5,2),
    custom_metrics  JSON,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_metrics_host_time (hostname, timestamp DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS metric_history (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    hostname        VARCHAR(255) NOT NULL,
    metric_name     VARCHAR(50) NOT NULL,
    value           DECIMAL(12,2) NOT NULL,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_history_host_metric_time (hostname, metric_name, timestamp DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- ALERTS & ALERT RULES
-- ============================================================
CREATE TABLE IF NOT EXISTS alert_rules (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    hostname        VARCHAR(255) NOT NULL DEFAULT '%',
    metric          VARCHAR(50) NOT NULL,
    operator        ENUM('>','<','>=','<=','=','!=') NOT NULL DEFAULT '>',
    threshold       DECIMAL(12,2) NOT NULL,
    severity        ENUM('INFO','WARNING','CRITICAL') NOT NULL DEFAULT 'WARNING',
    cooldown        INT NOT NULL DEFAULT 300,
    duration        INT NOT NULL DEFAULT 1,
    cause           TEXT,
    action          TEXT,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered  TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rules_enabled (enabled),
    INDEX idx_rules_hostname (hostname)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS alerts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    rule_id         INT,
    hostname        VARCHAR(255) NOT NULL,
    metric          VARCHAR(50) NOT NULL,
    value           DECIMAL(12,2) NOT NULL,
    threshold       DECIMAL(12,2) NOT NULL,
    operator        VARCHAR(5) NOT NULL,
    severity        ENUM('INFO','WARNING','CRITICAL') NOT NULL,
    status          ENUM('OPEN','ACKNOWLEDGED','RESOLVED') NOT NULL DEFAULT 'OPEN',
    cause           TEXT,
    action          TEXT,
    notes           TEXT,
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP NULL,
    resolved        BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_by     VARCHAR(255),
    resolved_at     TIMESTAMP NULL,
    triggered_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered  TIMESTAMP NULL,
    INDEX idx_alerts_status (status),
    INDEX idx_alerts_host (hostname),
    INDEX idx_alerts_severity (severity),
    INDEX idx_alerts_triggered (triggered_at DESC),
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    event_type      VARCHAR(50) NOT NULL,
    hostname        VARCHAR(255),
    source          VARCHAR(100),
    user            VARCHAR(255),
    details         JSON,
    event_time      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_events_time (event_time DESC),
    INDEX idx_events_type (event_type),
    INDEX idx_events_host (hostname)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- AI INSIGHTS & REMEDIATION
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_insights (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    hostname        VARCHAR(255) NOT NULL,
    metric          VARCHAR(50) NOT NULL,
    current_value   DECIMAL(12,2) NOT NULL,
    baseline_mean   DECIMAL(12,2) NOT NULL,
    baseline_std    DECIMAL(12,2) NOT NULL,
    deviation       DECIMAL(8,2) NOT NULL,
    severity        ENUM('INFO','WARNING','CRITICAL') NOT NULL DEFAULT 'WARNING',
    status          ENUM('OPEN','ACKNOWLEDGED','RESOLVED') NOT NULL DEFAULT 'OPEN',
    details         JSON,
    provider        VARCHAR(50),
    ai_analysis     TEXT,
    suggested_action TEXT,
    confidence      DECIMAL(5,4) DEFAULT 0,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_insights_status (status),
    INDEX idx_insights_host (hostname),
    INDEX idx_insights_time (timestamp DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS remediation_suggestions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    insight_id      INT,
    hostname        VARCHAR(255) NOT NULL,
    issue           TEXT NOT NULL,
    suggested_command TEXT NOT NULL,
    ai_explanation  TEXT,
    risk_level      ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'MEDIUM',
    status          ENUM('pending','approved','rejected','completed','failed') NOT NULL DEFAULT 'pending',
    approved_by     VARCHAR(255),
    approved_at     TIMESTAMP NULL,
    rejected_by     VARCHAR(255),
    rejected_at     TIMESTAMP NULL,
    executed_at     TIMESTAMP NULL,
    output          TEXT,
    exit_code       INT,
    generated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_remediation_status (status),
    INDEX idx_remediation_host (hostname),
    FOREIGN KEY (insight_id) REFERENCES ai_insights(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- REMOTE EXECUTION (renamed from remote_exec_requests)
-- ============================================================
CREATE TABLE IF NOT EXISTS remote_executions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    hostname        VARCHAR(255) NOT NULL,
    command         TEXT NOT NULL,
    requested_by    VARCHAR(255) NOT NULL,
    status          ENUM('pending','approved','rejected','running','completed','failed','timeout') NOT NULL DEFAULT 'pending',
    approved_by     VARCHAR(255),
    approved_at     TIMESTAMP NULL,
    rejected_by     VARCHAR(255),
    rejected_at     TIMESTAMP NULL,
    executed_at     TIMESTAMP NULL,
    completed_at    TIMESTAMP NULL,
    output          TEXT,
    error           TEXT,
    exit_code       INT,
    timeout_seconds INT DEFAULT 30,
    requested_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_remoteexec_status (status),
    INDEX idx_remoteexec_host (hostname)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- RUNBOOKS
-- ============================================================
CREATE TABLE IF NOT EXISTS runbooks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    category        VARCHAR(100) DEFAULT 'general',
    script_type     ENUM('bash','powershell','python') NOT NULL DEFAULT 'bash',
    script_content  TEXT,
    target_hosts    VARCHAR(500),
    created_by      VARCHAR(255),
    run_count       INT DEFAULT 0,
    last_run        TIMESTAMP NULL,
    last_run_status ENUM('success','failed','never') NOT NULL DEFAULT 'never',
    last_run_output TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS runbook_steps (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    runbook_id      INT NOT NULL,
    step_number     INT NOT NULL,
    action          VARCHAR(500) NOT NULL,
    command         TEXT,
    expected_result TEXT,
    FOREIGN KEY (runbook_id) REFERENCES runbooks(id) ON DELETE CASCADE,
    INDEX idx_steps_runbook (runbook_id),
    INDEX idx_steps_order (runbook_id, step_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS runbook_executions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    runbook_id      INT NOT NULL,
    executed_by     VARCHAR(255) NOT NULL,
    status          ENUM('running','completed','failed','cancelled') NOT NULL DEFAULT 'running',
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP NULL,
    output          TEXT,
    FOREIGN KEY (runbook_id) REFERENCES runbooks(id) ON DELETE CASCADE,
    INDEX idx_exec_runbook (runbook_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- NETWORK DISCOVERY
-- ============================================================
CREATE TABLE IF NOT EXISTS network_ranges (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    subnet          VARCHAR(50) NOT NULL,
    description     TEXT,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    last_scanned    TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ranges_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pending_hosts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    ip              VARCHAR(45) NOT NULL,
    hostname        VARCHAR(255),
    os_type         ENUM('linux','windows','macos','freebsd','other') DEFAULT 'linux',
    mac_address     VARCHAR(20),
    status          ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
    discovered_by   VARCHAR(50),
    discovered_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pending_status (status),
    INDEX idx_pending_ip (ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- SNMP DEVICES
-- ============================================================
CREATE TABLE IF NOT EXISTS snmp_devices (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    hostname        VARCHAR(255) NOT NULL,
    ip              VARCHAR(45) NOT NULL,
    device_type     ENUM('switch','router','firewall','access_point','server','other') NOT NULL DEFAULT 'other',
    community       VARCHAR(100) DEFAULT 'public',
    community_enc   TEXT,
    community_iv    VARCHAR(64),
    snmp_port       INT DEFAULT 161,
    snmp_version    ENUM('v1','v2c','v3') DEFAULT 'v2c',
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    status          ENUM('UP','DOWN','WARNING') NOT NULL DEFAULT 'UP',
    uptime_seconds  BIGINT DEFAULT 0,
    interfaces      JSON,
    sys_descr       TEXT,
    last_response   VARCHAR(500),
    last_polled     TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_snmp_host (hostname),
    INDEX idx_snmp_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- REPORTS
-- ============================================================
CREATE TABLE IF NOT EXISTS reports (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    report_type     ENUM('host_summary','alert_summary','ai_analysis','security_audit','custom') NOT NULL DEFAULT 'host_summary',
    parameters      JSON,
    file_path       VARCHAR(500),
    file_format     ENUM('json','csv','pdf','html') DEFAULT 'json',
    generated_by    VARCHAR(255),
    generated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_reports_type (report_type),
    INDEX idx_reports_time (generated_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT,
    type            ENUM('alert','ai_insight','remediation','system','security') NOT NULL DEFAULT 'alert',
    title           VARCHAR(255) NOT NULL,
    message         TEXT NOT NULL,
    severity        ENUM('INFO','WARNING','CRITICAL') NOT NULL DEFAULT 'INFO',
    source_id       INT,
    source_type     VARCHAR(50),
    read            BOOLEAN NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_notifs_user_read (user_id, read),
    INDEX idx_notifs_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- AUDIT LOG & APPLICATION LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(50),
    resource_id     VARCHAR(50),
    username        VARCHAR(255),
    ip              VARCHAR(45),
    user_agent      VARCHAR(500),
    status_code     INT,
    details         JSON,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_action (action),
    INDEX idx_audit_time (timestamp DESC),
    INDEX idx_audit_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS application_logs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level           VARCHAR(10) NOT NULL DEFAULT 'INFO',
    module          VARCHAR(100) NOT NULL,
    user_id         VARCHAR(255),
    hostname        VARCHAR(255),
    event_type      VARCHAR(100),
    message         TEXT NOT NULL,
    details         JSON,
    source_ip       VARCHAR(45),
    INDEX idx_applogs_time (timestamp DESC),
    INDEX idx_applogs_level (level),
    INDEX idx_applogs_module (module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- AI PROVIDER HEALTH
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_provider_health (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    provider        VARCHAR(50) NOT NULL,
    model           VARCHAR(100),
    api_key_present BOOLEAN NOT NULL DEFAULT FALSE,
    last_test_success BOOLEAN,
    last_test_at    TIMESTAMP NULL,
    last_test_latency_ms INT,
    last_error      TEXT,
    total_calls     INT DEFAULT 0,
    successful_calls INT DEFAULT 0,
    failed_calls    INT DEFAULT 0,
    priority        INT NOT NULL DEFAULT 99,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_provider (provider),
    INDEX idx_aihealth_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- BACKUP METADATA
-- ============================================================
CREATE TABLE IF NOT EXISTS backup_metadata (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    filename        VARCHAR(500) NOT NULL UNIQUE,
    size_bytes      BIGINT NOT NULL,
    status          ENUM('completed','failed','in_progress') NOT NULL DEFAULT 'completed',
    backup_type     ENUM('scheduled','manual','pre_update') NOT NULL DEFAULT 'scheduled',
    checksum        VARCHAR(64),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_backup_time (created_at DESC),
    INDEX idx_backup_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- SYSTEM CONFIG (key-value store)
-- ============================================================
CREATE TABLE IF NOT EXISTS system_config (
    config_key      VARCHAR(100) PRIMARY KEY,
    config_value    TEXT,
    description     VARCHAR(500),
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by      VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- CLOUD CREDENTIALS (encrypted)
-- ============================================================
CREATE TABLE IF NOT EXISTS cloud_credentials (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    provider        ENUM('aws','gcp','azure') NOT NULL,
    name            VARCHAR(100) NOT NULL,
    account_id      VARCHAR(200),
    region          VARCHAR(100),
    access_key_enc  TEXT,
    access_key_iv   VARCHAR(64),
    secret_key_enc  TEXT,
    secret_key_iv   VARCHAR(64),
    encrypted_data  TEXT,
    encryption_iv   VARCHAR(64),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_verified   TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cloudcred_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- LAUNCH TEMPLATES
-- ============================================================
CREATE TABLE IF NOT EXISTS launch_templates (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    provider        ENUM('aws','gcp','azure','docker') NOT NULL,
    instance_type   VARCHAR(50),
    image_id        VARCHAR(200),
    region          VARCHAR(50),
    security_groups JSON,
    user_data       TEXT,
    tags            JSON,
    disk_size_gb    INT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_templates_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- SEED DATA
-- ============================================================
INSERT INTO system_config (config_key, config_value, description) VALUES
    ('backup_schedule', '0 2 * * *', 'Cron schedule for automated backups'),
    ('backup_retention_days', '15', 'Number of days to retain backups'),
    ('backup_dir', '/var/backups/syswatch', 'Backup storage directory'),
    ('log_retention_days', '30', 'Number of days to retain application logs in DB'),
    ('alert_check_interval', '60', 'Seconds between alert rule evaluations'),
    ('host_check_interval', '120', 'Seconds between host status checks'),
    ('ai_analysis_interval', '300', 'Seconds between AI anomaly analysis runs'),
    ('snmp_poll_interval', '180', 'Seconds between SNMP polls'),
    ('enable_ssl', 'false', 'Enable HTTPS with Let Encrypt (apostrophe removed)'),
    ('ssl_domain', '', 'Domain name for Let Encrypt certificate'),
    ('ssl_email', '', 'Email for Let Encrypt registration'),
    ('cors_origins', '', 'Comma-separated allowed CORS origins'),
    ('session_timeout', '3600', 'Session timeout in seconds'),
    ('jwt_secret', '', 'JWT signing secret (auto-generated if empty)')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);

-- Default alert rules
INSERT INTO alert_rules (name, hostname, metric, operator, threshold, severity, cooldown, duration, cause, action, enabled) VALUES
    ('High CPU Usage', '%', 'cpu', '>', 90, 'CRITICAL', 300, 2, 'CPU usage exceeds 90% for 2 consecutive checks', 'Investigate top processes and load', TRUE),
    ('High Memory Usage', '%', 'memory', '>', 85, 'WARNING', 300, 2, 'Memory usage exceeds 85%', 'Check memory-consuming processes', TRUE),
    ('Disk Space Critical', '%', 'disk', '>', 90, 'CRITICAL', 600, 1, 'Disk usage exceeds 90%', 'Clean up disk space or add storage', TRUE),
    ('Host Unreachable', '%', 'status', '=', 0, 'CRITICAL', 60, 3, 'Host is not responding to checks', 'Verify network connectivity and host status', TRUE),
    ('High Load Average', '%', 'load_1', '>', 4, 'WARNING', 300, 3, 'Load average exceeds 4', 'Investigate system load and processes', TRUE)
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Default admin user (password: admin123)
-- CHANGE THIS PASSWORD IMMEDIATELY AFTER INSTALL
INSERT INTO users (email, name, password_hash, role, active) VALUES
    ('admin@syswatch.local', 'Administrator', '$2b$12$WMIvewSv2294a6WXA8DozuE0UvyMTztTq.k3yq1LwOliUgBrN0qUG', 'admin', TRUE)
ON DUPLICATE KEY UPDATE email = VALUES(email);

SET FOREIGN_KEY_CHECKS = 1;