# M365 x SysWatch Integration — Project Tracker

> **Project:** Integrate the M365-AI-SaaS-Toolkit into SysWatch as a first-class module (Roadmap Phase 2 → v3.0)  
> **Started:** 25 August 2026  
> **Target completion:** ~8-12 weeks (targeting end of October 2026)  
> **Repositories:**  
> - SysWatch: https://github.com/tws-manumaha/SysWatch_v2.1  
> - M365 Toolkit: https://github.com/tws-manumaha/M365-AI-SaaS-Toolkit  
> **Roadmap reference:** `roadmap.md` (Section 6, Phase 2)

---

## How to use this tracker

Each task below has a status emoji, an owner, a priority, and a dependency column. Update the status as you go:

| Status | Meaning |
|---|---|
| ⬜ | Not started |
| 🔄 | In progress |
| ✅ | Complete |
| ⚠️ | Blocked / needs attention |
| ❌ | Cancelled / descoped |

**Priorities:** P0 = blocker, P1 = must-have for v3.0, P2 = nice-to-have for v3.0, P3 = post-v3.0

---

## Phase 0 — Pre-Integration Preparation

Before writing any integration code, get the M365 Toolkit's PowerShell functions into a clean, portable state and set up the SysWatch side to receive them.

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 0.1 | Audit all 181 real PowerShell functions across 6 modules — verify each one works, document inputs/outputs | ⬜ | P0 | — | 60 stub functions in Security/Recovery — drop or implement separately |
| 0.2 | Consolidate PowerShell functions into a single `powershell/` directory tree with consistent naming | ⬜ | P0 | 0.1 | `powershell/Users/`, `powershell/Licensing/`, etc. |
| 0.3 | Write a `Connect-M365.ps1` that supports both interactive (MFA) and app-only (client secret) auth | ⬜ | P0 | — | Current version only does interactive; app-only is needed for background jobs |
| 0.4 | Document required Azure AD app permissions (Graph scopes, Exchange RBAC, SharePoint admin) | ⬜ | P0 | — | Needed for the settings UI guide |
| 0.5 | Create a test M365 tenant (Microsoft 365 Developer Program) for integration testing | ⬜ | P1 | — | Free E5 dev tenant for testing without prod risk |
| 0.6 | Verify `pwsh` (PowerShell Core 7) works on the SysWatch Linux deployment target | ⬜ | P1 | — | `Install-Module Microsoft.Graph` on Linux |
| 0.7 | Inventory SysWatch's existing `subprocess` usage and remote-exec patterns to align with the new PS pool | ⬜ | P1 | — | Ensure consistent error handling / timeout patterns |

---

## Phase 1 — Foundation (Database + Connection + Pool)

Build the data layer and the M365 connection infrastructure inside SysWatch.

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 1.1 | Add M365 tables to `schema.sql`: `m365_tenants`, `m365_users`, `m365_licenses`, `m365_audit_events`, `m365_executions` | ⬜ | P0 | — | SQL is already written in roadmap.md Section 6.4 |
| 1.2 | Extend `database.py` with M365-specific query helpers (get_tenant, upsert_m365_user, etc.) | ⬜ | P0 | 1.1 | |
| 1.3 | Build `backend/modules/m365/__init__.py` — module package | ⬜ | P0 | — | |
| 1.4 | Build `backend/modules/m365/connection.py` — Microsoft Graph auth via `msal` library (app-only token, auto-refresh) | ⬜ | P0 | 1.1 | Store client_secret encrypted using SysWatch's AES-256-GCM |
| 1.5 | Build `backend/modules/m365/powershell_pool.py` — Python port of `powershellPool.js` | ⬜ | P0 | 0.2, 0.3 | `subprocess.Popen` with stdin/stdout pipes; per-tenant sessions; `pwsh` on Linux, `powershell.exe` on Windows |
| 1.6 | Add M365 settings UI to `settings.html` — tenant config form (tenant ID, client ID, client secret, test connection) | ⬜ | P0 | 1.4 | Encrypted secret storage; connection health check button |
| 1.7 | Add M365 routes to `web_ui/routes.py` — `/m365` namespace | ⬜ | P0 | 1.3 | |
| 1.8 | Add `msal` to `requirements.txt` | ⬜ | P0 | — | `msal>=1.28.0` |
| 1.9 | Add M365 nav item to sidebar in `base.html` | ⬜ | P1 | 1.7 | Emerald icon, "M365" label |
| 1.10 | End-to-end test: configure a tenant, get a Graph token, verify `/organization` returns data | ⬜ | P0 | 1.4, 0.5 | |

