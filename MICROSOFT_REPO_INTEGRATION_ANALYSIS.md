# Microsoft M365 Copilot Assessment Repository Integration Analysis

Date: 2026-06-05  
Scope: analysis only. No platform feature replacement is recommended.

## 1. Repository Reverse Engineering Report

### Existing CRA Platform Components

| Component | Status | Must Preserve | Notes |
|---|---|---:|---|
| Authentication | Working | Yes | MSAL login, backend ID token validation, internal CRA JWT, refresh/logout flow. Do not change. |
| Multi-tenant onboarding | Working | Yes | Tenant app registration, service principal, client secret, consent validation. Do not change. |
| Graph authentication | Working | Yes | Runtime collectors use tenant app client credentials and `.default` scope. Do not change. |
| Assessment execution engine | Working | Yes | `runtime_assessment_service.py` runs registry parameters, persists artifacts/findings, scores, recommendations, report. |
| Collector routing engine | Working | Yes | `_select_runtime()` chooses Graph or PowerShell from manifest plus `POWERSHELL_REQUIRED_PARAMETERS`. |
| Findings generation | Working | Yes | `_persist_finding()` creates normalized `assessment_findings`. |
| Recommendation generation | Working | Yes | Registry-driven `runtime_recommendation_service.py`; preserve model/contract. |
| Evidence storage | Working | Yes | `assessment_artifacts` stores telemetry, raw evidence, Graph/PowerShell details. |
| Dashboard APIs/frontend | Working | Yes | Frontend consumes existing assessment/report contracts. Do not break. |
| Report generation | Working | Yes | `cra_report_service.py` builds report rows from registry, findings, recommendations, artifacts. |

### Existing CRA Coverage

| Area | Count |
|---|---:|
| Registry parameters | 65 |
| Registry collectors | 65 |
| Registry rules | 65 |
| Registry recommendations | 65 |
| Collector manifest entries | 65 |

| Service | Current Parameters |
|---|---:|
| Entra | 19 |
| Teams | 15 |
| Purview | 9 |
| SharePoint | 9 |
| Exchange | 8 |
| OneDrive | 4 |
| M365 | 1 |

### Existing Assessment Workflow

1. User starts assessment via `POST /api/v1/assessments/start`.
2. `assessment_service.py` creates assessment/job.
3. Celery or local background task calls `run_assessment_job`.
4. Runtime seeds registry rows.
5. Runtime executes all 65 registry parameters.
6. `_select_runtime()` routes Graph collectors in `GRAPH_COLLECTORS`, PowerShell-required workload checks to PowerShell, then PowerShell by manifest preference.
7. Artifacts and findings are persisted.
8. Scores are calculated with `runtime_scoring_service.py`.
9. Recommendations are generated with `runtime_recommendation_service.py`.
10. Report bundle is generated with `cra_report_service.py`.

### Existing Report Workflow

`cra_report_service.py` reads:

- `assessments`
- `assessment_findings`
- `assessment_recommendations`
- `assessment_artifacts`
- registry metadata

It builds detailed parameter rows for all 65 parameters. Missing evidence becomes `not_collected`; failed collectors become `collection_error`.

## 2. Microsoft Repository Inventory

Repository: `C:\Users\Admin\Desktop\m365-copilot-automated-readiness-assessment`

