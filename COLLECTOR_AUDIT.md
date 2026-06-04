# CRA Collector Audit

Date: 2026-05-31  
Scope: `CRA-Tool` backend runtime from assessment start through evidence collection, scoring, and report generation.

## Executive Summary

Every assessment is ending with zero collected controls because the active runtime does not produce persisted findings.

Observed in local dev DB `CRA-Tool/cra.db`:

- `assessments`: 11
- `assessment_findings`: 0
- `assessment_artifacts`: 520
- `assessment_artifacts.status`: 520 `failed`
- Latest jobs: `collector_total=65`, `collector_collected=0`, `collector_incomplete=65`
- Latest assessments: `status=incomplete`, `overall_score=None`, `total_findings=None`

Primary data-loss point:

`runtime_assessment_service._collect_findings()` calls `PowerShellExecutionEngine.run_collector()`. When the collector returns errors, throws, or remains `not_collected`, the runtime persists an artifact and then `continue`s before `_persist_finding()`. Therefore no `assessment_findings` rows are created. With zero findings, scoring and recommendation generation are skipped, and reports render artifact-only sections as `NOT COLLECTED`.

## Actual Runtime Path

```text
POST /api/v1/assessments/start
  -> assessment_service.start_assessment()
  -> creates Assessment(status=queued)
  -> creates AssessmentJob(status=queued)
  -> run_assessment_task.apply_async(job_id)

Celery worker
  -> app/tasks/assessment_tasks.py:run_assessment_task()
  -> runtime_assessment_service.run_assessment_job()
  -> _collect_findings()
  -> PowerShellExecutionEngine.run_collector()
  -> PowerShellExecutor.execute()
  -> parse_collector_contract()
  -> optional CSV ingestion
  -> _persist_finding() only if collector_result has no errors and status != not_collected
  -> if collector_incomplete > 0: assessment.status=incomplete and scoring/report findings are skipped
```

## Why Reports Show 0 Collected Controls and 0% Readiness

1. The active runtime is `phase7b_powershell`, not a Microsoft Graph collector runtime.
2. The registry has 65 parameters and 65 collector entries.
3. All 65 registry `graph_endpoint` values are empty.
4. The only generic Graph runtime, `GraphRuntime.collect_endpoint()`, is not called by `runtime_assessment_service`.
5. PowerShell scripts write a common JSON contract through `Write-CraContract`.
6. `Write-CraContract` always emits a finding with `status = "not_collected"`.
7. The runtime tries CSV rescue through `_csv_evidence_contract()`, but the generated CSV files do not contain canonical `status`, `pass_fail`, or `result` columns required by `normalize_evidence_row()` to determine pass/fail.
8. In the local DB, all collector artifacts are `failed`, no findings exist, and job metadata says all 65 collectors failed or were not collected.
9. Since `collector_incomplete > 0`, `run_assessment_job()` marks the assessment `incomplete` and returns before `apply_scores()`.
10. Report generation has no findings to summarize, so collected controls are 0 and readiness has no real score.

## Collector Inventory

Registry totals:

- Parameters: 65
- Collectors: 65
- Manifest entries: 65
- Collector types: 56 `powershell`, 8 `portal`, 1 `manual`
- Non-empty registry Graph endpoints: 0

Mapped PowerShell collector scripts:

- `app/powershell/entra/entra_master.ps1`
- `app/powershell/exchange/exchange_master.ps1`
- `app/powershell/purview/purview_master.ps1`
- `app/powershell/teams/teams_master.ps1`
- `app/powershell/onedrive/onedrive_master.ps1`
- `app/powershell/sharepoint/sharepoint_master.ps1`

Collector services:

- `PowerShellExecutionEngine`
- `PowerShellExecutor`
- `PowerShellCollectorResolver`
- `GraphRuntime` exists but is not used by assessment collection
- CSV ingestion: `parse_csv_evidence()`, `normalize_evidence_row()`
- Report collection reader: `cra_report_service._load_findings()` and `_load_artifacts()`

## Microsoft Graph Calls Found

Runtime/deployment Python Graph calls:

- `GET /me`
- `GET /organization`
- `POST /applications`
- `PATCH /applications/{application_object_id}`
- `GET /applications/{application_object_id}`
- `GET /applications?$filter=appId eq '{application_client_id}'`
- `POST /applications/{application_object_id}/addPassword`
- `GET /servicePrincipals?$filter=appId eq '00000003-0000-0000-c000-000000000000'`
- `POST /servicePrincipals`
- `GET /servicePrincipals?$filter=appId eq '{app_id}'`
- `GET /servicePrincipals/{service_principal_id}`
- `GET /servicePrincipals/{service_principal_id}/appRoleAssignments`
- Generic unused collector path: `GraphRuntime.collect_endpoint(endpoint)`

PowerShell Microsoft Graph cmdlets:

- `Get-MgOrganization`
- `Get-MgDirectoryRole`
- `Get-MgDirectoryRoleMember`
- `Get-MgUser`
- `Get-MgReportAuthenticationMethodUserRegistrationDetail`
- `Get-MgIdentityConditionalAccessPolicy`
- `Get-MgApplication`
- `Get-MgPolicyAuthorizationPolicy`
- `Get-MgReportOneDriveUsageAccountDetail`
- `Get-MgReportOneDriveActivityUserDetail`

## Required Graph Permissions

Deployment currently requests these Microsoft Graph application permissions:

- `Application.Read.All`
- `Directory.Read.All`
- `Group.Read.All`
- `User.Read.All`
- `Reports.Read.All`
- `AuditLog.Read.All`
- `Policy.Read.All`
- `RoleManagement.Read.Directory`
- `UserAuthenticationMethod.Read.All`
- `Team.ReadBasic.All`
- `Sites.Read.All`
- `Files.Read.All`

Delegated deployment-token permissions:

- `User.Read`
- `Application.ReadWrite.All`
- `AppRoleAssignment.ReadWrite.All`
- `Directory.Read.All`

Collector script permission mapping:

- Entra: `Directory.Read.All`, `Policy.Read.All`, `Application.Read.All`, `RoleManagement.Read.Directory`, `AuditLog.Read.All`, `UserAuthenticationMethod.Read.All`
- Teams: `Reports.Read.All`, `Group.Read.All`, `Team.ReadBasic.All`, plus Microsoft Teams module connection/admin rights
- OneDrive: `Reports.Read.All`, `Files.Read.All`, `Sites.Read.All`
- SharePoint: `Reports.Read.All`, `Sites.Read.All`, `Directory.Read.All`, plus PnP/SharePoint admin URL and admin rights
- Exchange: no registry Graph endpoint; requires Exchange Online PowerShell/RBAC
- Purview: no registry Graph endpoint; requires IPPSSession/compliance RBAC

Currently missing Graph permissions by code comparison:

- None of the Graph scopes declared in the PowerShell scripts are absent from `REQUIRED_APPLICATION_PERMISSIONS`.

Important non-Graph gaps:

- Exchange, Purview, Teams, and SharePoint collectors depend on PowerShell modules and admin/RBAC sessions outside Graph.
- SharePoint collectors are broken because `sharepoint_master.ps1` requires `collector.admin_url`, but every SharePoint manifest entry has empty `admin_url`.

## Collector Implementation Classification

- `WORKING`: 0
- `PARTIAL`: 48
- `MOCK`: 0
- `NOT_IMPLEMENTED`: 9
- `BROKEN`: 8

No collector script was found returning mock data. The runtime explicitly rejects mock/simulated collector contracts. No collector function directly returns Python `None`; however, failed artifacts in the local DB have `result=None` and `contract=None` because exceptions were caught before a collector result was produced.

## Never-Called Collectors / Services

The following implementation exists but is not on the active assessment path:

- `GraphRuntime.collect_endpoint()`
- Registry `graph_endpoint` collection path; all current registry Graph endpoints are empty.
- `findings.finding_engine.build_finding()`
- `findings.rule_engine.evaluate_rule()` as the primary runtime evaluator

## Per-Parameter Collector Matrix