---

## Phase 2 — M365 Dashboard + User Sync

Get the first visible M365 data into the SysWatch UI.

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 2.1 | Build `backend/modules/m365/graph_client.py` — thin Python wrapper for Graph API calls | ⬜ | P0 | 1.4 | Users, licenses, organization endpoints |
| 2.2 | Implement M365 user sync — pull all users from Graph, upsert into `m365_users` table | ⬜ | P0 | 2.1, 1.2 | Scheduled job via SysWatch's APScheduler; store licenses as JSON |
| 2.3 | Implement license sync — pull `subscribedSkus`, upsert into `m365_licenses` | ⬜ | P0 | 2.1, 1.2 | |
| 2.4 | Build `m365_dashboard.html` template — tenant health, license consumption bars, user count, recent audit events | ⬜ | P0 | 2.2, 2.3 | Dark slate / emerald theme; Chart.js for license consumption |
| 2.5 | Build `m365_users.html` template — searchable/sortable user table, filter by license/status, click for detail | ⬜ | P0 | 2.2 | |
| 2.6 | Build `m365_licenses.html` template — license cards with consumption %, warning at >90%, cleanup recommendations | ⬜ | P0 | 2.3 | |
| 2.7 | Add scheduled sync jobs to `scheduler.py` — users every 1h, licenses every 4h | ⬜ | P1 | 2.2, 2.3 | Configurable interval in settings |
| 2.8 | End-to-end test: dashboard shows live M365 tenant data | ⬜ | P0 | 2.4, 2.5, 2.6 | |

---

## Phase 3 — Users Module (24 functions)

Port the M365 Users PowerShell functions into SysWatch's Python + PowerShell hybrid model.

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 3.1 | Build `backend/modules/m365/modules/users.py` — Python wrapper for user operations | ⬜ | P0 | 1.4, 1.5 | Each function: try Graph API first, fall back to PowerShell |
| 3.2 | Port PowerShell user functions to `powershell/Users/` directory | ⬜ | P0 | 0.2 | 24 real functions (skip 6 empty stubs) |
| 3.3 | Wire user operations through human-in-the-loop approval for destructive actions | ⬜ | P0 | 3.1 | Disable, delete, password reset require approval; read ops don't |
| 3.4 | Add user CRUD API endpoints to `api_m365.py` blueprint | ⬜ | P0 | 3.1 | `GET/POST/PUT/DELETE /api/m365/users` |
| 3.5 | Add user action buttons to `m365_users.html` — create, disable, enable, reset password, revoke sessions | ⬜ | P0 | 3.4 | Modal dialogs with confirmation |
| 3.6 | Log all M365 user operations to `m365_executions` table | ⬜ | P0 | 3.1 | Module, action, params, result, executed_by, approved_by |
| 3.7 | End-to-end test: create user in SysWatch UI → verify in M365 → disable → verify | ⬜ | P0 | 3.5, 0.5 | |

### User functions to port (checklist)

