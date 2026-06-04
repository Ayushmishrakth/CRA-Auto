# Microsoft 365 Reports + Teams Collector Implementation Report

Generated: 2026-06-01

## Scope

Phase 8.7 implemented Microsoft 365 usage report collectors and Microsoft Teams collectors using `PARAMETER_DATA_COLLECTION_MAP.md` and the Phase 8.6 collector architecture as references.

No runtime redesign was performed. New collectors are registered in the existing `GRAPH_COLLECTORS` registry and flow through the existing assessment artifact, finding, scoring, recommendation, reporting, and dashboard paths.

## Files Changed

| Area | File | Change |
|---|---|---|
| Collectors | `CRA-Tool/app/services/graph_cra_collector_service.py` | Added Microsoft 365 report CSV helpers, usage collectors, Teams Graph owner/member collectors, Teams admin policy limitation collectors, and registry entries. |
| Readiness API | `CRA-Tool/app/services/assessment_service.py` | Extended readiness response with `collaboration_readiness`, `adoption_readiness`, and `teams_readiness`. |

## Collector Architecture

Runtime path:

`assessment registry -> GRAPH_COLLECTORS -> collector/normalizer/evaluator -> assessment_artifacts -> assessment_findings -> scoring -> recommendations -> report bundle -> readiness dashboard`

The runtime remains registry-driven. No separate execution path was introduced.

## Implemented Parameters

### Microsoft 365 Reports

| Parameter Key | Endpoint | Evidence Generated | Status |
|---|---|---|---|
| `mailboxes_status_active_inactive` | `/reports/getEmailActivityUserDetail(period='D30')` | active mailboxes, inactive mailboxes, active ratio | Implemented |
| `mailbox_storage_usage` | `/reports/getMailboxUsageDetail(period='D30')` | mailbox size, quota, utilization ratio | Implemented |
| `number_of_emails_read_received` | `/reports/getEmailActivityUserDetail(period='D30')` | read ratio, engagement metrics | Implemented |
| `number_of_emails_sent` | `/reports/getEmailActivityUserDetail(period='D30')` | average sent per user | Implemented |
| `active_inactive_teams` | `/reports/getTeamsTeamActivityDetail(period='D30')` | active team count, inactive team count | Implemented |
| `activer_inactive_teams_users` | `/reports/getTeamsUserActivityUserDetail(period='D30')` | active users, inactive users, inactive ratio | Implemented |
| `active_sites_count` | `/reports/getSharePointSiteUsageDetail(period='D30')` | active SharePoint sites and active ratio | Implemented |
| `active_users_on_sharepoint` | `/reports/getSharePointActivityUserDetail(period='D30')` | active SharePoint users and active ratio | Implemented |
| `total_active_users_on_onedrive` | `/reports/getOneDriveActivityUserDetail(period='D30')` | active OneDrive users and active ratio | Implemented |

### Microsoft Teams

| Parameter Key | Collection Source | Evidence Generated | Status |
|---|---|---|---|
| `guest_access_enabled_disabled` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `minimum_number_of_owners` | `/groups` + `/groups/{id}/owners` | teams, owners, teams with fewer than 2 owners | Implemented |
| `orphan_teams` | `/groups` + `/groups/{id}/owners` | teams, owner counts, orphan teams | Implemented |
| `teams_anonymous_users` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `teams_external_unmanaged_user_communication` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `teams_file_storage_option` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `teams_with_external_users` | `/groups` + `/groups/{id}/members` | teams, members, guest users, external ratio | Implemented |
| `copilot_integration_enabled` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `meeting_transcription_enabled` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `meeting_recording_retention_policies` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `meeting_policies_configuration` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `teams_channel_email_addresses` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `teams_lobby_bypass` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `teams_meeting_chat` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |
| `third_party_apps_allowed` | Teams admin Graph surface | Microsoft Graph Teams admin response/error | Implemented |

## Live Validation

Validation tenant: `fe4eff9a-f69c-48c0-921d-8006a6d5beb2`

Fresh assessment:

| Field | Value |
|---|---|
| Assessment ID | `8b7d4159-7eb7-457b-9ff1-8061e9134a8f` |
| Job ID | `638d6b0b-75db-49c2-8edd-9fc10a639633` |
| Assessment status | `completed` |
| Progress | `100.0` |
| Collector total | `44` |
| Collector collected | `44` |
| Collector incomplete | `0` |
| Graph calls | `68` |
| Artifacts | `44` |
| Findings | `44` |
| Recommendations | `44` |
| Reports | `2` |

Scores:

| Score | Value |
|---|---:|
| Overall | 27.63 |
| Identity | 0.0 |
| Security | 100.0 |
| Compliance | 100.0 |
| Collaboration | 0.0 |
| Licensing | 99.0 |

Finding status counts:

| Status | Count |
|---|---:|
| Pass | 13 |
| Fail | 31 |

## Readiness Metrics

The readiness endpoint now returns:

| Readiness Bucket | Score | Total | Pass | Fail | Warning |
|---|---:|---:|---:|---:|---:|
| Identity | 0.0 | 0 | 0 | 0 | 0 |
| Security | 100.0 | 18 | 6 | 12 | 0 |
| Licensing | 99.0 | 2 | 1 | 1 | 0 |
| Collaboration | 0.0 | 24 | 6 | 18 | 0 |
| Adoption | 14.29 | 7 | 1 | 6 | 0 |
| Teams | 29.41 | 17 | 5 | 12 | 0 |

## Phase 8.7 Result Matrix

| Parameter Key | Category | Result | Severity | Last Result |
|---|---|---|---|---|
| `active_inactive_teams` | Best Practice | pass | info | 0 active team(s), 0 inactive team(s) |
| `active_sites_count` | Best Practice | fail | medium | 0 active SharePoint site(s) out of 0 (0.0%) |
| `active_users_on_sharepoint` | Best Practice | fail | medium | 0 active SharePoint user(s) out of 0 (0.0%) |
| `activer_inactive_teams_users` | Governance | pass | info | 0 active Teams user(s), 0 inactive Teams user(s), inactive ratio 0.0% |
| `copilot_integration_enabled` | Governance | fail | critical | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `guest_access_enabled_disabled` | Security | fail | medium | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `mailbox_storage_usage` | Best Practice | pass | info | 0 mailbox(es) exceed 75% storage utilization; maximum utilization 0.0% |
| `mailboxes_status_active_inactive` | Governance | fail | critical | 0 active mailbox(es), 0 inactive mailbox(es), active ratio 0.0% |
| `meeting_policies_configuration` | Governance | fail | high | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `meeting_recording_retention_policies` | Best Practice | fail | medium | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `meeting_transcription_enabled` | Governance | fail | high | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `minimum_number_of_owners` | Best Practice | pass | info | 0 team(s) have fewer than 2 owners |
| `number_of_emails_read_received` | Best Practice | fail | info | 0.0% of users read more than 70% of received emails |
| `number_of_emails_sent` | Best Practice | fail | info | Average sent email count per user is 0.0 |
| `orphan_teams` | Governance | pass | info | 0 orphan team(s) found |
| `teams_anonymous_users` | Security | fail | info | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `teams_channel_email_addresses` | Governance | fail | low | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `teams_external_unmanaged_user_communication` | Security | fail | info | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `teams_file_storage_option` | Security | fail | medium | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `teams_lobby_bypass` | Best Practice | fail | medium | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `teams_meeting_chat` | Governance | fail | medium | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `teams_with_external_users` | Governance | pass | info | 0 team(s) have external users (0.0% of teams) |
| `third_party_apps_allowed` | Governance | fail | high | Teams admin policy data unavailable because Microsoft returned `AADSTS500014`. |
| `total_active_users_on_onedrive` | Governance | fail | info | 0 active OneDrive user(s) out of 0 (0.0%) |

## Graph And Licensing Limitations

Microsoft 365 Reports endpoints were reachable and returned `200 application/octet-stream`, but the current tenant returned header-only CSV datasets for the D30 report period. The collectors persisted that real Graph output and evaluated the parameters using the Excel rules.

Teams group, owner, and member Graph endpoints were reachable:

- `/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')`
- `/groups/{id}/owners`
- `/groups/{id}/members`

Teams channel/teamwork admin surfaces returned Microsoft error `AADSTS500014`, indicating the Teams service principal/resource is disabled or the subscription has lapsed for the target tenant. Policy collectors preserve that Microsoft response as evidence and generate failed findings instead of creating fake policy states.

Teams PowerShell limitations:

- Teams policy settings such as meeting transcription, lobby bypass, guest access, channel email, app permission, and recording retention are Teams PowerShell-first in the parameter map.
- No delegated Teams PowerShell session is available to the assessment runtime.
- The implementation uses real Microsoft Graph admin surface responses as evidence where Teams PowerShell-only policy data cannot be collected by the app-only Graph runtime.

## Verification

Backend syntax check:

`.\venv\Scripts\python.exe -m py_compile app\services\graph_cra_collector_service.py app\services\assessment_service.py app\services\runtime_assessment_service.py app\api\v1\assessments.py`

Result: passed.

Frontend build:

`npm run build`

Result: passed. Vite reported the existing chunk-size warning for the main bundle.

Live assessment:

Result: completed with 44/44 collectors executed, 44 artifacts, 44 findings, 44 recommendations, scores, and report rows.

## Coverage

| Coverage Area | Result |
|---|---:|
| Phase 8.7 requested parameters implemented | 24 / 24 |
| Phase 8.7 collectors registered | 24 / 24 |
| Phase 8.7 collectors executed in live run | 24 / 24 |
| Total registered Graph collectors executed | 44 / 44 |
| Artifacts generated | 44 / 44 |
| Findings generated | 44 / 44 |
| Recommendations generated | 44 / 44 |
| Assessment completion | 100% |

## Remaining Blockers

No runtime blocker remains for Phase 8.7.

Tenant/service blockers observed:

- Microsoft 365 usage reports returned no D30 activity rows for this tenant.
- Teams admin policy data is blocked by Microsoft `AADSTS500014` for the Teams admin resource in this tenant.
- A true Teams PowerShell collection path still requires delegated Teams admin authentication/session support if exact Teams PowerShell policy values are required instead of Graph admin limitation evidence.