| # | Parameter Name | Collector Function | Graph Endpoint | Required Permission | Current Status | Reason |
|---:|---|---|---|---|---|---|
| 1 | Global Administrator Accounts | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 2 | Guest users count | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 3 | User Information | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 4 | Guest Invite Settings | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 5 | Entra - Third Party App Integrations | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 6 | Tenant Collaboration Invitations | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 7 | Authentication methods enabled | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 8 | Admin Consent Workflow | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 9 | CAP policies for risky sign-ins | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 10 | Users without MFA | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 11 | Unused licenses count | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 12 | Emergency Access Accounts | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 13 | User Consent For Applications | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 14 | Custom Banned Password List | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 15 | Non-Admin Users can register Applications | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 16 | Restricted Access To Microsoft Entra Admin Centre | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 17 | Self-Service Password Reset Authentication Method | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 18 | Account enabled | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 19 | Assigned License | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 20 | Conditional Access Policies (Exclusion) | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 21 | Entra - Tenant Creation By Non-Admin | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 22 | Devices without compliance policies | `app/powershell/entra/entra_master.ps1` | `(none)` | Directory.Read.All; Policy.Read.All; Application.Read.All; RoleManagement.Read.Directory; AuditLog.Read.All; UserAuthenticationMethod.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 23 | Mailboxes Status (Active/Inactive) | `app/powershell/exchange/exchange_master.ps1` | `(none)` | No Graph endpoint; ExchangeOnlineManagement RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 24 | Mailbox Storage usage | `app/powershell/exchange/exchange_master.ps1` | `(none)` | No Graph endpoint; ExchangeOnlineManagement RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 25 | Number of emails read/received | `app/powershell/exchange/exchange_master.ps1` | `(none)` | No Graph endpoint; ExchangeOnlineManagement RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 26 | Number of emails sent | `app/powershell/exchange/exchange_master.ps1` | `(none)` | No Graph endpoint; ExchangeOnlineManagement RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 27 | External Storage Providers In OWA | `app/powershell/exchange/exchange_master.ps1` | `(none)` | No Graph endpoint; ExchangeOnlineManagement RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 28 | Full Calendar Schedules Able To Be Shared Externally | `app/powershell/exchange/exchange_master.ps1` | `(none)` | No Graph endpoint; ExchangeOnlineManagement RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 29 | Customer Lockbox | `app/powershell/entra/entra_master.ps1` | `(none)` | Not declared | BROKEN | manifest expects evidence.csv, but mapped script does not generate it |
| 30 | Compliance Score overview | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 31 | Secure Score percentage | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 32 | Audit log retention duration | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 33 | Sensitivity Labels configured and applied | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 34 | Audit Logs enabled | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 35 | DLP rules configured | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 36 | Information Protection Labels applied | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 37 | Sensitivity Labels applied to Teams | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 38 | Sensitivity labels are applied | `app/powershell/purview/purview_master.ps1` | `(none)` | No Graph endpoint; IPPSSession/Compliance RBAC | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 39 | Guest access enabled / disabled | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 40 | Minimum number of owners | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 41 | Orphan Teams | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 42 | Teams - Anonymous Users | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 43 | Teams - External Unmanaged User Communication | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 44 | Active /Inactive teams | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 45 | Activer/Inactive Teams users | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 46 | Teams - File Storage Option | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 47 | Teams with external users | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 48 | Copilot integration enabled | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 49 | Meeting transcription enabled | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 50 | Meeting recording retention policies | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 51 | Meeting Policies configuration | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 52 | Teams - Channel Email Addresses | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 53 | Teams - Lobby Bypass | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 54 | Teams - Meeting Chat | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 55 | Third-party apps allowed | `app/powershell/teams/teams_master.ps1` | `(none)` | Reports.Read.All; Group.Read.All; Team.ReadBasic.All + MicrosoftTeams connection | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 56 | External sharing settings | `app/powershell/onedrive/onedrive_master.ps1` | `(none)` | Reports.Read.All; Files.Read.All; Sites.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 57 | Total active users on OneDrive | `app/powershell/onedrive/onedrive_master.ps1` | `(none)` | Reports.Read.All; Files.Read.All; Sites.Read.All | PARTIAL | script generates CSV, but Write-CraContract emits not_collected and rows lack pass/fail/status fields |
| 58 | Active Sites count | `app/powershell/sharepoint/sharepoint_master.ps1` | `(none)` | Reports.Read.All; Sites.Read.All; Directory.Read.All + PnP admin URL | NOT_IMPLEMENTED | portal/manual collector type; no Graph endpoint; no automated criteria evaluator |
| 59 | Active users on SharePoint | `app/powershell/sharepoint/sharepoint_master.ps1` | `(none)` | Reports.Read.All; Sites.Read.All; Directory.Read.All + PnP admin URL | BROKEN | sharepoint_master.ps1 requires admin_url, but manifest admin_url is empty |
| 60 | SharePoint - Modern Authentication | `app/powershell/sharepoint/sharepoint_master.ps1` | `(none)` | Reports.Read.All; Sites.Read.All; Directory.Read.All + PnP admin URL | BROKEN | sharepoint_master.ps1 requires admin_url, but manifest admin_url is empty |
| 61 | Storage Quota consumption | `app/powershell/sharepoint/sharepoint_master.ps1` | `(none)` | Reports.Read.All; Sites.Read.All; Directory.Read.All + PnP admin URL | BROKEN | sharepoint_master.ps1 requires admin_url, but manifest admin_url is empty |
| 62 | Sharing Settings (External/Internal) | `app/powershell/sharepoint/sharepoint_master.ps1` | `(none)` | Reports.Read.All; Sites.Read.All; Directory.Read.All + PnP admin URL | BROKEN | sharepoint_master.ps1 requires admin_url, but manifest admin_url is empty |
| 63 | SharePoint & OneDrive Guest Access Expiry | `app/powershell/sharepoint/sharepoint_master.ps1` | `(none)` | Reports.Read.All; Sites.Read.All; Directory.Read.All + PnP admin URL | BROKEN | sharepoint_master.ps1 requires admin_url, but manifest admin_url is empty |
| 64 | Getting all sites with Sensitivity keywords on a Tenant | `app/powershell/sharepoint/sharepoint_master.ps1` | `(none)` | Reports.Read.All; Sites.Read.All; Directory.Read.All + PnP admin URL | BROKEN | sharepoint_master.ps1 requires admin_url, but manifest admin_url is empty |
| 65 | Checking Sharing permissions for each sites on a Tenant | `app/powershell/sharepoint/sharepoint_master.ps1` | `(none)` | Reports.Read.All; Sites.Read.All; Directory.Read.All + PnP admin URL | BROKEN | sharepoint_master.ps1 requires admin_url, but manifest admin_url is empty |