- [ ] `Get-M365Users` (list all)
- [ ] `Get-UserDetails` (single user)
- [ ] `Get-ActiveUsers`
- [ ] `Get-DisabledUsers`
- [ ] `Get-UnlicensedUsers`
- [ ] `Get-NewUsers`
- [ ] `Get-UserGroups`
- [ ] `Get-UserManager`
- [ ] `Get-UserSignin`
- [ ] `Create-NewM365User`
- [ ] `Bulk-CreateM365Users`
- [ ] `Update-M365UserProfile`
- [ ] `Disable-M365User`
- [ ] `Enable-M365User`
- [ ] `Bulk-DisableM365Users`
- [ ] `Bulk-EnableM365Users`
- [ ] `Remove-M365User`
- [ ] `Bulk-DeleteM365Users`
- [ ] `Reset-PasswordM365User`
- [ ] `Force-PasswordResetM365User`
- [ ] `Bulk-ResetPasswordsM365Users`
- [ ] `Revoke-SessionsM365`
- [ ] `Lock-M365UserAccount`
- [ ] `Unlock-M365UserAccount`
- [ ] `Add-AliasM365Users`
- [ ] `Remove-AliasM365Users`
- [ ] `Check-M365UserAccountStatus`
- [ ] `Export-M365Users`

---

## Phase 4 — Licensing Module (31 functions)

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 4.1 | Build `backend/modules/m365/modules/licensing.py` — Python wrapper for license operations | ⬜ | P0 | 1.4 | Most via Graph API (subscribedSkus) |
| 4.2 | Port PowerShell licensing functions to `powershell/Licensing/` | ⬜ | P0 | 0.2 | 31 functions |
| 4.3 | Add license API endpoints to `api_m365.py` | ⬜ | P0 | 4.1 | `GET/POST /api/m365/licenses` |
| 4.4 | Add license action buttons to `m365_licenses.html` — assign, remove, bulk assign, bulk remove | ⬜ | P1 | 4.3, 2.6 | |
| 4.5 | Implement license alert rules — alert when consumption > 90% of prepaid | ⬜ | P1 | 2.3 | Wire into SysWatch's existing alert_engine |
| 4.6 | Implement license cleanup recommendations — disabled users with active licenses | ⬜ | P1 | 2.2, 2.3 | AI-powered suggestion in dashboard |
| 4.7 | End-to-end test: assign license → verify in M365 → remove → verify | ⬜ | P0 | 4.4, 0.5 | |

### Licensing functions to port (checklist)

- [ ] `Get-LicenseSummary`
- [ ] `Get-LicenseDetails`
- [ ] `Get-LicenseSkus`
- [ ] `Get-LicensePlans`
- [ ] `Get-LicenseUsage`
- [ ] `Get-LicenseConsumption`
- [ ] `Get-LicenseHealth`
- [ ] `Get-LicenseAlerts`
- [ ] `Get-LicenseTrend`
- [ ] `Get-AvailableLicenses`
- [ ] `Get-LicensedUsers`
- [ ] `Get-UnlicensedUsers`
- [ ] `Get-UsersByLicense`
- [ ] `Get-UserLicenses`
- [ ] `Get-UserLicenseCount`
- [ ] `Get-DisabledUsersWithLicense`
- [ ] `Check-LicenseAvailability`
- [ ] `Detect-LicenseOveruse`
- [ ] `Recommend-LicenseCleanup`
- [ ] `Cleanup-UnusedLicenses`
- [ ] `Assign-License`
- [ ] `Assign-LicenseToGroup`
- [ ] `Bulk-AssignLicense`
- [ ] `Remove-License`
- [ ] `Remove-LicenseFromGroup`
- [ ] `Bulk-RemoveLicense`
- [ ] `Bulk-LicenseCheck`
- [ ] `Reassign-License`
- [ ] `Export-LicenseReport`
- [ ] `Bulk-UnlicensedUsers`
- [ ] `Get-LicenseSummary` (duplicate check)

---