| File | Purpose | Service Area | Graph | PowerShell | Recommendation | Scoring |
|---|---|---|---:|---:|---:|---:|
| `main.py` | CLI entrypoint, credential validation, orchestrator startup | All | Indirect | Indirect | No | No |
| `params.py` | Tenant ID and service selection | All | No | No | No | No |
| `Core/orchestrator.py` | High-level pipeline orchestration | All | Yes | Yes | Yes | No |
| `Core/orchestrator_pipelines.py` | Per-service async pipelines | M365, Entra, Purview, Defender, PP, Copilot Studio, A365 | Yes | Yes | Yes | No |
| `Core/get_m365_client.py` | M365 usage reports and site/user summaries | M365 | Yes | No | No | No |
| `Core/get_m365_info.py` | `/subscribedSkus` service-plan processing and M365 recommendations | M365 | Yes | No | Yes | No |
| `Core/get_entra_client.py` | Conditional Access, MFA registration, PIM, devices, consent, sign-ins, GSA | Entra | Yes | No | No | No |
| `Core/get_entra_info.py` | Entra service-plan recommendations | Entra | Yes | No | Yes | No |
| `Core/get_defender_client.py` | Defender API client/enrichment | Defender | Yes/API | No | No | No |
| `Core/get_defender_info.py` | Defender license/service-plan and Copilot security recommendations | Defender | Yes | No | Yes | No |
| `Core/get_purview_client.py` | Hydrates Purview object from PowerShell JSON | Purview | Limited | Yes | No | No |
| `Core/get_purview_info.py` | Purview service-plan and deployment recommendations | Purview | Yes | Yes | Yes | No |
| `Core/get_power_platform_client.py` | Power Platform environments, flows, apps, connectors, AI models, DLP, capacity, solutions | Power Platform | API | Yes fallback | No | No |
| `Core/get_power_platform_info.py` | Power Platform service-plan/deployment recommendations | Power Platform | API | Yes data source | Yes | No |
| `Core/get_copilot_studio_info.py` | Copilot Studio service-plan/deployment recommendations | Copilot Studio | Yes/API | Yes data source | Yes | No |
| `Core/a365/get_a365_client.py` | Graph beta Copilot package catalog via delegated PowerShell auth | A365 | Yes beta | Yes auth wrapper | No | No |
| `Core/a365/get_a365_detail_client.py` | A365 package detail fetch | A365 | Yes beta | No | No | No |
| `Core/a365/get_a365_info.py` | A365 catalog recommendation data | A365 | Yes beta | No | Yes | No |
| `Core/service_categorization.py` | Maps service plan names to service areas | All | No | No | No | No |
| `Core/get_recommendation.py` | Dynamic recommendation router | All | No | No | Yes | No |
| `Core/export_recommendations.py` | CSV/Excel export | All | No | No | Yes | No |
| `collect_purview_data.ps1` | Purview Compliance PowerShell data collection | Purview | No | Yes | No | No |
| `collect_power_platform_and_copilot_studio_data.ps1` | Power Platform/Copilot Studio admin data collection | PP/Copilot Studio | API token | Yes | No | No |
| `Recommendations/*` | Modular recommendation definitions | All | No | No | Yes | Implied by priority only |

Microsoft recommendation module counts:

| Area | Modules |
|---|---:|
| M365 | 90 |
| Purview | 36 |
| Defender | 18 |
| Power Platform | 17 |
| Entra | 13 |
| Copilot Studio | 11 |
| A365 | 1 |

## 3. Collector Mapping Matrix

### Microsoft Collector Discovery

| Collector | File | Service | Graph Endpoint / API | PowerShell Cmdlet | Output Fields |
|---|---|---|---|---|---|
| M365 license plans | `Core/get_m365_info.py` | M365 | `/subscribedSkUs` | None | SKU part number, SKU ID, enabled, consumed, service plan name/status |
| M365 sites/users/reports | `Core/get_m365_client.py` | M365 | `/sites`, `/users`, `/reports/get*` | None | users, sites, email/Teams/SP/OD usage, activations |
| Entra identity posture | `Core/get_entra_client.py` | Entra | CA, auth methods, identity protection, role management, access reviews, devices, sign-ins | None | CA summary, auth summary, risk, PIM, access reviews, devices, consent |
| Defender service plans | `Core/get_defender_info.py` | Defender | `/subscribedSkUs`; Defender APIs via client | None | Defender plan names/status, XDR/onboarding/security posture |
| Purview data | `collect_purview_data.ps1` + `Core/get_purview_client.py` | Purview | Limited | `Connect-IPPSSession`, `Get-DlpCompliancePolicy`, `Get-Label`, `Get-RetentionCompliancePolicy`, `Get-AdminAuditLogConfig`, etc. | DLP, labels, retention, audit, IRM, insider risk, comm compliance |
| Power Platform data | `collect_power_platform_and_copilot_studio_data.ps1` + `Core/get_power_platform_client.py` | Power Platform | `api.bap.microsoft.com`, `api.flow.microsoft.com`, `api.powerplatform.com` | `Connect-AzAccount`, `Get-AzAccessToken`, REST | environments, flows, apps, connectors, AI models, DLP, capacity, solutions |
| Copilot Studio | `Core/get_copilot_studio_info.py` | Copilot Studio | Graph/service plan + PP data | PP collector data | bot/agent/service-plan readiness |
| A365 catalog | `Core/a365/get_a365_client.py` | A365 | `/beta/copilot/admin/catalog/packages` | `Connect-MgGraph`, `Invoke-MgGraphRequest` | package catalog, package detail metadata |

### Existing CRA Collectors Not Exposed in Manifest

