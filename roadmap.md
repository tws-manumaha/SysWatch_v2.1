# SysWatch v2.1 — Product Roadmap (Revised)

> **Document owner:** Makarand Maha  
> **Last updated:** 25 August 2026  
> **Status:** v2.1 shipped; M365 integration analysis complete after full codebase review  
> **Repositories:**  
> - SysWatch: https://github.com/tws-manumaha/SysWatch_v2.1  
> - M365 Toolkit: https://github.com/tws-manumaha/M365-AI-SaaS-Toolkit  
> **Supersedes:** Previous roadmap.md (which was based on the GitHub repo only, not the full uploaded codebase)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What the Full M365 Codebase Review Revealed](#2-what-the-full-m365-codebase-review-revealed)
3. [M365 Toolkit Evolution and Current State](#3-m365-toolkit-evolution-and-current-state)
4. [Integration Analysis: SysWatch x M365 Toolkit (Revised)](#4-integration-analysis-syswatch--m365-toolkit-revised)
5. [Recommended Integration Architecture (Revised)](#5-recommended-integration-architecture-revised)
6. [Roadmap Phase 1 — Stabilise and Harden (v2.2)](#6-roadmap-phase-1--stabilise-and-harden-v22)
7. [Roadmap Phase 2 — M365 Integration (v3.0)](#7-roadmap-phase-2--m365-integration-v30)
8. [Roadmap Phase 3 — Advanced AI and Automation (v3.5)](#8-roadmap-phase-3--advanced-ai-and-automation-v35)
9. [Roadmap Phase 4 — Ecosystem and Scale (v4.0)](#9-roadmap-phase-4--ecosystem-and-scale-v40)
10. [Feature Backlog](#10-feature-backlog)
11. [Summary Opinion](#11-summary-opinion)

---

## 1. Executive Summary

This is a revised roadmap based on a thorough review of the complete M365-AI-SaaS-Toolkit codebase — including 6 zip archives and 4 chat exports that were not available when the first roadmap was written. The review revealed that the M365 Toolkit is significantly more advanced than the GitHub repo suggested. The previous roadmap underestimated the toolkit's capabilities by treating Security and Recovery as empty stubs; in reality, both modules contain real, functional PowerShell scripts. The total count of real, implemented PowerShell functions is 90 (not 181 as previously stated), and the Node.js API layer has 49 fully wired REST endpoints across 8 modules (not 4 as on GitHub).

The core recommendation remains the same: **integrate the M365 Toolkit into SysWatch**, but the integration scope is now larger and the technical path is clearer. The V10 skeleton already implements Azure AD device-code authentication, an LLM-powered AI service, an audit logger, RBAC, rate limiting, and a secure PowerShell runner — all of which inform the integration design.

---

## 2. What the Full M365 Codebase Review Revealed

### The uploaded codebase vs. GitHub

The GitHub repository (`tws-manumaha/M365-AI-SaaS-Toolkit`) contains an early skeleton with stub service files, only 4 API routes (users only), and no real authentication. The uploaded zip files contain the full V10 codebase, which is a dramatically different and more mature codebase.

### What V10 has that GitHub does not

| Component | GitHub repo | V10 (uploaded) |
|---|---|---|
| **Authentication** | JWT secret in `.env` | Azure AD device-code flow via `@azure/msal-node`, multi-tenant session management, RBAC class |
| **API routes** | 4 (users only) | 49 endpoints across all 8 modules with `logAndRespond` audit wrapper |
| **Modules** | users.js (real), licensing/exchange/groups/teams/sharepoint.js (thin wrappers), security/reports/workflows.js (18-byte stubs) | All 8 modules fully implemented with 5-7 operations each, taking sessionId/tenantId/userId params |
| **AI/Copilot** | Keyword matching (`copilotRoutes.js`) | Full LLM-powered AI service (`aiService.js`, 12.7KB) with `processQuery`, `callAI`, `handleAction`, `executeAction`, `confirmAction` — maps natural language to module actions |
| **PowerShell execution** | `powershellPool.js` (raw `child_process.spawn`) | `securePowerShellRunner.js` using `node-powershell` library with per-session tenant connection, command queue, session lifecycle management |
| **Audit logging** | None | `auditLogger.js` — database-backed with `log()`, `getLogs()`, `createTable()` |
| **Security middleware** | Basic JWT verify | Helmet, CORS, rate limiting, RBAC permission checks |
| **Web UI** | Basic `index.html` (2.5KB) | Full SPA `index.html` (36.7KB) with device-code login flow, API testing panel, all module sections |
| **Recovery module** | 30 stub functions (`Invoke-RecoveryTask1-30.ps1`) | 15 real functions: `Restore-DeletedUser`, `Restore-DeletedMailbox`, `Undo-DisableUser`, `Get-ActionHistory`, etc. + 30 remaining stubs |
| **Security module** | 30 stub functions (`Invoke-SecurityTask1-30.ps1`) | 5 real functions: `Get-AuditLogs`, `Get-SecurityReport`, `Get-RiskyUsers`, `Get-SignInLogs`, `Get-ConditionalAccessPolicies` + 30 remaining stubs |
| **Reports module** | 18-byte stub | 6 report functions: user activity, license usage, group activity, SharePoint usage, Teams usage, export |
| **Database** | 2-table schema (users + logs) in PostgreSQL | Same minimal schema (this was identified as a weak point in the Copilot review) |
| **Deployment** | nginx + pm2 | nginx + pm2 + `tenant-setup.ps1` for M365 tenant configuration |

### Real PowerShell function count (corrected)

The previous roadmap stated "181 real functions." After reading every `.ps1` and `.txt` file in the V10 codebase, the actual count of real, implemented functions is:

| Module | Real functions | Stub/placeholder files | Key functions |
|---|---|---|---|
| **Users** | 29 | 3 | Get-M365Users, New-M365User, Disable-M365User, Reset-M365Password, Lock-User, Unlock-User, Revoke-Sessions, Bulk-CreateUsers, Bulk-DisableUsers, Export-M365Users, etc. |
| **Licensing** | 15 | 24 | Get-LicenseAlerts, Get-LicenseConsumption, Get-LicenseSkus, Get-UserLicenses, Assign-License, Remove-License, Get-UnlicensedUsers, Detect-LicenseOveruse, etc. |
| **Recovery** | 15 | 36 | Restore-DeletedUser, Restore-DeletedMailbox, Restore-DeletedGroup, Restore-DeletedTeam, Undo-DisableUser, Undo-ResetPassword, Get-ActionHistory, etc. |
| **Groups** | 11 | 16 | Get-Groups, New-Group, Add-GroupMember, Add-GroupOwner, Get-GroupMembers, Get-EmptyGroups, Get-DynamicGroups, etc. |
| **Exchange** | 7 | 23 | Get-Mailboxes, Get-MailboxStatistics, Get-MailboxPermissions, Get-MailboxSize, Get-SharedMailboxes, Get-UserMailbox, Add-MailboxPermission |
| **Security** | 5 | 31 | Get-AuditLogs, Get-SecurityReport, Get-RiskyUsers, Get-SignInLogs, Get-ConditionalAccessPolicies |
| **Teams** | 4 | 27 | Get-Teams, Get-TeamChannels, Get-TeamUsers (most Teams functions are small .ps1 wrappers, not fully implemented) |
| **SharePoint** | 4 | 53 | Get-Sites, Get-SiteStorage (most SP functions are small .ps1 wrappers) |
| **TOTAL** | **90** | **213** | |

### PowerShell code quality (from reading the actual scripts)

The real functions follow a consistent, professional pattern:
- `[CmdletBinding()]` with `SupportsShouldProcess` for destructive operations
- `begin/process/end` block structure
- Input validation (UPN format regex checking)
- Pre-existence checks (verify user exists before disabling)
- `try/catch` with structured `[PSCustomObject]` return: `@{ Success=$true; Message="..."; Data=$result }`
- `Export-ModuleMember -Function` at the end
- `Write-Verbose` for diagnostic logging
- `WHATIF` support for `-WhatIf` parameter

This is significantly better quality than the GitHub repo suggested. The functions are production-grade PowerShell with proper error handling, validation, and structured output.

### What the Copilot chat exports revealed

The chat exports (from Microsoft Copilot sessions) document the project's architecture review and roadmap discussion. Key points from the Copilot assessment:

1. The project was assessed at **60-70% production readiness**
2. **10 critical weak points** were identified: M365 auth gap, script quality inconsistency, no standard output contract, database unused, Copilot only partial, security basic, no user/session model, no execution governance, frontend minimal, no observability
3. A **5-phase fix roadmap** was proposed: Fix M365 authentication, Standardize scripts, Integrate database, Upgrade Copilot to real assistant, Add logging and monitoring
4. The user (Makarand) explicitly pushed back on the AI "skipping layers and assuming structure" — demanding a disciplined, validate-before-build approach
5. A professional Word document (`M365_Platform_Review_and_Roadmap.docx`) was created for a team meeting

The project vision, as documented in the V6 Master Guide, follows enterprise-grade principles: Zero Trust, MFA-first authentication, RBAC, secure logging, Microsoft Graph API (no legacy modules), and no stored passwords.

---

## 3. M365 Toolkit Evolution and Current State

### Version history (reconstructed from file evidence)

| Version | What it was | Evidence |
|---|---|---|
| V1-V3 | Simple PowerShell scripts (one-liners and small functions) | `M365_Readme_V1/V2/V3.txt`, `M365_PowerShell_Toolkit.txt` |
| V5 | Enterprise toolkit with GUI dashboard, RBAC, automation | `M365_V5_Enterprise.zip` |
| V6 | "Secure Graph Toolkit" — Graph API only, MFA, no legacy modules, GUI + CLI, logging, RBAC | `M365_V6_Final_Toolkit.zip`, `M365_V6_Master_Guide.txt`, `README_M365_V6.md` |
| V7 | Web starter project (Node.js + Express) | `M365_V7_Complete_Repo.zip`, `M365_V7_Full_Enterprise.zip`, `M365_Web_Starter_Project.zip` |
| V10 (Skeleton) | Full platform: Node.js + Express + 8 modules + 49 API routes + AI service + device-code auth + secure PowerShell runner + audit logger + RBAC + rate limiting + 90 real PS functions + web SPA | `M365_PLATFORM_SKELETON_V10.zip` |

### Architecture at V10

```
M365 Platform V10
|
+-- app/
|   +-- server.js                    # Express with CORS, rate limiting, static files
|   +-- server-with-DB.js            # Enhanced version with helmet, DB routes, all middleware
|   +-- auth/
|   |   +-- azureAuth.js             # MSAL device-code flow, session management, user/group lookup
|   |   +-- multiTenantAuth.js       # Per-tenant session management
|   |   +-- rbac.js                  # Role-based access control manager
|   +-- engine/
|   |   +-- powershellPool.js        # Legacy PowerShell pool (spawn-based)
|   |   +-- securePowerShellRunner.js # New: node-powershell library, per-tenant sessions
|   |   +-- moduleLoader.js          # Dynamic module loader
|   +-- routes/
|   |   +-- moduleRoutes.js          # 49 REST endpoints (33.5KB, 1003 lines)
|   |   +-- aiRoutes.js             # AI assistant: /ask, /confirm, /clear
|   |   +-- copilotRoutes.js         # Legacy keyword copilot: /ask, /select, /confirm, /execute
|   |   +-- authRoutes.js           # Device-code: /device/initiate, /device/poll, /session/validate, /logout
|   +-- modules/
|   |   +-- users.js (6 ops)         # getAllUsers, getUserDetails, disableUser, enableUser, createUser, resetPassword
|   |   +-- licensing.js (6 ops)     # getLicenseSkus, getUserLicenses, assignLicense, removeLicense, getUnlicensedUsers, getLicenseConsumption
|   |   +-- exchange.js (6 ops)     # getMailboxes, getMailboxDetails, enableMailbox, disableMailbox, createMailbox, getMailboxStatistics
|   |   +-- groups.js (6 ops)       # getGroups, getMembers, createGroup, addMember, removeMember, deleteGroup
|   |   +-- teams.js (7 ops)        # getTeams, getChannels, createTeam, addUser, removeUser, archiveTeam, unarchiveTeam
|   |   +-- sharepoint.js (6 ops)   # getSites, getSiteDetails, createSite, removeSite, addUser, removeUser
|   |   +-- security.js (5 ops)     # getAuditLogs, getSignInLogs, getSecurityReport, getRiskyUsers, getConditionalAccessPolicies
|   |   +-- reports.js (6 ops)      # getUserActivityReport, getLicenseUsageReport, getGroupActivityReport, getSharePointSiteUsage, getTeamsUsageReport, exportReport
|   |   +-- admin.js (1 op)         # exportLogs
|   +-- services/
|   |   +-- aiService.js             # LLM-powered AI (12.7KB): processQuery, callAI, handleAction, executeAction, confirmAction
|   +-- utils/
|   |   +-- auditLogger.js          # DB-backed audit: log(), getLogs(), createTable()
|   |   +-- logger.js               # File logging
+-- modules/                         # PowerShell scripts
|   +-- Users/Functions/ (29 real)
|   +-- Licensing/Functions/ (15 real)
|   +-- Exchange/Functions/ (7 real)
|   +-- Groups/Functions/ (11 real)
|   +-- Teams/Functions/ (4 real)
|   +-- SharePoint/Functions/ (4 real)
|   +-- Security/Functions/ (5 real)
|   +-- Recovery/Functions/ (15 real)
+-- public/index.html               # 36.7KB SPA with device-code login, all module panels
+-- database/schema.sql             # Minimal (2 tables — identified as weak point)
+-- deployment/
    +-- tenant-setup.ps1            # M365 tenant configuration script
    +-- nginx.conf, pm2.config.js   # Deployment config
```

### What's still missing in V10 (the gap to close)

Based on the Copilot assessment and code review:

1. **Database is still minimal** — 2-table schema (users + logs). The `auditLogger.js` has a `createTable()` method but it's not clear the schema is actually used. All session state is in-memory.
2. **213 stub/small PowerShell files** — Many modules have functions that are one-liner `.ps1` or `.txt` wrappers without real implementation. Teams and SharePoint are particularly thin.
3. **Copilot vs. AI Service duplication** — Two copilot systems exist: the legacy keyword-based `copilotRoutes.js` and the new LLM-based `aiService.js` + `aiRoutes.js`. The legacy one should be removed.
4. **No background scheduling** — Everything is on-demand API calls. No cron/scheduler for periodic syncs or reports.
5. **No alerting** — The toolkit can retrieve M365 data but doesn't alert on anomalies (license overuse, risky users, etc.).
6. **No monitoring** — No health checks, no performance metrics, no Grafana/Azure Monitor integration.
7. **PostgreSQL not MySQL** — SysWatch uses MySQL; the M365 Toolkit uses PostgreSQL. Must unify.
8. **Windows-only** — `securePowerShellRunner.js` spawns `powershell.exe`. Needs `pwsh` for cross-platform.
9. **Three service files are still 18-byte stubs** — `copilotService.js`, `loggingService.js`, `memoryService.js`.

---

## 4. Integration Analysis: SysWatch x M365 Toolkit (Revised)

### Revised assessment

The integration is even more attractive than previously assessed. The V10 codebase already implements several things that the previous roadmap assumed we'd need to build from scratch:

| What the previous roadmap assumed | What V10 actually has |
|---|---|
| Build M365 auth from scratch | Done — `azureAuth.js` with MSAL device-code flow |
| Build a Python PowerShell pool | Can port the concept from `securePowerShellRunner.js` |
| Build an AI copilot from scratch | Done — `aiService.js` with LLM integration, action mapping, confirmation flow |
| Build audit logging | Done — `auditLogger.js` with DB-backed logging |
| Build RBAC | Done — `rbac.js` with role definitions |
| Build M365 module wrappers | Done — all 8 modules with 5-7 operations each |

The integration now becomes less about building and more about **porting** — taking the V10 Node.js implementations and translating them to Python/Flask within the SysWatch framework, while keeping the PowerShell scripts as-is (they're language-agnostic).

### Integration verdict (revised)

**Feasibility: HIGH** — The V10 codebase proves the concept works. The architecture is sound. The PowerShell functions are production-grade. The AI service design (intent mapping to module actions with confirmation) aligns perfectly with SysWatch's human-in-the-loop approach.

The integration work is primarily:
1. Port the Node.js module wrappers to Python (straightforward — they're thin wrappers that build PowerShell commands and parse JSON responses)
2. Port the `securePowerShellRunner.js` concept to Python `subprocess.Popen` with persistent sessions
3. Port the `aiService.js` LLM integration to Python (SysWatch already has `ai/llm.py` with multi-provider support)
4. Port the `azureAuth.js` device-code flow to Python using `msal` Python SDK
5. Add M365 tables to SysWatch's `schema.sql`
6. Create M365 Jinja2 templates matching SysWatch's dark theme
7. Wire M365 alerts into SysWatch's alert engine and AI remediation pipeline

---

## 5. Recommended Integration Architecture (Revised)

```
SysWatch v3.0 (post-integration)
|
+-- backend/
|   +-- app.py                          # Flask entrypoint
|   +-- schema.sql                      # Extended with M365 tables
|   +-- modules/
|   |   +-- (existing SysWatch modules)  # config, database, security, etc.
|   |   +-- m365/                       # NEW — M365 integration (ported from V10)
|   |   |   +-- __init__.py
|   |   |   +-- auth.py                 # Port of azureAuth.js — MSAL device-code flow
|   |   |   +-- powershell_runner.py    # Port of securePowerShellRunner.js
|   |   |   +-- graph_client.py         # Direct Graph API calls (Python msal)
|   |   |   +-- ai_m365.py              # Port of aiService.js — M365-specific AI
|   |   |   +-- rbac.py                 # Port of rbac.js — M365 permission model
|   |   |   +-- modules/
|   |   |       +-- users.py            # Port of users.js (6 operations)
|   |   |       +-- licensing.py        # Port of licensing.js (6 operations)
|   |   |       +-- exchange.py         # Port of exchange.js (6 operations)
|   |   |       +-- groups.py           # Port of groups.js (6 operations)
|   |   |       +-- teams.py            # Port of teams.js (7 operations)
|   |   |       +-- sharepoint.py       # Port of sharepoint.js (6 operations)
|   |   |       +-- security.py         # Port of security.js (5 operations)
|   |   |       +-- recovery.py         # Port of Recovery PS functions (15 functions)
|   |   |       +-- reports.py          # Port of reports.js (6 report types)
|   |   +-- api_m365.py                 # Flask blueprint with 49+ M365 API endpoints
|   |   +-- web_ui/
|   |       +-- routes.py               # Extended with /m365 routes
|   |       +-- templates/
|   |           +-- m365_dashboard.html  # M365 overview
|   |           +-- m365_users.html     # User management
|   |           +-- m365_licenses.html  # License dashboard
|   |           +-- m365_exchange.html  # Mailbox overview
|   |           +-- m365_teams.html     # Teams management
|   |           +-- m365_security.html   # Security posture
|   |           +-- m365_recovery.html  # Recovery and undo operations
|   |           +-- m365_reports.html    # M365 usage reports
|   +-- powershell/                     # PowerShell scripts (from V10, as-is)
|       +-- Connect-M365.ps1
|       +-- Users/
|       +-- Licensing/
|       +-- Exchange/
|       +-- Groups/
|       +-- Teams/
|       +-- SharePoint/
|       +-- Security/
|       +-- Recovery/
|
+-- agents/
|   +-- syswatch_agent.py               # Existing (unchanged)
|
+-- docker-compose.yml                  # Extended if needed
```

### Key architecture decisions (from V10 evidence)

1. **Device-code flow, not client-secret** — V10 uses MSAL device-code flow (`azureAuth.js`), which means the user authenticates interactively via browser. This is more secure than storing a client secret but doesn't work for background jobs. SysWatch integration should support **both**: device-code for interactive sessions, client-secret for scheduled syncs.

2. **Per-session PowerShell, not per-command** — V10's `securePowerShellRunner.js` maintains a persistent PowerShell session per user, pre-authenticated to the M365 tenant. This avoids re-authenticating on every command. SysWatch should port this pattern.

3. **AI maps to module actions** — V10's `aiService.js` parses user input, maps it to a module action (e.g., "disable user" then `users.disable`), and executes through the module wrapper with confirmation. This is exactly the human-in-the-loop pattern SysWatch already uses.

4. **Structured PowerShell output** — All V10 PowerShell functions return `[PSCustomObject]@{ Success=$true; Message="..."; Data=$result }`. This is the standard output contract that the Copilot review identified as missing but was actually implemented in V10.

---

## 6. Roadmap Phase 1 — Stabilise and Harden (v2.2)

**Timeline:** 4-6 weeks  
**Goal:** Make SysWatch v2.1 production-grade before adding M365 capabilities.

### 6.1 Notification channels
- Email (SMTP), Slack, Teams, Discord, PagerDuty, generic webhook

### 6.2 Real-time UI updates
- WebSocket (Flask-SocketIO) for live metric streaming
- Auto-refresh alert/event feeds

### 6.3 Dashboard improvements
- Time-range selector, host grouping, customisable widgets, capacity planning charts

### 6.4 Agent enhancements
- Windows Event Log collection, Linux syslog, Docker container metrics, process monitoring

### 6.5 Security hardening
- SSO (OAuth2/SAML), TOTP 2FA, rate limiting, API key scoping, session management UI

### 6.6 Testing and CI/CD
- Unit tests, integration tests, GitHub Actions CI, vulnerability scanning

---

## 7. Roadmap Phase 2 — M365 Integration (v3.0)

**Timeline:** 8-12 weeks  
**Goal:** Port the M365 Toolkit V10 into SysWatch as a first-class module.

### 7.1 M365 connection management
- Port `azureAuth.js` to Python using `msal` SDK
- Support both device-code (interactive) and client-secret (background) flows
- Encrypted storage of tenant credentials using SysWatch's AES-256-GCM
- Multi-tenant support

### 7.2 PowerShell runner (Python port)
- Port `securePowerShellRunner.js` concept to Python
- `subprocess.Popen` with persistent stdin/stdout pipes
- Per-tenant PowerShell sessions with pre-loaded Microsoft.Graph module
- Support `pwsh` (Linux/macOS) and `powershell.exe` (Windows)
- Session recycling, timeout, queue management

### 7.3 M365 modules (port 90 real PowerShell functions + 8 JS module wrappers)

| Module | PS functions | JS operations | Priority | Notes |
|---|---|---|---|---|
| Users | 29 | 6 | P0 | Most complete module — port all 29 PS functions |
| Licensing | 15 | 6 | P0 | All via Graph API (subscribedSkus) |
| Recovery | 15 | 0 (new) | P1 | Port all 15 real functions; this is a NEW module for SysWatch |
| Groups | 11 | 6 | P1 | Graph API primary |
| Exchange | 7 | 6 | P1 | PowerShell (ExchangeOnlineManagement) |
| Security | 5 | 5 | P2 | Graph API (audit logs, risky users, sign-in logs, conditional access) |
| Teams | 4 | 7 | P2 | Graph API + PowerShell; many Teams PS functions need full implementation |
| SharePoint | 4 | 6 | P2 | PowerShell (PnP/SPO); many SP PS functions need full implementation |
| Reports | 0 (new) | 6 | P2 | Port JS report functions; they call other modules' data |

### 7.4 M365 database tables

```sql
CREATE TABLE IF NOT EXISTS m365_tenants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    tenant_id VARCHAR(100) NOT NULL UNIQUE,
    client_id VARCHAR(200) NOT NULL,
    client_secret_enc TEXT NOT NULL,
    client_secret_iv VARCHAR(64) NOT NULL,
    graph_endpoint VARCHAR(200) DEFAULT 'https://graph.microsoft.com',
    is_active BOOLEAN DEFAULT TRUE,
    last_synced TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS m365_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    upn VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    given_name VARCHAR(100),
    surname VARCHAR(100),
    job_title VARCHAR(200),
    department VARCHAR(200),
    office_location VARCHAR(200),
    usage_location VARCHAR(10),
    account_enabled BOOLEAN DEFAULT TRUE,
    created_date DATETIME,
    licenses JSON,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES m365_tenants(id) ON DELETE CASCADE,
    INDEX idx_m365user_upn (upn),
    INDEX idx_m365user_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS m365_licenses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    sku_id VARCHAR(100) NOT NULL,
    sku_part_number VARCHAR(200),
    display_name VARCHAR(300),
    consumed_units INT DEFAULT 0,
    prepaid_units INT DEFAULT 0,
    warning_ratio DECIMAL(5,2) DEFAULT 0.90,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES m365_tenants(id) ON DELETE CASCADE,
    UNIQUE KEY uk_tenant_sku (tenant_id, sku_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS m365_audit_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    record_type VARCHAR(100),
    operation VARCHAR(200),
    workload VARCHAR(50),
    user_upn VARCHAR(255),
    object_id VARCHAR(255),
    result_status VARCHAR(20),
    details JSON,
    event_time TIMESTAMP NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES m365_tenants(id) ON DELETE CASCADE,
    INDEX idx_m365audit_time (event_time DESC),
    INDEX idx_m365audit_user (user_upn),
    INDEX idx_m365audit_op (operation)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS m365_executions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    module VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    params JSON,
    result_status ENUM('success','failed','partial') NOT NULL,
    output TEXT,
    error TEXT,
    execution_ms INT,
    executed_by VARCHAR(255) NOT NULL,
    approved_by VARCHAR(255),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES m365_tenants(id) ON DELETE CASCADE,
    INDEX idx_m365exec_module (module),
    INDEX idx_m365exec_time (executed_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 7.5 M365 web UI templates

| Template | Purpose |
|---|---|
| `m365_dashboard.html` | Tenant health, license consumption, user count, recent audit events |
| `m365_users.html` | User table with search, filter, bulk actions |
| `m365_licenses.html` | License consumption bars, >90% alerts, cleanup recommendations |
| `m365_exchange.html` | Mailbox overview, large mailboxes, forwarding rules, audit |
| `m365_teams.html` | Team inventory, empty teams, guest users, activity |
| `m365_security.html` | Secure Score, conditional access, sign-in risk, audit log |
| `m365_recovery.html` | Deleted items recovery, undo operations, action history |
| `m365_reports.html` | User activity, license usage, group activity, Teams/SharePoint usage |

### 7.6 AI-powered M365 insights

Port V10's `aiService.js` concept into SysWatch's existing AI engine:
- License optimisation AI ("15 unlicensed users, 3 disabled users with active licenses — reclaim to save Rs X/month")
- Impossible-travel detection (sign-in anomalies)
- Mailbox growth anomaly AI
- Teams sprawl AI (inactive teams)
- All suggestions flow through SysWatch's existing human-in-the-loop approval

### 7.7 Cross-domain alerting

Correlate infrastructure alerts with M365 events:
- Exchange VM down then check M365 mail flow
- Disk 95% on AD Connect server then alert that M365 sync may fail
- Domain controller unreachable then alert that M365 password resets will fail

---

## 8. Roadmap Phase 3 — Advanced AI and Automation (v3.5)

**Timeline:** 6-8 weeks  
**Goal:** Move from reactive to proactive AI.

- Predictive alerting (CPU/disk/license exhaustion forecasting)
- Natural language operations ("Show me all users who haven't logged in for 90 days")
- Automated runbook generation from recurring alert patterns
- Log intelligence (Windows Event Log + Linux syslog + M365 audit log analysis)
- Self-healing with guardrails (auto-approve LOW-risk actions, all logged and reversible)

---

## 9. Roadmap Phase 4 — Ecosystem and Scale (v4.0)

**Timeline:** 10-14 weeks  
**Goal:** Central nervous system for the entire IT estate.

- Docker and Kubernetes monitoring
- Network topology mapping (SNMP auto-discovery)
- Asset inventory / CMDB
- Configuration drift detection
- Patch management
- Multi-tenancy
- Mobile PWA
- Plugin marketplace

---

## 10. Feature Backlog

### High impact, low effort (quick wins)

| # | Feature | Effort | Impact |
|---|---|---|---|
| 1 | Email alert notifications (SMTP) | 2 days | High |
| 2 | Slack/Teams webhook alerts | 1 day | High |
| 3 | Dashboard time-range selector | 1 day | Medium |
| 4 | Host group filtering on dashboard | 0.5 day | Medium |
| 5 | Export host/alert lists as CSV | 0.5 day | Medium |
| 6 | Password change on first login | 0.5 day | High |
| 7 | API rate limiting | 1 day | High |
| 8 | Health check endpoint for load balancer | 0.5 day | High |

### High impact, medium effort

| # | Feature | Effort | Impact |
|---|---|---|---|
| 9 | WebSocket live updates (Flask-SocketIO) | 3 days | High |
| 10 | Docker container monitoring | 4 days | High |
| 11 | Windows Event Log collection | 3 days | High |
| 12 | SSO (Google / Microsoft OAuth2) | 3 days | High |
| 13 | TOTP 2FA | 2 days | High |
| 14 | [M365] Port azureAuth.js to Python | 3 days | High |
| 15 | [M365] Port securePowerShellRunner.js to Python | 4 days | High |
| 16 | [M365] Port aiService.js M365 AI to Python | 3 days | High |
| 17 | [M365] Port 8 module wrappers (users, licensing, exchange, groups, teams, sharepoint, security, reports) | 1 week | High |

### High impact, high effort (major features)

| # | Feature | Effort | Impact |
|---|---|---|---|
| 18 | [M365] Full Users module (29 PS functions) | 2 weeks | High |
| 19 | [M365] Full Licensing module (15 functions) | 1 week | High |
| 20 | [M365] Recovery module (15 functions — NEW for SysWatch) | 1.5 weeks | High |
| 21 | [M365] Exchange module (7 functions + missing implementations) | 1.5 weeks | High |
| 22 | [M365] Groups module (11 functions) | 1 week | Medium |
| 23 | [M365] Security module (5 functions) | 0.5 week | Medium |
| 24 | [M365] Teams module (4 real + 27 to implement) | 2 weeks | Medium |
| 25 | [M365] SharePoint module (4 real + 25 to implement) | 2 weeks | Medium |
| 26 | [M365] 8 web UI templates | 1.5 weeks | High |
| 27 | [M365] Cross-domain alerting | 1 week | High |
| 28 | [M365] AI-powered M365 insights | 2 weeks | High |
| 29 | Kubernetes monitoring | 3 weeks | High |
| 30 | Asset inventory / CMDB | 4 weeks | High |
| 31 | Patch management | 4 weeks | High |
| 32 | Multi-tenancy | 4 weeks | Medium |
| 33 | Mobile PWA | 3 weeks | Medium |
| 34 | Predictive alerting | 2 weeks | High |
| 35 | Natural language AI copilot | 3 weeks | High |
| 36 | Self-healing automation | 2 weeks | High |

---

## 11. Summary Opinion

### What changed from the first roadmap

The first roadmap was written based on the GitHub repository, which is an early skeleton. The uploaded codebase reveals a project that is far more advanced than the GitHub repo suggested:

- **90 real PowerShell functions** (not 181 as previously stated, but far better quality than assumed — proper CmdletBinding, validation, structured output)
- **Security and Recovery modules are real** (not stubs as previously stated) — 5 security functions and 15 recovery functions with genuine implementations
- **Full AI service** (not keyword matching as on GitHub) — LLM-powered intent mapping with confirmation flow
- **Azure AD device-code authentication** — real MSAL integration, not plaintext JWT
- **49 API routes** (not 4) with audit logging via `logAndRespond` wrapper
- **RBAC, rate limiting, helmet, CORS** — security middleware that GitHub doesn't have

### Revised integration recommendation

**Integrate it. The V10 codebase proves the concept works.**

The integration is now primarily a **port** (Node.js to Python) rather than a **build** (from scratch). The V10 architecture — device-code auth, secure PowerShell runner, AI service with action mapping, audit logging, module-based structure — maps cleanly to SysWatch's existing patterns (JWT auth, subprocess execution, AI/LLM engine, audit log, blueprint-based API).

The key insight from the Copilot chat review is that the user demands discipline: validate before building, anchor on existing code, no parallel architecture. This aligns perfectly with a port approach — take what works in V10, translate it to Python/Flask, and integrate it into SysWatch's existing framework.

### On what makes this integration uniquely valuable

No single open-source tool today combines:
- On-premises infrastructure monitoring (CPU, disk, network, SNMP)
- Microsoft 365 cloud management (users, licenses, Exchange, Teams, SharePoint)
- AI-powered diagnosis connecting both domains
- Human-in-the-loop remediation with audit trail
- Self-hosted (no SaaS dependency)

SysWatch v3.0 would be that tool.

---

*This roadmap is a living document. Revisit at the end of each phase.*