## Phase 5 — Exchange Module (30 functions)

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 5.1 | Build `backend/modules/m365/modules/exchange.py` — Python wrapper for mailbox operations | ⬜ | P1 | 1.4, 1.5 | Requires PowerShell (ExchangeOnlineManagement) |
| 5.2 | Port PowerShell Exchange functions to `powershell/Exchange/` | ⬜ | P1 | 0.2 | 30 functions |
| 5.3 | Build `m365_exchange.html` template — mailbox overview, large mailboxes, forwarding rules, audit | ⬜ | P1 | 5.1 | |
| 5.4 | Add Exchange API endpoints to `api_m365.py` | ⬜ | P1 | 5.1 | |
| 5.5 | Implement mailbox growth alerting — alert when mailbox grows > 2x normal rate | ⬜ | P2 | 5.1 | AI-powered; uses historical data |
| 5.6 | End-to-end test: get mailboxes → check forwarding rules → enable audit | ⬜ | P1 | 5.4, 0.5 | |

### Exchange functions to port (checklist)

- [ ] `Get-Mailboxes`
- [ ] `Get-UserMailbox`
- [ ] `Get-SharedMailboxes`
- [ ] `Get-MailboxSize`
- [ ] `Get-LargeMailboxes`
- [ ] `Get-MailboxPermissions`
- [ ] `Get-MailboxRules`
- [ ] `Get-MailboxAudit`
- [ ] `Get-TransportRules`
- [ ] `Get-AutoReply`
- [ ] `Get-MailForwarding`
- [ ] `New-Mailbox`
- [ ] `New-SharedMailbox`
- [ ] `Enable-Mailbox`
- [ ] `Disable-Mailbox`
- [ ] `Remove-Mailbox`
- [ ] `Bulk-EnableMailbox`
- [ ] `Bulk-DisableMailbox`
- [ ] `Bulk-RemoveMailbox`
- [ ] `Add-MailboxPermission`
- [ ] `Remove-MailboxPermission`
- [ ] `Set-AutoReply`
- [ ] `Remove-AutoReply`
- [ ] `Set-MailForwarding`
- [ ] `Remove-MailForwarding`
- [ ] `Remove-MailboxRules`
- [ ] `Enable-MailboxAudit`
- [ ] `Export-MailboxReport`
- [ ] `Remove-SharedMailbox`

---

## Phase 6 — Groups Module (30 functions)

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 6.1 | Build `backend/modules/m365/modules/groups.py` | ⬜ | P1 | 1.4 | Graph API primary |
| 6.2 | Port PowerShell Groups functions to `powershell/Groups/` | ⬜ | P1 | 0.2 | 30 functions |
| 6.3 | Add Groups section to M365 dashboard (or separate `m365_groups.html`) | ⬜ | P2 | 6.1 | |
| 6.4 | Add Groups API endpoints to `api_m365.py` | ⬜ | P1 | 6.1 | |
| 6.5 | Implement orphan group detection + cleanup recommendation | ⬜ | P2 | 6.1 | AI-powered |
| 6.6 | End-to-end test: create group → add members → remove group | ⬜ | P1 | 6.4, 0.5 | |

### Groups functions to port (checklist)

- [ ] `Get-Groups`
- [ ] `Get-GroupTypes`
- [ ] `Get-SecurityGroups`
- [ ] `Get-O365Groups`
- [ ] `Get-DynamicGroups`
- [ ] `Get-GroupsByName`
- [ ] `Get-GroupSettings`
- [ ] `Get-GroupMembers`
- [ ] `Get-GroupOwners`
- [ ] `Get-LargeGroups`
- [ ] `Get-EmptyGroups`
- [ ] `Get-OrphanGroups`
- [ ] `Get-GuestsInGroups`
- [ ] `New-Group`
- [ ] `Update-Group`
- [ ] `Remove-Group`
- [ ] `Clone-Group`
- [ ] `Add-GroupMember`
- [ ] `Remove-GroupMember`
- [ ] `Add-GroupOwner`
- [ ] `Remove-GroupOwner`
- [ ] `Bulk-AddMembers`
- [ ] `Bulk-RemoveMembers`
- [ ] `Bulk-CreateGroups`
- [ ] `Clean-EmptyGroups`
- [ ] `Transfer-Ownership`
- [ ] `Remove-GuestUsers`
- [ ] `Group-ActivityReport`
- [ ] `Export-GroupReport`