These already exist in `GRAPH_COLLECTORS` but are not in the 65-parameter manifest:

| Collector | Action |
|---|---|
| `assigned_license` | Add only if it is part of the approved 65 list; user list includes Assigned License, so expose safely. |
| `checking_sharing_permissions_for_each_sites_on_a_tenant` | Add if row 65 must be collected; existing code exists. |
| `non_admin_users_can_register_applications` | Add if row 54 must be collected; existing code exists. |
| `sensitivity_labels_are_applied` | Add if row 58 must be collected; existing code exists. |
| `teams_anonymous_users` | Add if row 13 must be collected; existing code exists. |
| `teams_external_unmanaged_user_communication` | Add if row 14 must be collected; existing code exists. |

## 4. Recommendation Mapping Matrix

Microsoft recommendation objects contain:

| Field | Meaning |
|---|---|
| `Service` | Recommendation area |
| `Feature` | Friendly feature name |
| `Status` | Service plan or insight status |
| `Priority` | High/Medium/Low/blank |
| `Observation` | Finding-like narrative |
| `Recommendation` | Remediation/adoption text |
| `LinkText` | Documentation label |
| `LinkUrl` | Documentation URL |

Existing CRA recommendation objects contain:

| Field | Meaning |
|---|---|
| `parameter_key` | CRA parameter identity |
| `severity` | Finding/registry severity |
| `title` | Recommendation title |
| `recommendation_text` | User-facing recommendation |
| `remediation_steps` | Step list |
| `effort` | Low/Medium/High |
| `impact` | Finding impact |
| `priority_score` | Calculated by CRA |

Mapping rule:

| Microsoft Field | CRA Target |
|---|---|
| `Feature` | `title` or source metadata |
| `Observation` | `impact` or finding `evaluated_value` |
| `Recommendation` | `recommendation_text` / first `remediation_steps` |
| `Priority` | priority score input only, not direct replacement |
| `LinkUrl` | optional docs link in recommendation metadata if schema is extended |

Recommendation action: **ENHANCE_EXISTING only**. Do not replace `runtime_recommendation_service.py`.

## 5. Readiness Scoring Design

### Existing CRA Scoring

Existing scoring is registry-driven:

| Parameter | Threshold | Weight | Pass Logic | Fail Logic |
|---|---|---:|---|---|
| All 65 current parameters | In `rules.json` expression/pass criteria | In `parameters.json`/manifest `scoring_weight` | Collector returns `pass`; no deduction | Collector returns `fail`/`warning`; severity deduction x weight |

Domain score fields:

| Domain | Assessment Field |
|---|---|
| `identity_access` | `identity_score` |
| `security`, `best_practice`, `governance` | `security_score` |
| `compliance` | `compliance_score` |
| `collaboration` | `collaboration_score` |
| `licensing` | `licensing_score` |

Status behavior:

| Status | Scoring Behavior |
|---|---|
| `pass` | No deduction |
| `fail` | Full severity x weight deduction |
| `warning` | 45% of severity x weight deduction |
| `collection_error` | No deduction; treated as evidence problem |
| `licensing_required` | No deduction |
| `manual_validation` | No deduction |

### Microsoft Scoring

The Microsoft repo does not have a comparable CRA score engine. It uses recommendation priority and service-plan status, not a persisted readiness score model.

Safe design: keep CRA scoring as-is. If Microsoft service-plan readiness is added later, add new registry parameters with domain `licensing` or service-specific domains and explicit weights.

## 6. CRA Parameter Mapping

Summary:

| Coverage | Meaning |
|---|---|
| Already Covered | Current CRA has collector logic and registry row. |
| Partially Covered | Current CRA has some logic, but collection may depend on PowerShell/session/permission/tenant capability. |
| Missing | Current approved list includes a parameter not exposed by registry/manifest. |

