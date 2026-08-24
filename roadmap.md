# SysWatch v2.1 — Product Roadmap

> **Document owner:** Makarand Maha  
> **Last updated:** 25 August 2026  
> **Status:** v2.1 shipped (Flask + Jinja2, dark UI, AI insights, human-in-the-loop remediation)  
> **Repository:** https://github.com/tws-manumaha/SysWatch_v2.1

---

## Table of Contents

1. [Where SysWatch Stands Today](#1-where-syswatch-stands-today)
2. [M365-AI-SaaS-Toolkit — Repository Review](#2-m365-ai-saas-toolkit--repository-review)
3. [Integration Analysis: SysWatch x M365 Toolkit](#3-integration-analysis-syswatch--m365-toolkit)
4. [Recommended Integration Architecture](#4-recommended-integration-architecture)
5. [Roadmap Phase 1 — Stabilise and Harden (v2.2)](#5-roadmap-phase-1--stabilise-and-harden-v22)
6. [Roadmap Phase 2 — M365 Integration (v3.0)](#6-roadmap-phase-2--m365-integration-v30)
7. [Roadmap Phase 3 — Advanced AI and Automation (v3.5)](#7-roadmap-phase-3--advanced-ai-and-automation-v35)
8. [Roadmap Phase 4 — Ecosystem and Scale (v4.0)](#8-roadmap-phase-4--ecosystem-and-scale-v40)
9. [Feature Backlog — SysAdmin Wish List](#9-feature-backlog--sysadmin-wish-list)
10. [Summary Opinion](#10-summary-opinion)

---

## 1. Where SysWatch Stands Today

### What is SysWatch

SysWatch is a self-hosted, AI-enabled IT infrastructure monitoring platform built for sysadmins who want full control over their monitoring stack. It runs on-premises or in a private cloud, stores metrics in MySQL, and serves a Flask-based web UI with a dark slate / emerald-accent aesthetic.

### Current Capability Matrix (v2.1)

| Area | What exists | Maturity |
|---|---|---|
| **Host monitoring** | Cross-OS agent (psutil) for Linux, Windows, macOS; CPU, memory, disk, network, load, swap, processes, uptime | Production-ready |
| **Alerting** | Rule-based alert engine with thresholds, cooldowns, durations; severity levels (INFO, WARNING, CRITICAL); default rules seeded | Production-ready |
| **AI insights** | Anomaly detection (z-score baseline), multi-provider LLM support (OpenAI, Anthropic, Google, local Ollama), AI-generated remediation suggestions | Functional, needs tuning |
| **Human-in-the-loop** | All AI remediation requires explicit human approval; remote execution has approve/reject workflow | Production-ready |
| **Security** | JWT auth, bcrypt password hashing, API key auth, brute-force protection, AES-256-GCM credential encryption, input validation, module allowlist | Production-ready |
| **Web UI** | 11 Jinja2 templates: dashboard, hosts, host detail, alerts, events, AI insights, remote exec, reports, settings, login; Tailwind CSS via CDN | Functional, needs polish |
| **API** | 15 REST API blueprints covering hosts, alerts, events, AI, discovery, runbooks, SNMP, reporting, security, backups, users, notifications, cloud, agent, remote exec | Production-ready |
| **Database** | 31 tables in MySQL 8.0+ / MariaDB 10.6+; seed data for admin user, alert rules, system config | Production-ready |
| **Deployment** | Docker Compose (MySQL + Redis + Flask + Nginx), Let's Encrypt SSL, installers for Linux (systemd) and Windows (NSSM), cross-OS agent | Production-ready |
| **SNMP** | SNMP device polling (v1/v2c/v3), interface monitoring, device types (switch, router, firewall, AP, server) | Functional |
| **Cloud** | Cloud credential management (AWS, GCP, Azure), launch templates | Skeleton — needs provider-specific implementations |
| **Backup** | Automated backup scheduler with retention, checksums, metadata tracking | Production-ready |
| **Reporting** | Report generation (host summary, alert summary, AI analysis, security audit) in JSON, CSV, PDF, HTML | Functional |

### What SysWatch does NOT do yet

- No M365 / Azure AD / Entra ID integration
- No Windows Event Log or syslog collection
- No Docker container monitoring
- No Kubernetes monitoring
- No network topology mapping
- No Slack / Teams / Discord / email alert notifications (table exists, no sender)
- No mobile-responsive UI or PWA
- No multi-tenancy
- No SSO / OAuth / SAML
- No log aggregation (ELK-style)
- No configuration management drift detection
- No asset inventory / CMDB
- No patch management
- No capacity planning / forecasting

---

## 2. M365-AI-SaaS-Toolkit — Repository Review

### What it is

The M365-AI-SaaS-Toolkit is a PowerShell-centric management platform for Microsoft 365 environments. It wraps 241 PowerShell functions across 8 modules behind a Node.js / Express API, with JWT authentication and a basic web UI.

### Architecture summary

```
M365-AI-SaaS-Toolkit/
├── app/                          # Node.js Express backend
│   ├── server.js                 # Entry point (Express, port 3000)
│   ├── config/
│   │   ├── db.js                 # PostgreSQL connection pool (pg)
│   │   ├── auth.js               # JWT secret from env
│   │   └── modules.js            # Module registry
│   ├── engine/
│   │   ├── moduleLoader.js       # Dynamic module loader
│   │   └── powershellPool.js     # PowerShell process pool (spawn powershell.exe)
│   ├── middleware/
│   │   └── authMiddleware.js     # JWT authenticate + authorize(roles)
│   ├── modules/                   # 8 JS wrapper modules
│   │   ├── users.js, licensing.js, exchange.js, groups.js,
│   │   ├── teams.js, sharepoint.js, security.js (stub), reports.js (stub)
│   │   └── common.js             # Shared utilities
│   ├── routes/
│   │   ├── authRoutes.js         # Login/logout
│   │   ├── moduleRoutes.js       # CRUD for users module
│   │   ├── copilotRoutes.js      # AI copilot (keyword-based intent matching)
│   │   └── memoryRoutes.js       # In-memory state
│   └── services/                 # Stubs (copilot, logging, memory)
├── Licensing/Functions/           # 31 PowerShell functions
├── Modules/
│   ├── Users/Functions/           # 30 PowerShell functions
│   ├── Exchange/Functions/        # 30 PowerShell functions
│   ├── Groups/Functions/          # 30 PowerShell functions
│   ├── Teams/Functions/           # 31 PowerShell functions
│   ├── SharePoint/Functions/      # 29 PowerShell functions
│   ├── Security/Functions/        # 30 PowerShell functions (stubs)
│   └── Recovery/Functions/        # 30 PowerShell functions (stubs)
├── database/schema.sql            # Minimal (users + logs tables)
├── public/                        # Basic HTML UI
└── deployment/                    # nginx + pm2 + ssl-setup
```

### Module inventory

| Module | Functions | Key capabilities |
|---|---|---|
| **Licensing** | 31 | License assignment, removal, bulk operations, consumption tracking, alerts when >90% consumed, cleanup recommendations, health checks |
| **Users** | 30 | CRUD, bulk create/disable/enable/delete, password resets, alias management, session revocation, account lock/unlock, profile updates, export |
| **Exchange** | 30 | Mailbox CRUD, shared mailbox, permissions, forwarding, auto-reply, audit, rules, transport rules, size reporting, bulk operations |
| **Groups** | 30 | Security/O365/dynamic groups, member/owner management, bulk operations, orphan detection, guest cleanup, activity reports |
| **Teams** | 31 | Team CRUD, channel management, member/owner management, app management, archive/restore, guest management, bulk operations |
| **SharePoint** | 29 | Site CRUD, user management, permissions, storage, lists, sharing settings, file upload/download, deleted site recovery |
| **Security** | 30 | Stub functions (Invoke-SecurityTask1-30) — placeholders, not implemented |
| **Recovery** | 30 | Stub functions (Invoke-RecoveryTask1-30) — placeholders, not implemented |

### Technology stack

- **Backend:** Node.js + Express 4.18
- **Database:** PostgreSQL (pg 8.11)
- **Auth:** JWT (jsonwebtoken 9.0)
- **PowerShell execution:** `child_process.spawn('powershell.exe')` with per-user session pooling
- **Process management:** PM2
- **Reverse proxy:** Nginx with SSL

### Assessment

**Strengths:**
- Comprehensive PowerShell function library (241 functions, 6 fully implemented modules)
- Clean module/loader architecture — the `moduleLoader.js` + `powershellPool.js` pattern is sound
- Human-in-the-loop copilot concept (keyword-based, multi-step with confirmation)
- Covers M365 management comprehensively: licensing, users, Exchange, Groups, Teams, SharePoint

**Weaknesses:**
- Security and Recovery modules are stubs (60 placeholder functions doing nothing)
- PostgreSQL with a 2-table schema (just `users` and `logs`) — no audit trail, no execution history
- No encryption of M365 credentials — they sit in plaintext env vars
- The copilot uses hardcoded keyword matching, not actual AI/LLM
- No background scheduling — everything is on-demand
- No alerting or monitoring — it is purely a management tool
- Windows-only (spawns `powershell.exe`; no `pwsh` cross-platform support)
- No test suite
- Several service files are 18-byte stubs (copilot, logging, memory)
- In-memory state for copilot sessions (lost on restart)
- Only Users routes are wired in `moduleRoutes.js`; the other five modules are defined but not routed

---

## 3. Integration Analysis: SysWatch x M365 Toolkit

### The core question

Can these two projects be integrated into a single unified platform?

**Short answer: Yes, and they should be. They are highly complementary.**

### Why integration makes sense

SysWatch and the M365 Toolkit occupy two sides of the same sysadmin workflow:

```
  ┌─────────────────────────────────────────────────────┐
  │                    SysAdmin's Day                    │
  │                                                      │
  │   "Is something wrong?"          "Fix it."           │
  │         │                             │               │
  │    ┌────▼────┐                  ┌────▼────┐         │
  │    │ SysWatch │                  │  M365   │         │
  │    │  (alert) │ ──────────────►  │ Toolkit │         │
  │    │          │  "CPU 95% on    │ (remedy)│         │
  │    │          │   Exchange VM"   │         │         │
  │    └─────────┘                  └─────────┘         │
  │                                                      │
  │   Monitor + Alert ────────► Diagnose + Remediate     │
  └─────────────────────────────────────────────────────┘
```

- **SysWatch** answers: "Is something wrong?" (monitor, alert, anomaly detect)
- **M365 Toolkit** answers: "What should I do about it?" (manage, remediate, automate)

Together they form a complete **observe → detect → diagnose → remediate** loop — the exact workflow every sysadmin follows daily.

### Technical compatibility

| Dimension | SysWatch v2.1 | M365 Toolkit | Compatibility |
|---|---|---|---|
| **Language** | Python (Flask) | JavaScript (Node.js/Express) | Different runtimes — need bridge |
| **Database** | MySQL 8.0+ | PostgreSQL | Different — unify on MySQL |
| **Auth** | JWT + bcrypt + sessions | JWT (no bcrypt) | Compatible — adopt SysWatch's auth |
| **PowerShell** | Used for remote exec (paramiko/subprocess) | Used via `child_process.spawn` | Same concept — unify under Python `subprocess` |
| **Web UI** | Jinja2 + Tailwind (dark theme) | Plain HTML | Adopt SysWatch's UI |
| **AI** | Multi-provider LLM (OpenAI, Anthropic, Google, Ollama) | Keyword matching (not AI) | SysWatch's AI is strictly superior |
| **Scheduling** | APScheduler (background jobs) | None | SysWatch already has this |
| **Security** | AES-256-GCM encryption, brute-force protection | Plaintext credentials | SysWatch's security is production-grade |
| **Human-in-the-loop** | Full approve/reject workflow for remediation | Multi-step copilot confirmation | Compatible — merge concepts |

### Integration challenges

1. **Language gap:** SysWatch is Python; M365 Toolkit's API layer is Node.js. The 241 PowerShell functions themselves are language-agnostic (they are `.ps1`/`.txt` files). The Node.js wrapper is disposable — Python can call PowerShell directly via `subprocess`.

2. **Database gap:** M365 Toolkit uses PostgreSQL with a 2-table schema. SysWatch uses MySQL with 31 tables. Integration means porting the M365 data model into SysWatch's schema (adding M365-specific tables) and dropping PostgreSQL entirely.

3. **Credential management:** M365 Toolkit stores Azure AD app credentials in `.env` plaintext. SysWatch has AES-256-GCM encryption. The M365 tenant credentials must be migrated into SysWatch's encrypted credential store.

4. **PowerShell execution model:** M365 Toolkit's `powershellPool.js` maintains per-user PowerShell sessions. SysWatch's remote execution model is per-command via `subprocess`. The session pool concept is valuable for M365 (avoids re-authenticating to Microsoft Graph on every call) and should be ported to Python.

5. **Module maturity:** 60 of the 241 PowerShell functions are stubs. The 181 real functions cover Licensing, Users, Exchange, Groups, Teams, and SharePoint — these are the valuable ones.

### Integration verdict

**Feasibility: HIGH** — The PowerShell functions are the real asset. The Node.js layer is a thin wrapper that Python can replace. The integration work is:

1. Port the 181 real PowerShell functions into SysWatch's repository under `backend/modules/m365/`
2. Build a Python `powershell_pool.py` that maintains persistent PowerShell sessions (like the Node.js version)
3. Add M365-specific database tables to `schema.sql`
4. Create M365 API blueprints and web UI templates
5. Wire M365 alerts into SysWatch's existing alert engine and AI remediation pipeline

The result: a single Python/Flask application that monitors infrastructure AND manages Microsoft 365, with AI-powered diagnosis connecting the two.

---

## 4. Recommended Integration Architecture

```
SysWatch v3.0 (post-integration)
│
├── backend/
│   ├── app.py                          # Flask entrypoint
│   ├── schema.sql                      # Extended with M365 tables
│   ├── modules/
│   │   ├── (existing modules)           # config, database, security, etc.
│   │   ├── m365/                       # NEW — M365 integration
│   │   │   ├── __init__.py
│   │   │   ├── connection.py           # Microsoft Graph auth (app-only)
│   │   │   ├── powershell_pool.py      # Persistent PS sessions (port from Node.js)
│   │   │   ├── graph_client.py         # Direct Graph API calls (Python)
│   │   │   └── modules/
│   │   │       ├── users.py            # M365 user operations
│   │   │       ├── licensing.py        # License management
│   │   │       ├── exchange.py         # Mailbox operations
│   │   │       ├── groups.py           # Group operations
│   │   │       ├── teams.py            # Teams operations
│   │   │       └── sharepoint.py       # SharePoint operations
│   │   ├── api_m365.py                 # NEW — Flask blueprint for M365 API
│   │   └── web_ui/
│   │       ├── routes.py               # Extended with /m365 routes
│   │       └── templates/
│   │           ├── m365_dashboard.html # NEW
│   │           ├── m365_users.html     # NEW
│   │           ├── m365_licenses.html  # NEW
│   │           ├── m365_exchange.html  # NEW
│   │           ├── m365_teams.html     # NEW
│   │           └── m365_security.html  # NEW
│   └── powershell/                     # NEW — PowerShell scripts
│       ├── Connect-M365.ps1
│       ├── Users/
│       ├── Licensing/
│       ├── Exchange/
│       ├── Groups/
│       ├── Teams/
│       └── SharePoint/
│
├── agents/
│   └── syswatch_agent.py               # Existing (unchanged)
│
└── docker-compose.yml                  # Extended if needed
```

### Dual-path M365 access strategy

SysWatch v3.0 should access M365 via two paths, choosing the best for each operation:

1. **Microsoft Graph API (Python, direct)** — For read-heavy operations (list users, check license consumption, get mailbox sizes). This is fast, REST-based, needs no PowerShell, and works cross-platform. Uses `msal` library for app-only authentication.

2. **PowerShell (via `powershell_pool.py`)** — For operations that require PowerShell cmdlets not available via Graph (e.g., Exchange transport rules, SharePoint site management, some Teams operations). The pool maintains an authenticated session per tenant.

This dual-path approach means SysWatch v3.0 is not Windows-dependent. The PowerShell pool can use `pwsh` (PowerShell Core) on Linux, falling back to Graph API when PowerShell is unavailable.

---

## 5. Roadmap Phase 1 — Stabilise and Harden (v2.2)

**Timeline:** 4-6 weeks  
**Goal:** Make v2.1 production-grade before adding new capabilities.

### 5.1 Notification channels

Currently alerts are stored in the database but nothing pushes them out. SysWatch needs real notification delivery.

- Email notifications (SMTP) — configurable per-user, per-severity
- Slack webhook integration — post alerts to channels
- Microsoft Teams webhook — post to Teams channels (this becomes especially relevant after M365 integration)
- Discord webhook — for teams that use Discord
- PagerDuty webhook — for on-call escalation
- Webhook (generic) — user-defined URL + payload template

### 5.2 Real-time UI updates

- WebSocket (Flask-SocketIO) for live metric streaming on the dashboard
- Auto-refresh alert and event feeds without page reload
- Live status indicator in the sidebar (green pulse → red flash on new critical alert)

### 5.3 Dashboard improvements

- Time-range selector (1h, 6h, 24h, 7d, 30d) for charts
- Host grouping and filtering by group, OS, status
- Customisable dashboard widgets (drag-and-drop layout)
- Capacity planning charts (disk usage trend → projected exhaustion date)

### 5.4 Agent enhancements

- Windows Event Log collection (forward to SysWatch for AI analysis)
- Linux syslog forwarding (journald → SysWatch)
- Docker container metrics (container CPU, memory, network)
- Process-level monitoring (top N processes by CPU/memory)
- Agent auto-update mechanism

### 5.5 Security hardening

- SSO via OAuth2 (Google, Microsoft) and SAML
- TOTP-based 2FA for local logins
- Rate limiting on API endpoints
- API key scoping (per-key permissions)
- Session management UI (view/revoke active sessions)
- Password policy enforcement (complexity, rotation, history)

### 5.6 Testing and CI/CD

- Unit tests for core modules (database, security, alert_engine)
- Integration tests for API endpoints
- Docker-based end-to-end test environment
- GitHub Actions CI pipeline (lint, test, build, push image)
- Automated dependency vulnerability scanning

---

## 6. Roadmap Phase 2 — M365 Integration (v3.0)

**Timeline:** 8-12 weeks  
**Goal:** Integrate the M365-AI-SaaS-Toolkit into SysWatch as a first-class module.

### 6.1 M365 connection management

- Azure AD app registration guide (step-by-step in settings UI)
- Encrypted storage of tenant ID, client ID, client secret (using SysWatch's existing AES-256-GCM)
- Microsoft Graph authentication via `msal` library (Python)
- Connection health check (Graph API `/organization` endpoint)
- Multi-tenant support (manage multiple M365 tenants from one SysWatch instance)

### 6.2 PowerShell pool (Python port)

Port the `powershellPool.js` concept to Python:

```python
# backend/modules/m365/powershell_pool.py
class PowerShellPool:
    """Maintains persistent PowerShell sessions per tenant."""
    # Uses subprocess.Popen with stdin/stdout pipes
    # Supports both 'powershell.exe' (Windows) and 'pwsh' (Linux/macOS)
    # Session initialisation: Import-Module Microsoft.Graph, ExchangeOnline, Teams
    # Per-command execution with queue and timeout
```

### 6.3 M365 modules (port 181 real PowerShell functions)

Each module gets:
- A Python wrapper (`m365/modules/users.py`, etc.) that calls either Graph API or PowerShell
- An API blueprint (`api_m365.py`) exposing REST endpoints
- A web UI template with the dark slate / emerald theme
- Integration with SysWatch's audit log (every M365 action is logged)

| Module | Functions to port | Priority | Access method |
|---|---|---|---|
| Users | 24 (skip 6 empty stubs) | P0 | Graph API primary, PS for complex ops |
| Licensing | 31 | P0 | Graph API (subscribedSkus) |
| Exchange | 30 | P1 | PowerShell (ExchangeOnlineManagement) |
| Groups | 30 | P1 | Graph API primary |
| Teams | 31 | P2 | Graph API + PowerShell |
| SharePoint | 29 | P2 | PowerShell (PnP or SPO) |

### 6.4 M365-specific database tables

```sql
-- M365 tenant configuration
CREATE TABLE IF NOT EXISTS m365_tenants (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    tenant_id       VARCHAR(100) NOT NULL UNIQUE,
    client_id       VARCHAR(200) NOT NULL,
    client_secret_enc TEXT NOT NULL,
    client_secret_iv VARCHAR(64) NOT NULL,
    graph_endpoint  VARCHAR(200) DEFAULT 'https://graph.microsoft.com',
    is_active       BOOLEAN DEFAULT TRUE,
    last_synced     TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- M365 user cache (synced from Graph)
CREATE TABLE IF NOT EXISTS m365_users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id       INT NOT NULL,
    upn             VARCHAR(255) NOT NULL,
    display_name    VARCHAR(255),
    given_name      VARCHAR(100),
    surname         VARCHAR(100),
    job_title       VARCHAR(200),
    department      VARCHAR(200),
    office_location VARCHAR(200),
    usage_location  VARCHAR(10),
    account_enabled BOOLEAN DEFAULT TRUE,
    created_date    DATETIME,
    licenses        JSON,
    last_synced     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES m365_tenants(id) ON DELETE CASCADE,
    INDEX idx_m365user_upn (upn),
    INDEX idx_m365user_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- M365 license summary
CREATE TABLE IF NOT EXISTS m365_licenses (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id       INT NOT NULL,
    sku_id          VARCHAR(100) NOT NULL,
    sku_part_number VARCHAR(200),
    display_name    VARCHAR(300),
    consumed_units  INT DEFAULT 0,
    prepaid_units   INT DEFAULT 0,
    warning_ratio   DECIMAL(5,2) DEFAULT 0.90,
    last_synced     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES m365_tenants(id) ON DELETE CASCADE,
    UNIQUE KEY uk_tenant_sku (tenant_id, sku_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- M365 audit log (from Unified Audit Log)
CREATE TABLE IF NOT EXISTS m365_audit_events (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id       INT NOT NULL,
    record_type     VARCHAR(100),
    operation       VARCHAR(200),
    workload        VARCHAR(50),
    user_upn        VARCHAR(255),
    object_id       VARCHAR(255),
    result_status   VARCHAR(20),
    details         JSON,
    event_time      TIMESTAMP NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES m365_tenants(id) ON DELETE CASCADE,
    INDEX idx_m365audit_time (event_time DESC),
    INDEX idx_m365audit_user (user_upn),
    INDEX idx_m365audit_op (operation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- M365 execution history (all PS/Graph operations)
CREATE TABLE IF NOT EXISTS m365_executions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id       INT NOT NULL,
    module          VARCHAR(50) NOT NULL,
    action          VARCHAR(100) NOT NULL,
    params          JSON,
    result_status   ENUM('success','failed','partial') NOT NULL,
    output          TEXT,
    error           TEXT,
    execution_ms    INT,
    executed_by     VARCHAR(255) NOT NULL,
    approved_by     VARCHAR(255),
    executed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES m365_tenants(id) ON DELETE CASCADE,
    INDEX idx_m365exec_module (module),
    INDEX idx_m365exec_time (executed_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 6.5 M365 web UI templates

| Template | Purpose |
|---|---|
| `m365_dashboard.html` | M365 overview: tenant health, license consumption, active users, recent audit events |
| `m365_users.html` | User table with search, filter by license/status, bulk actions |
| `m365_licenses.html` | License consumption bars, alerts when >90%, cleanup recommendations |
| `m365_exchange.html` | Mailbox overview, large mailboxes, forwarding rules, audit |
| `m365_teams.html` | Team inventory, empty teams, guest users, activity |
| `m365_security.html` | M365 Secure Score, conditional access, sign-in risk, audit log |

### 6.6 AI-powered M365 insights

This is where the integration becomes genuinely powerful. SysWatch's existing AI engine extends to M365:

- **License optimisation AI:** "You have 15 unlicensed users and 3 disabled users with active licenses. Reclaiming those licenses saves Rs 4,500/month."
- **Security anomaly AI:** "User john.doe@example.com signed in from Mumbai at 9 AM and from Lagos at 11 AM — impossible travel detected."
- **Mailbox growth AI:** "The finance@ mailbox grew 2.3 GB in 7 days, 4x the normal rate. Suggest archiving items older than 2 years."
- **Teams sprawl AI:** "23 Teams have had zero activity in 60 days. Suggest archiving."
- **Remediation suggestions:** When SysWatch detects an on-prem Exchange server is overloaded (via the agent), the AI can suggest offloading to Exchange Online and present a one-click runbook to migrate mailboxes.

All AI suggestions flow through the existing human-in-the-loop approval workflow.

### 6.7 Cross-domain alerting

SysWatch can correlate infrastructure alerts with M365 events:

- If the on-prem Exchange VM is DOWN → check if Hybrid Exchange mail flow is affected → alert
- If disk is 95% full on a server → check if it hosts M365 AD Connect → alert that sync may fail
- If a domain controller is unreachable → alert that M365 password resets via AD Connect will fail
- If a monitored host is a SharePoint server → correlate SharePoint site health

---

## 7. Roadmap Phase 3 — Advanced AI and Automation (v3.5)

**Timeline:** 6-8 weeks  
**Goal:** Move from reactive AI (suggests actions) to proactive AI (predicts and prevents).

### 7.1 Predictive alerting

- CPU/memory trend forecasting using linear regression (already have the data)
- Disk exhaustion prediction ("at current rate, /var will fill in 12 days")
- M365 license exhaustion prediction ("at current growth, you'll exceed E5 licenses in 23 days")
- Seasonal anomaly detection (knows that Monday 9 AM CPU spikes are normal)

### 7.2 Natural language operations (AI Copilot)

Replace the M365 Toolkit's keyword-based copilot with a real LLM-powered one:

- "Show me all users who haven't logged in for 90 days" → queries Graph API, returns table
- "Reclaim unused licenses" → AI identifies, lists, asks for approval, executes
- "Why is server-db-01 slow?" → AI correlates metrics, identifies bottleneck, suggests fix
- "Migrate john.doe to Exchange Online" → AI generates runbook, asks for approval, executes step-by-step

### 7.3 Automated runbook generation

- AI generates runbooks based on recurring alert patterns
- "I've seen this disk-full issue 7 times this month. Shall I create a runbook?"
- Runbooks can include both infrastructure commands (Linux/Windows) and M365 operations
- Version-controlled runbook library with AI-assisted improvement suggestions

### 7.4 Log intelligence

- Parse Windows Event Logs and Linux syslog with AI for anomaly detection
- "7 failed login attempts on PROD-DC-01 in 2 minutes from 3 different IPs — likely brute force"
- Correlate log events across multiple hosts (lateral movement detection)
- M365 Unified Audit Log analysis (when integrated with M365 module)

### 7.5 Self-healing (with guardrails)

- Auto-approve LOW-risk remediation actions (e.g., clear /tmp when disk >90%)
- Auto-restart failed services (configurable per-service)
- Auto-scale resources when sustained high load detected
- All auto-actions are logged, reversible, and can be overridden

---

## 8. Roadmap Phase 4 — Ecosystem and Scale (v4.0)

**Timeline:** 10-14 weeks  
**Goal:** Make SysWatch the central nervous system of the entire IT estate.

### 8.1 Docker and Kubernetes monitoring

- Docker container metrics (CPU, memory, network per container)
- Docker host integration (Docker API → SysWatch agent)
- Kubernetes cluster monitoring (pod health, node pressure, deployment status)
- Container log streaming (stdout/stderr → SysWatch log intelligence)

### 8.2 Network topology mapping

- Auto-discover network topology via SNMP
- Visual network map (interactive D3.js or vis.js graph)
- Highlight bottleneck links and failing devices
- VLAN and subnet overlay

### 8.3 Asset inventory / CMDB

- Auto-discover hardware (manufacturer, model, serial, warranty)
- Track software installations and versions
- Track license compliance (tie into M365 license module)
- Dependency mapping (which services depend on which hosts)
- End-of-life tracking (hardware and software)

### 8.4 Configuration drift detection

- Baseline host configurations (packages installed, config files, services running)
- Detect unauthorised changes (new packages, modified configs, new services)
- Alert on drift with diff view
- Integration with Git for config version control

### 8.5 Patch management

- Detect available OS updates (Linux: apt/dnf, Windows: WSUS/Windows Update)
- Patch compliance dashboard
- Staged patching (test → staging → production)
- Maintenance window scheduling
- Pre/post patch health checks (run health check before and after patching)

### 8.6 Multi-tenancy

- Organisation-based isolation (each org sees only their hosts)
- Role-based access per org (a user can be admin in org A, viewer in org B)
- Shared global infrastructure (SysWatch server itself) visible to all
- Per-tenant M365 configuration

### 8.7 Mobile app / PWA

- Progressive Web App for mobile monitoring
- Push notifications for critical alerts
- Quick action buttons (acknowledge alert, approve/reject remediation)
- Biometric authentication (fingerprint/face)

### 8.8 Marketplace / plugin system

- Third-party integrations via plugin API (Zabbix, Nagios, Datadog import)
- Custom metric collectors (user-written Python scripts registered as plugins)
- Theme marketplace (custom dark/light themes)
- Community runbook library (share and import runbooks)

---

## 9. Feature Backlog — SysAdmin Wish List

Prioritised by impact and effort. Items marked with [M365] are specific to the M365 integration.

### High impact, low effort (quick wins)

| # | Feature | Effort | Impact |
|---|---|---|---|
| 1 | Email alert notifications (SMTP) | 2 days | High |
| 2 | Slack/Teams webhook alerts | 1 day | High |
| 3 | Dashboard time-range selector | 1 day | Medium |
| 4 | Host group filtering on dashboard | 0.5 day | Medium |
| 5 | Export host list / alert list as CSV | 0.5 day | Medium |
| 6 | Dark/light theme toggle | 1 day | Low |
| 7 | Password change on first login | 0.5 day | High |
| 8 | API rate limiting | 1 day | High |
| 9 | Session timeout warning | 0.5 day | Medium |
| 10 | Health check endpoint for load balancer | 0.5 day | High |

### High impact, medium effort

| # | Feature | Effort | Impact |
|---|---|---|---|
| 11 | WebSocket live updates (Flask-SocketIO) | 3 days | High |
| 12 | Docker container monitoring | 4 days | High |
| 13 | Windows Event Log collection | 3 days | High |
| 14 | Process-level monitoring (top N) | 2 days | Medium |
| 15 | SSO (Google / Microsoft OAuth2) | 3 days | High |
| 16 | TOTP 2FA | 2 days | High |
| 17 | [M365] Tenant connection + Graph auth | 3 days | High |
| 18 | [M365] User listing + search (Graph API) | 2 days | High |
| 19 | [M365] License dashboard | 2 days | High |
| 20 | [M365] PowerShell pool (Python port) | 4 days | High |

### High impact, high effort (major features)

| # | Feature | Effort | Impact |
|---|---|---|---|
| 21 | [M365] Full Users module (24 functions) | 2 weeks | High |
| 22 | [M365] Full Licensing module (31 functions) | 2 weeks | High |
| 23 | [M365] Exchange module (30 functions) | 2 weeks | High |
| 24 | [M365] Groups module (30 functions) | 1.5 weeks | Medium |
| 25 | [M365] Teams module (31 functions) | 1.5 weeks | Medium |
| 26 | [M365] SharePoint module (29 functions) | 1.5 weeks | Medium |
| 27 | [M365] Cross-domain alerting (infra x M365) | 1 week | High |
| 28 | [M365] AI-powered M365 insights | 2 weeks | High |
| 29 | Kubernetes monitoring | 3 weeks | High |
| 30 | Network topology mapping | 3 weeks | Medium |
| 31 | Asset inventory / CMDB | 4 weeks | High |
| 32 | Configuration drift detection | 3 weeks | Medium |
| 33 | Patch management | 4 weeks | High |
| 34 | Multi-tenancy | 4 weeks | Medium |
| 35 | Mobile PWA | 3 weeks | Medium |
| 36 | Predictive alerting (trend forecasting) | 2 weeks | High |
| 37 | Natural language AI copilot | 3 weeks | High |
| 38 | Self-healing automation | 2 weeks | High |

---

## 10. Summary Opinion

### On the M365 integration

The M365-AI-SaaS-Toolkit brings 181 real PowerShell functions covering six M365 workloads (Users, Licensing, Exchange, Groups, Teams, SharePoint). The Node.js wrapper around them is thin and disposable — the real value is in the PowerShell scripts themselves, which Python can invoke directly via `subprocess`.

**My recommendation: integrate it. Do not keep them as separate projects.**

The integration creates a unified platform that covers the full sysadmin lifecycle — monitor, alert, diagnose, remediate — for both on-premises infrastructure and Microsoft 365 cloud. This is genuinely valuable. No single open-source tool does both well today.

The technical path is clear:

1. **Phase 1 (v2.2):** Stabilise SysWatch — notifications, real-time UI, testing, security hardening. 4-6 weeks.
2. **Phase 2 (v3.0):** Integrate M365 — port PowerShell functions, build M365 API and UI, add AI-powered M365 insights. 8-12 weeks.
3. **Phase 3 (v3.5):** Advanced AI — predictive alerting, natural language copilot, self-healing. 6-8 weeks.
4. **Phase 4 (v4.0):** Ecosystem — Docker/K8s, CMDB, patch management, multi-tenancy, mobile. 10-14 weeks.

### On the M365 Toolkit's current state

The toolkit is about 60% complete. The six implemented modules (Users, Licensing, Exchange, Groups, Teams, SharePoint) have real, functional PowerShell functions. The Security and Recovery modules (60 functions) are empty stubs — they should either be implemented properly or dropped. The Node.js API layer only wires up the Users module; the other five are defined but not routed. The copilot is keyword-matching, not AI. The database is minimal (2 tables).

**However, the PowerShell function library itself is the asset.** Each function is a small, focused, well-named operation that maps to a real M365 management task. Porting these into SysWatch's Python + PowerShell hybrid model is straightforward, and SysWatch's existing infrastructure (encrypted credentials, audit logging, AI engine, human-in-the-loop approval, web UI) makes them immediately more useful than they are in the standalone toolkit.

### On what makes SysAdmins choose a tool

Sysadmins choose tools that reduce the number of dashboards they have to check. The promise of SysWatch v3.0 is that a sysadmin can see their Linux server CPU at 95%, their M365 license consumption at 90%, and their Exchange mailbox growth anomaly — all on one dashboard — and act on all three with AI-assisted remediation through a single approval workflow. That is a compelling proposition.

The roadmap above is ambitious but sequenced so that each phase delivers value independently. v2.2 makes the current product production-grade. v3.0 adds the M365 dimension. v3.5 adds intelligence. v4.0 adds scale.

---

*This roadmap is a living document. It should be revisited at the end of each phase and adjusted based on user feedback, new requirements, and the evolving threat landscape.*