---

## Phase 7 — Teams Module (31 functions)

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 7.1 | Build `backend/modules/m365/modules/teams.py` | ⬜ | P2 | 1.4, 1.5 | Graph API + PowerShell |
| 7.2 | Port PowerShell Teams functions to `powershell/Teams/` | ⬜ | P2 | 0.2 | 31 functions |
| 7.3 | Build `m365_teams.html` template — team inventory, empty teams, guest users, activity | ⬜ | P2 | 7.1 | |
| 7.4 | Add Teams API endpoints to `api_m365.py` | ⬜ | P2 | 7.1 | |
| 7.5 | Implement Teams sprawl detection — inactive teams recommendation | ⬜ | P2 | 7.1 | AI-powered |
| 7.6 | End-to-end test: create team → add channel → add user → archive | ⬜ | P2 | 7.4, 0.5 | |

### Teams functions to port (checklist)

- [ ] `Get-Teams`
- [ ] `Get-TeamSettings`
- [ ] `Get-TeamChannels`
- [ ] `Get-StandardChannels`
- [ ] `Get-PrivateChannels`
- [ ] `Get-TeamUsers`
- [ ] `Get-TeamOwners`
- [ ] `Get-TeamGuestUsers`
- [ ] `Get-TeamApps`
- [ ] `Get-EmptyTeams`
- [ ] `Get-LargeTeams`
- [ ] `New-Team`
- [ ] `New-TeamChannel`
- [ ] `Set-TeamSettings`
- [ ] `Archive-Team`
- [ ] `Restore-Team`
- [ ] `Remove-Team`
- [ ] `Remove-TeamChannel`
- [ ] `Add-TeamUser`
- [ ] `Add-TeamOwner`
- [ ] `Remove-TeamUser`
- [ ] `Remove-TeamOwner`
- [ ] `Remove-TeamGuestUsers`
- [ ] `Add-TeamApp`
- [ ] `Remove-TeamApp`
- [ ] `Bulk-CreateTeams`
- [ ] `Bulk-AddTeamUsers`
- [ ] `Bulk-RemoveTeamUsers`
- [ ] `Clone-Team`
- [ ] `Export-TeamReport`

---

## Phase 8 — SharePoint Module (29 functions)

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 8.1 | Build `backend/modules/m365/modules/sharepoint.py` | ⬜ | P2 | 1.4, 1.5 | PowerShell (PnP or SPO) |
| 8.2 | Port PowerShell SharePoint functions to `powershell/SharePoint/` | ⬜ | P2 | 0.2 | 29 functions |
| 8.3 | Add SharePoint API endpoints to `api_m365.py` | ⬜ | P2 | 8.1 | |
| 8.4 | Add SharePoint overview to M365 dashboard | ⬜ | P2 | 8.1 | Site count, storage usage, empty sites |
| 8.5 | End-to-end test: create site → upload file → check storage → remove site | ⬜ | P2 | 8.3, 0.5 | |

### SharePoint functions to port (checklist)

- [ ] `Get-Sites`
- [ ] `Get-DeletedSites`
- [ ] `Get-EmptySites`
- [ ] `Get-LargeSites`
- [ ] `Get-SiteStorage`
- [ ] `Get-SiteUsers`
- [ ] `Get-SitePermissions`
- [ ] `Get-SharingSettings`
- [ ] `Get-Lists`
- [ ] `Get-Documents`
- [ ] `New-Site`
- [ ] `New-List`
- [ ] `Restore-Site`
- [ ] `Remove-Site`
- [ ] `Remove-DeletedSite`
- [ ] `Remove-List`
- [ ] `Add-SiteUser`
- [ ] `Remove-SiteUser`
- [ ] `Grant-SitePermission`
- [ ] `Revoke-SitePermission`
- [ ] `Set-SharingSettings`
- [ ] `Set-SiteStorage`
- [ ] `Upload-File`
- [ ] `Download-File`
- [ ] `Bulk-CreateSites`
- [ ] `Bulk-AddSiteUsers`
- [ ] `Bulk-RemoveSiteUsers`
- [ ] `Export-SitesReport`