| Parameter Area | Existing Collector | Repository Coverage | Action Required |
|---|---|---|---|
| Entra ID core users/admins/guests/CA/MFA/apps | Graph collectors and/or Entra PowerShell registry rows | Microsoft Entra client has stronger summarization for CA, MFA, PIM, consent, devices | ENHANCE_EXISTING |
| `assigned_license` | Implemented in `GRAPH_COLLECTORS`, not manifest | Microsoft `/subscribedSkUs` logic helps | ENHANCE_EXISTING / expose current collector |
| `unused_licenses_count` | Not in current 65 registry observed | Microsoft `/subscribedSkUs` plus user assignment logic helps strongly | ADD_NEW_COLLECTOR if approved |
| Exchange mailbox/activity | Existing Graph/Powershell collectors | Microsoft M365 reports help for email activity, not OWA/calendar config | KEEP_EXISTING |
| Exchange OWA/calendar/Customer Lockbox | Existing Exchange PowerShell script | Microsoft does not improve these exact controls materially | KEEP_EXISTING |
| Purview DLP/audit/labels | Existing Purview PowerShell script | Microsoft Purview script has broader cmdlets and object model | ENHANCE_EXISTING |
| Teams meeting/app/client policy checks | Existing Teams PowerShell script | Microsoft repo is weak for exact Teams policy controls | KEEP_EXISTING |
| Teams anonymous/external unmanaged | Implemented in Graph collectors, not registry manifest | Microsoft repo does not directly solve | ENHANCE_EXISTING / expose current collector |
| OneDrive/SharePoint usage/settings | Existing Graph/Powershell collectors | Microsoft M365 reports help with usage metrics only | ENHANCE_EXISTING selectively |
| SharePoint site sensitivity keywords/sharing permissions | Existing or hidden Graph collector + PowerShell evidence | Microsoft Purview labels help as source data | ENHANCE_EXISTING |

Do not create duplicate collectors for parameters already implemented.

## 7. Gap Analysis

| Missing / Weak Functionality | Graph Endpoint | Graph Permission | PowerShell Cmdlet | License Requirement | Effort |
|---|---|---|---|---|---|
| Assigned License exposed as approved parameter | `/users`, `/subscribedSkUs` | `User.Read.All`, `Organization.Read.All` | None | M365 tenant licensing | Low |
| Unused licenses count | `/subscribedSkUs`, `/users?$select=assignedLicenses` | `Organization.Read.All`, `User.Read.All` | None | License inventory readable | Low |
| Teams anonymous users | Limited Graph support | App-only Graph is insufficient for full Teams policy | `Get-CsTeamsMeetingPolicy` / Teams policy cmdlets | Teams admin module/role | Medium |
| Teams external unmanaged communication | Limited Graph support | App-only Graph is insufficient | `Get-CsTenantFederationConfiguration`, related external access policy cmdlets | Teams admin role | Medium |
| Purview richer DLP/labels/audit | Limited Graph/security score endpoints | `SecurityEvents.Read.All`, `Reports.Read.All` partial only | `Connect-IPPSSession`, `Get-DlpCompliancePolicy`, `Get-Label`, `Get-AdminAuditLogConfig` | Purview/Compliance permissions | Medium |
| Power Platform/Copilot Studio | Power Platform APIs, not Microsoft Graph only | Power Platform admin/API permissions | Microsoft repo PS collector | Power Platform admin role | High |
| A365 agent catalog | `/beta/copilot/admin/catalog/packages` | `CopilotPackages.Read.All` delegated | `Connect-MgGraph` wrapper | Copilot/A365 preview availability | High/manual auth |

## 8. Collection Error Resolution Plan