## Fully Implemented Collectors

None meet the `WORKING` bar. A working collector must collect evidence, evaluate criteria, return pass/warning/fail, persist an `AssessmentFinding`, contribute to score, and appear in report output as collected.

## Mock Collectors

No mock collector implementation was found. The runtime has explicit mock rejection in `PowerShellExecutionEngine._contract_uses_mock_data()`.

## Collectors Returning None

No collector function intentionally returns `None`.

Observed local artifacts have `result=None` and `contract=None` because the outer collector exception path persisted failed artifacts before a collector result was available.

## Data Loss Points

1. `Write-CraContract` emits `not_collected`.
2. CSV normalization maps rows without `status`, `pass_fail`, or `result` to `not_collected`.
3. `_collect_findings()` does not persist findings when collector results contain errors.
4. `_collect_findings()` does not persist findings when collector result status is `not_collected`.
5. `run_assessment_job()` skips scoring/recommendations/reports when any collector is incomplete.
6. Reports fall back to artifact sections and display `NOT COLLECTED`.

## Immediate Fix Order

1. Fix PowerShell subprocess execution so collector exceptions include real error messages in artifacts.
2. Stop using `Write-CraContract` as a final finding contract; either emit evaluated pass/fail per parameter or route every generated CSV through a real criteria evaluator.
3. Add per-parameter evaluators for the generated CSV files.
4. Populate registry `graph_endpoint` values or replace the runtime with real Graph collector services.
5. Add SharePoint `admin_url` derivation from tenant verified domain or configuration.
6. Persist failed collector diagnostics with exception type, message, and traceback-safe location.
7. Do not mark the whole assessment incomplete solely because one collector fails; score collected controls and mark missing controls separately.