---

## Phase 9 — AI-Powered M365 Insights

Extend SysWatch's existing AI engine to M365 data.

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 9.1 | Add M365 context to `ai/log_intelligence.py` — feed M365 audit events + license data + user activity to the LLM | ⬜ | P1 | 2.2, 2.3, 3.1 | |
| 9.2 | Implement license optimisation AI — "You have N unlicensed users and M disabled users with licenses. Reclaiming saves Rs X/month." | ⬜ | P1 | 2.2, 2.3 | |
| 9.3 | Implement impossible-travel detection — flag sign-ins from impossible locations | ⬜ | P1 | 2.2 | Uses M365 sign-in logs |
| 9.4 | Implement mailbox growth anomaly AI — flag mailboxes growing > 2x normal rate | ⬜ | P2 | 5.1 | |
| 9.5 | Implement Teams sprawl AI — inactive teams, empty teams, guest user audit | ⬜ | P2 | 7.1 | |
| 9.6 | Implement SharePoint sprawl AI — empty sites, oversized sites, external sharing audit | ⬜ | P2 | 8.1 | |
| 9.7 | Add M365 insights to `ai_insights.html` — dedicated M365 section in the AI insights page | ⬜ | P1 | 9.2 | |
| 9.8 | All M365 AI suggestions flow through human-in-the-loop approval | ⬜ | P0 | 9.2 | Reuse existing approval workflow |

---

## Phase 10 — Cross-Domain Alerting (Infrastructure × M365)

Correlate SysWatch infrastructure alerts with M365 events.

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 10.1 | Define cross-domain alert rules in `alert_engine.py` | ⬜ | P1 | 2.2 | e.g., "Exchange VM down → check M365 mail flow" |
| 10.2 | Implement host-to-M365-service mapping (tag hosts with their M365 role: AD Connect, Exchange Hybrid, ADFS, etc.) | ⬜ | P1 | — | New host metadata field |
| 10.3 | Implement alert correlation logic — when infra alert fires, check related M365 services | ⬜ | P1 | 10.1, 10.2 | |
| 10.4 | Add cross-domain alerts to the alerts dashboard with a special "correlated" badge | ⬜ | P2 | 10.3 | |
| 10.5 | Implement AI-powered cross-domain diagnosis — "Exchange VM CPU 95% → likely causing M365 mail delivery delays" | ⬜ | P2 | 10.3, 9.1 | |

---

## Phase 11 — Audit, Logging & Execution History

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 11.1 | Log every M365 operation to `m365_executions` table (module, action, params, result, user, approval) | ⬜ | P0 | 1.1 | |
| 11.2 | Build M365 audit log view in UI — filterable by module, action, user, date, status | ⬜ | P1 | 11.1 | |
| 11.3 | Implement M365 Unified Audit Log pull (Graph API) → store in `m365_audit_events` | ⬜ | P1 | 2.1 | Scheduled job |
| 11.4 | Add M365 audit events to SysWatch's event stream | ⬜ | P2 | 11.3 | |
| 11.5 | Implement execution replay — view past M365 operation inputs/outputs | ⬜ | P2 | 11.1 | |

---

## Phase 12 — Multi-Tenant Support

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 12.1 | Support multiple M365 tenants in `m365_tenants` table | ⬜ | P2 | 1.1 | Already designed for multi-tenant |
| 12.2 | Add tenant selector dropdown in M365 UI (sidebar or dashboard header) | ⬜ | P2 | 12.1 | |
| 12.3 | Per-tenant PowerShell pool sessions | ⬜ | P2 | 1.5, 12.1 | |
| 12.4 | Per-tenant scheduled sync jobs | ⬜ | P2 | 2.7, 12.1 | |
| 12.5 | End-to-end test: manage 2 tenants, switch between them, verify data isolation | ⬜ | P2 | 12.4, 0.5 | |

---