| Parameter | Why Current Collection Fails | Graph App-Only Limitation | Teams PS | Exchange PS | Purview PS | Manual Validation |
|---|---|---:|---:|---:|---:|---:|
| Copilot Integration Enabled | Requires Teams app catalog/permission/setup policy visibility; Graph app-only often insufficient | Yes | Yes: `Get-TeamsApp`, `Get-CsTeamsAppPermissionPolicy`, `Get-CsTeamsAppSetupPolicy` | No | No | Sometimes |
| Meeting Policies Configuration | Requires Teams meeting policy cmdlets | Yes | Yes: `Get-CsTeamsMeetingPolicy` | No | No | No if Teams PS works |
| Meeting Recording Retention Policies | Requires Teams meeting policy recording fields | Yes | Yes: `Get-CsTeamsMeetingPolicy` | No | No | No if Teams PS works |
| Meeting Transcription Enabled | Requires Teams meeting policy transcription field | Yes | Yes: `Get-CsTeamsMeetingPolicy` | No | No | No if Teams PS works |
| Teams Channel Email Addresses | Requires Teams client/channel email configuration | Partial/limited | Yes: `Get-CsTeamsClientConfiguration` or channel cmdlets | Possibly Exchange transport context, but Teams PS primary | No | Sometimes |
| Teams File Storage Option | Requires Teams client configuration external storage flags | Yes | Yes: `Get-CsTeamsClientConfiguration` | No | No | No if Teams PS works |
| Teams Lobby Bypass | Requires `AutoAdmittedUsers` from meeting policies | Yes | Yes: `Get-CsTeamsMeetingPolicy` | No | No | No |
| Teams Meeting Chat | Requires `MeetingChatEnabledType` | Yes | Yes: `Get-CsTeamsMeetingPolicy` | No | No | No |
| Third Party Apps Allowed | Requires Teams app permission policy | Yes | Yes: `Get-CsTeamsAppPermissionPolicy` | No | No | No |
| Customer Lockbox | Requires org/config compliance feature; can be Exchange/Purview oriented | Partial | No | Yes: `Get-OrganizationConfig` | Also possible via compliance/org config | Sometimes if licensing hides field |
| External Storage Providers In OWA | Requires OWA mailbox policy | Yes | No | Yes: `Get-OwaMailboxPolicy` | No | No |
| Full Calendar Schedules Shared Externally | Requires Exchange sharing policy/org config | Yes | No | Yes: `Get-SharingPolicy`, `Get-OrganizationConfig` | No | No |
| Custom Banned Password List | Microsoft does not expose custom banned word list/count cleanly to app-only Graph | Yes | No | No | No | Yes unless tenant evidence can prove enabled/count |
| DLP Rules Configured | Requires Purview compliance policy access | Partial | No | No | Yes: `Get-DlpCompliancePolicy` | No if Purview PS works |
| Sensitivity Labels Configured And Applied | Requires labels and application/deployment evidence | Partial | No | No | Yes: `Get-Label`, label policy/cmdlets | Sometimes for applied-to-content evidence |
| Information Protection Labels Applied | Same as labels; tenant config is easier than content application proof | Partial | No | No | Yes: `Get-Label`, `Get-LabelPolicy` | Sometimes |

## 9. Safe Integration Plan

### Phase 1: No-Risk Improvements

| Change | Files Affected | Risk | Dependencies | Rollback |
|---|---|---|---|---|
| Expose already-implemented Graph collectors missing from registry only if they are in the approved 65 list | registry JSON only | Low | Existing `GRAPH_COLLECTORS` | Revert registry entries |
| Add better backend error visibility for collector failures | frontend only, already isolated | Low | Existing events | Revert UI component |
| Add documentation/mapping files | docs only | None | None | Delete doc |

### Phase 2: New Collectors Only

| Change | Files Affected | Risk | Dependencies | Rollback |
|---|---|---|---|---|
| Add `unused_licenses_count` collector | `graph_cra_collector_service.py`, registry JSON | Low/Medium | `/subscribedSkUs`, `/users` | Remove registry + collector |
| Add Microsoft-style M365 service-plan inventory as optional evidence collector | new service module + registry only | Medium | `Organization.Read.All` | Disable parameter |
| Add Purview enhanced collector using Microsoft script techniques | PowerShell script + registry mapping | Medium | Compliance PowerShell auth | Revert script/registry |

### Phase 3: Scoring Enhancements

| Change | Files Affected | Risk | Dependencies | Rollback |
|---|---|---|---|---|
| Add explicit weights for new license/service-plan parameters | `scoring.json`, `parameters.json` | Low | Approved parameters | Revert JSON |
| Keep `collection_error` non-deducting | None | None | Existing policy | No change |

### Phase 4: Recommendation Enhancements

| Change | Files Affected | Risk | Dependencies | Rollback |
|---|---|---|---|---|
| Translate Microsoft recommendation text into existing registry recommendation templates | `recommendations.json` | Low | No schema change | Revert JSON |
| Add docs links only if schema/UI supports it | registry/report optional | Medium | UI/report support | Remove field |

## 10. Protection Rules

Do not rewrite:

- Authentication
- Tenant onboarding
- API contracts
- Assessment engine
- Collector routing engine
- Findings engine
- Report engine
- Frontend data contracts

Only add:

- Missing collectors
- Registry entries for approved parameters
- Optional recommendation text enhancements
- PowerShell collector robustness for workload-specific parameters

## Final Recommendation

Use the Microsoft repository as a reference library, not a replacement backend. The most useful parts are:

1. `/subscribedSkUs` service-plan mapping from `get_m365_info.py`.
2. Entra summarization patterns from `get_entra_client.py`.
3. Purview PowerShell collection pattern from `collect_purview_data.ps1`.
4. Power Platform/Copilot Studio collectors if the product later expands beyond the 65 CRA parameters.
5. Recommendation text as enrichment for existing CRA recommendation templates.

The current 65-parameter platform should remain authoritative.
