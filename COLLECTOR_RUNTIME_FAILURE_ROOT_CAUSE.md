# Collector Runtime Failure Root Cause

## Requested Parameter Trace

| Parameter | Assessment | Collector Selected | Runtime | Graph Endpoint | Token/API Response | Exception | Stdout | Stderr | Artifact Status | Finding Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `guest_users_count` | `successful_baseline` | `powershell.guest_users_count` | `powershell` | `/users?$select=id,displayName,userPrincipalName,mail,userType` | True | ``NULL`` | `NULL` | `NULL` | `collected` | `fail` |
| `guest_users_count` | `post_reset_completed` | `powershell.guest_users_count` | `powershell` | ``NULL`` | False | `NotImplementedError` | `NULL` | `NULL` | `failed` | `collection_error` |
| `guest_users_count` | `post_reset_latest_partial` | `powershell.guest_users_count` | ``NULL`` | ``NULL`` | False | ``NULL`` | `NULL` | `NULL` | ``NULL`` | ``NULL`` |
| `account_enabled` | `successful_baseline` | `powershell.account_enabled` | `powershell` | `/users?$select=id,displayName,userPrincipalName,accountEnabled,userType` | True | ``NULL`` | `NULL` | `NULL` | `collected` | `pass` |
| `account_enabled` | `post_reset_completed` | `powershell.account_enabled` | `powershell` | ``NULL`` | False | `NotImplementedError` | `NULL` | `NULL` | `failed` | `collection_error` |
| `account_enabled` | `post_reset_latest_partial` | `powershell.account_enabled` | ``NULL`` | ``NULL`` | False | ``NULL`` | `NULL` | `NULL` | ``NULL`` | ``NULL`` |
| `users_without_mfa` | `successful_baseline` | `powershell.users_without_mfa` | `powershell` | `/users + /users/{id}/authentication/methods` | True | ``NULL`` | `NULL` | `NULL` | `collected` | `fail` |
| `users_without_mfa` | `post_reset_completed` | `powershell.users_without_mfa` | `powershell` | ``NULL`` | False | `NotImplementedError` | `NULL` | `NULL` | `failed` | `collection_error` |
| `users_without_mfa` | `post_reset_latest_partial` | `powershell.users_without_mfa` | ``NULL`` | ``NULL`` | False | ``NULL`` | `NULL` | `NULL` | ``NULL`` | ``NULL`` |
| `authentication_methods_enabled` | `successful_baseline` | `powershell.authentication_methods_enabled` | `powershell` | `https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy` | True | ``NULL`` | `NULL` | `NULL` | `collected` | `pass` |
| `authentication_methods_enabled` | `post_reset_completed` | `powershell.authentication_methods_enabled` | `powershell` | ``NULL`` | False | `NotImplementedError` | `NULL` | `NULL` | `failed` | `collection_error` |
| `authentication_methods_enabled` | `post_reset_latest_partial` | `powershell.authentication_methods_enabled` | ``NULL`` | ``NULL`` | False | ``NULL`` | `NULL` | `NULL` | ``NULL`` | ``NULL`` |
| `secure_score_percentage` | `successful_baseline` | `portal.secure_score_percentage` | `powershell` | `/security/secureScores` | True | ``NULL`` | `NULL` | `NULL` | `collected` | `not_supported` |
| `secure_score_percentage` | `post_reset_completed` | `portal.secure_score_percentage` | `powershell` | ``NULL`` | False | `NotImplementedError` | `NULL` | `NULL` | `failed` | `collection_error` |
| `secure_score_percentage` | `post_reset_latest_partial` | `portal.secure_score_percentage` | ``NULL`` | ``NULL`` | False | ``NULL`` | `NULL` | `NULL` | ``NULL`` | ``NULL`` |
| `active_sites_count` | `successful_baseline` | `powershell.active_sites_count` | `powershell` | `/reports/getSharePointSiteUsageDetail(period='D30')` | True | ``NULL`` | `NULL` | `NULL` | `collected` | `fail` |
| `active_sites_count` | `post_reset_completed` | `powershell.active_sites_count` | `powershell` | ``NULL`` | False | `NotImplementedError` | `NULL` | `NULL` | `failed` | `collection_error` |
| `active_sites_count` | `post_reset_latest_partial` | `powershell.active_sites_count` | `powershell` | ``NULL`` | False | ``NULL`` | {"status":"success","collector":"powershell.active_sites_count","tenant_id":"fe4eff9a-f69c-48c0-921d-8006a6d5beb2","timestamp":"2026-06-03T21:13:43.3040587Z","findings":[{"parameter_key":"active_sites_count","status":"no... |  | `collected` | `warning` |
| `mailboxes_status_active_inactive` | `successful_baseline` | `powershell.mailboxes_status_active_inactive` | `powershell` | `/reports/getEmailActivityUserDetail(period='D30')` | True | ``NULL`` | `NULL` | `NULL` | `collected` | `pass` |
| `mailboxes_status_active_inactive` | `post_reset_completed` | `powershell.mailboxes_status_active_inactive` | `powershell` | ``NULL`` | False | `NotImplementedError` | `NULL` | `NULL` | `failed` | `collection_error` |
| `mailboxes_status_active_inactive` | `post_reset_latest_partial` | `powershell.mailboxes_status_active_inactive` | `powershell` | ``NULL`` | False | ``NULL`` | Error Acquiring Token: A window handle must be configured. See https://aka.ms/msal-net-wam#parent-window-handles  | [31;1mOperationStopped: [31;1mA window handle must be configured. See https://aka.ms/msal-net-wam#parent-window-handles[0m  | `failed` | `manual_validation` |

## Root Cause Decision

| Candidate | Result | Evidence |
| --- | --- | --- |
| runtime broken | Yes | Completed post-reset assessments produce 64 failed artifacts with empty `NotImplementedError` before stdout/stderr/CSV. Latest partial run shows runtime-launched PowerShell commands but with disabled or interactive auth failures. |
| tenant configuration missing | Partially | Tenant deployment/consent exists. SharePoint collector-specific `admin_url` is missing for SharePoint PowerShell collection. |
| consent missing | No | Post-reset tenant has `consent_status=connected`, service principal, encrypted secret, and app role assignment count 20. |
| deployment missing | No | Post-reset tenant has `deployment_status=ACTIVE`, application object/client IDs, service principal ID, and secret. |
| graph auth broken | No for app Graph collector | `global_administrator_accounts` succeeds with Graph after reset. The successful baseline used many Graph collectors; post-reset routing selects PowerShell for most named parameters instead. |
| powershell auth broken | Yes | Latest partial run: Exchange reports WAM window-handle failure; Teams reports unsupported auth mode `disabled`; SharePoint reports missing admin URL/manual validation. |

## Exact Technical Explanation

The post-reset assessment history for the same tenant was intentionally deleted, so there is no same-tenant successful assessment left to diff. The surviving successful baseline proves the engine can return PASS/FAIL when collectors use Graph-backed evidence paths. The post-reset completed run selected PowerShell for 64 parameters and failed before PowerShell output with `NotImplementedError`. The latest partial run then proves PowerShell execution can start, but its runtime auth/config is invalid: `interactive_powershell_disabled=true` sets workload auth modes to `disabled`, and Exchange/PnP/Teams cannot collect evidence non-interactively in that state.

Therefore the stopped-working behavior is caused by post-reset runtime/auth state and runtime selection, not by deleted tenant deployment or consent records.