## Phase 13 — Testing & Documentation

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 13.1 | Unit tests for `m365/connection.py` (token acquisition, refresh, error handling) | ⬜ | P1 | 1.4 | |
| 13.2 | Unit tests for `m365/powershell_pool.py` (session lifecycle, command queue, timeout) | ⬜ | P1 | 1.5 | |
| 13.3 | Integration tests for each module (Users, Licensing, Exchange, Groups, Teams, SharePoint) | ⬜ | P1 | 3-8 | Mock Graph API + real PS on test tenant |
| 13.4 | End-to-end test suite: full workflow from dashboard → action → M365 → verify | ⬜ | P1 | 13.3 | |
| 13.5 | Update `README.md` with M365 setup instructions | ⬜ | P1 | — | Azure AD app registration, permissions, config |
| 13.6 | Write M365 integration docs — `docs/m365-setup.md` | ⬜ | P1 | — | Step-by-step with screenshots |
| 13.7 | Update `docker-compose.yml` if PowerShell Core needs to be in the Flask container | ⬜ | P1 | 0.6 | Add `pwsh` install to Dockerfile |
| 13.8 | Update `install.sh` / `install.ps1` with M365 dependency checks | ⬜ | P2 | — | Check for `pwsh`, `Microsoft.Graph` module |
| 13.9 | Performance test — PowerShell pool under concurrent load (10+ simultaneous M365 operations) | ⬜ | P2 | 1.5 | |
| 13.10 | Security review — verify no M365 credentials logged, all secrets encrypted at rest | ⬜ | P0 | — | |

---

## Phase 14 — Deployment & Release

| # | Task | Status | Priority | Depends on | Notes |
|---|---|---|---|---|---|
| 14.1 | Merge M365 integration branch to `main` | ⬜ | P0 | All above | |
| 14.2 | Tag release `v3.0.0` | ⬜ | P0 | 14.1 | |
| 14.3 | Update `roadmap.md` — mark Phase 2 complete | ⬜ | P1 | 14.2 | |
| 14.4 | Write v3.0 release notes | ⬜ | P1 | 14.2 | |
| 14.5 | Deploy to production SysWatch instance | ⬜ | P0 | 14.2 | |

---

## Dependency Graph (simplified)

```
Phase 0 (Prep)
    │
    ▼
Phase 1 (Foundation: DB + Connection + PS Pool)
    │
    ├──► Phase 2 (Dashboard + User Sync)
    │        │
    │        ├──► Phase 3 (Users Module)
    │        ├──► Phase 4 (Licensing Module)
    │        ├──► Phase 5 (Exchange Module)
    │        ├──► Phase 6 (Groups Module)
    │        ├──► Phase 7 (Teams Module)
    │        └──► Phase 8 (SharePoint Module)
    │                  │
    │                  ▼
    │            Phase 9 (AI Insights) ──► Phase 10 (Cross-Domain Alerting)
    │                  │
    │                  ▼
    │            Phase 11 (Audit & Logging)
    │                  │
    │                  ▼
    │            Phase 12 (Multi-Tenant)
    │
    ▼
Phase 13 (Testing & Docs) ──► Phase 14 (Deploy & Release)
```

---

## Progress Summary

| Phase | Tasks | Done | In Progress | Blocked | Not Started |
|---|---|---|---|---|---|
| 0 — Pre-Integration | 7 | 0 | 0 | 0 | 7 |
| 1 — Foundation | 10 | 0 | 0 | 0 | 10 |
| 2 — Dashboard + Sync | 8 | 0 | 0 | 0 | 8 |
| 3 — Users Module | 7 + 28 functions | 0 | 0 | 0 | 35 |
| 4 — Licensing Module | 7 + 31 functions | 0 | 0 | 0 | 38 |
| 5 — Exchange Module | 6 + 29 functions | 0 | 0 | 0 | 35 |
| 6 — Groups Module | 6 + 29 functions | 0 | 0 | 0 | 35 |
| 7 — Teams Module | 6 + 30 functions | 0 | 0 | 0 | 36 |
| 8 — SharePoint Module | 5 + 28 functions | 0 | 0 | 0 | 33 |
| 9 — AI Insights | 8 | 0 | 0 | 0 | 8 |
| 10 — Cross-Domain Alerting | 5 | 0 | 0 | 0 | 5 |
| 11 — Audit & Logging | 5 | 0 | 0 | 0 | 5 |
| 12 — Multi-Tenant | 5 | 0 | 0 | 0 | 5 |
| 13 — Testing & Docs | 10 | 0 | 0 | 0 | 10 |
| 14 — Deploy & Release | 5 | 0 | 0 | 0 | 5 |
| **TOTAL** | **100 tasks + 175 function checklists** | **0** | **0** | **0** | **275** |

---

## Decision Log

Record key decisions made during the project. Add new rows as decisions are made.

| Date | Decision | Rationale | Decided by |
|---|---|---|---|
| 2026-08-25 | Integrate M365 Toolkit into SysWatch (not keep separate) | Complementary tools; PowerShell functions are language-agnostic; SysWatch has superior infra (auth, AI, UI, scheduling) | Makarand |
| 2026-08-25 | Use dual-path access (Graph API + PowerShell) | Graph API for read-heavy ops (fast, cross-platform); PowerShell for Exchange/SharePoint ops not in Graph | Roadmap Section 4 |
| 2026-08-25 | Port PowerShellPool.js to Python (subprocess.Popen) | Eliminates Node.js dependency; consistent with SysWatch's Python stack | Roadmap Section 4 |
| 2026-08-25 | Drop PostgreSQL (M365 Toolkit's DB); unify on MySQL | SysWatch already has MySQL with 31 tables; avoids dual-database complexity | Roadmap Section 3 |
| 2026-08-25 | Drop Security and Recovery stub modules (60 functions) | They are empty placeholders with no implementation; can be rebuilt properly post-v3.0 if needed | Roadmap Section 2 |
| _add new rows below_ | | | |

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | PowerShell Core (`pwsh`) on Linux has compatibility issues with M365 modules | Medium | High | Test early (task 0.6); fall back to Graph API-only mode for Linux deployments |
| 2 | Microsoft Graph API rate limiting (throttling) | Medium | Medium | Implement exponential backoff; cache aggressively; use delta queries for sync |
| 3 | M365 module deprecation (Microsoft changes cmdlets) | Low | Medium | Pin module versions; test before upgrading; prefer Graph API where possible |
| 4 | PowerShell session pool memory leaks | Medium | Medium | Implement session recycling (recreate after N commands); monitor memory |
| 5 | Azure AD app secret expiration | Medium | High | Alert when secret is within 14 days of expiry; UI shows expiry date |
| 6 | Large tenants (>10k users) cause sync performance issues | Medium | Medium | Implement pagination; batch upserts; background sync with progress indicator |
| 7 | Cross-platform PowerShell inconsistency (Windows vs Linux `pwsh`) | Medium | Medium | Test on both; prefer Graph API; document Windows-only limitations |
| 8 | AI hallucination on M365 remediation suggestions | Medium | High | Human-in-the-loop approval is mandatory for all M365 actions; AI only suggests, never executes |
| 9 | M365 credentials stored insecurely | Low | Critical | Use SysWatch's existing AES-256-GCM encryption; never log secrets; security review (task 13.10) |

---

## Notes

- This tracker should be updated at least weekly, or whenever a task status changes.
- The function checklists under each module phase are the source of truth for "what's ported."
- If a PowerShell function doesn't work as expected during porting, note it in the task's Notes column and decide whether to fix it, replace it with a Graph API call, or descope it.
- The M365 Developer Program tenant (task 0.5) is the recommended test environment — it provides a free E5 license with sample data.
- All destructive M365 operations (delete user, remove mailbox, remove team, etc.) MUST go through the human-in-the-loop approval workflow, even in testing.

---

*Last updated: 25 August 2026*
