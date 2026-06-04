# Entra ID Graph Collector Implementation Report

Generated: 2026-06-01

## Scope

Phase 8.6 implemented the Entra ID Graph collector batch using `PARAMETER_DATA_COLLECTION_MAP.md` as the source of truth for endpoints, evidence, and pass/fail criteria.

No mock collectors or placeholder responses were added. Collectors call Microsoft Graph with the connected tenant app credentials and persist raw/normalized evidence into `assessment_artifacts`.

## Files Changed

| Area | File | Change |
|---|---|---|
| Graph collectors | `CRA-Tool/app/services/graph_cra_collector_service.py` | Added/registered Entra ID Graph collectors, normalizers, evaluators, evidence payloads, and tenant Graph edge-case handling. |
| Runtime orchestration | `CRA-Tool/app/services/runtime_assessment_service.py` | Removed the hard-coded first-operational collector subset. Runtime now executes registry parameters that have registered Graph collectors. |
| Dashboard service | `CRA-Tool/app/services/assessment_service.py` | Added live readiness breakdown for Identity, Security, and Licensing from persisted findings. |
| Backend API | `CRA-Tool/app/api/v1/assessments.py` | Added `GET /api/v1/assessments/{assessment_id}/readiness`. |
| Frontend API | `CRA-frontend/src/api/assessmentApi.js` | Added `getAssessmentReadiness(assessmentId)`. |

## Parameters Implemented

| # | Parameter Key | Collector Registered | Evidence Persisted | Finding | Score | Recommendation | Report |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `global_administrator_accounts` | Yes | Yes | Yes | Yes | Yes | Yes |
| 2 | `guest_users_count` | Yes | Yes | Yes | Yes | Yes | Yes |
| 3 | `user_information` | Yes | Yes | Yes | Yes | Yes | Yes |
| 4 | `guest_invite_settings` | Yes | Yes | Yes | Yes | Yes | Yes |
| 5 | `entra_third_party_app_integrations` | Yes | Yes | Yes | Yes | Yes | Yes |
| 6 | `tenant_collaboration_invitations` | Yes | Yes | Yes | Yes | Yes | Yes |
| 7 | `authentication_methods_enabled` | Yes | Yes | Yes | Yes | Yes | Yes |
| 8 | `admin_consent_workflow` | Yes | Yes | Yes | Yes | Yes | Yes |
| 9 | `cap_policies_for_risky_sign_ins` | Yes | Yes | Yes | Yes | Yes | Yes |
| 10 | `users_without_mfa` | Yes | Yes | Yes | Yes | Yes | Yes |
| 11 | `unused_licenses_count` | Yes | Yes | Yes | Yes | Yes | Yes |
| 12 | `user_consent_for_applications` | Yes | Yes | Yes | Yes | Yes | Yes |
| 13 | `non_admin_users_can_register_applications` | Yes | Yes | Yes | Yes | Yes | Yes |
| 14 | `restricted_access_to_microsoft_entra_admin_centre` | Yes | Yes | Yes | Yes | Yes | Yes |
| 15 | `self_service_password_reset_authentication_method` | Yes | Yes | Yes | Yes | Yes | Yes |
| 16 | `account_enabled` | Yes | Yes | Yes | Yes | Yes | Yes |
| 17 | `assigned_license` | Yes | Yes | Yes | Yes | Yes | Yes |
| 18 | `conditional_access_policies_exclusion` | Yes | Yes | Yes | Yes | Yes | Yes |
| 19 | `entra_tenant_creation_by_non_admin` | Yes | Yes | Yes | Yes | Yes | Yes |
| 20 | `devices_without_compliance_policies` | Yes | Yes | Yes | Yes | Yes | Yes |

## Runtime Registration

Collector execution is now registry-driven:

`Assessment registry -> GRAPH_COLLECTORS -> collector/evaluator -> assessment_artifacts -> assessment_findings -> scoring -> recommendations -> report bundle -> dashboards`

The previous hard-coded operational subset was removed from `runtime_assessment_service.py`. Any active registry parameter with a matching `GRAPH_COLLECTORS` key now executes in the runtime.

## Live Validation

Validation tenant: `fe4eff9a-f69c-48c0-921d-8006a6d5beb2`

Fresh assessment:

| Field | Value |
|---|---|
| Assessment ID | `52b75cc1-3dbd-4f4f-ab63-321e9b6cbe6b` |
| Job ID | `62e78f06-c657-4681-9be1-92e68b5050c5` |
| Assessment status | `completed` |
| Job status | `completed` |
| Progress | `100.0` |
| Collector total | `20` |
| Collector collected | `20` |
| Collector incomplete | `0` |
| Graph calls | `38` |
| Artifacts | `20` |
| Findings | `20` |
| Recommendations | `20` |
| Reports | `2` |

Scores generated:

| Score | Value |
|---|---:|
| Overall | 59.0 |
| Identity | 0.0 |
| Security | 100.0 |
| Compliance | 100.0 |
| Collaboration | 100.0 |
| Licensing | 99.0 |

Finding status counts:

| Status | Count |
|---|---:|
| Pass | 7 |
| Fail | 13 |

Finding severity counts:

| Severity | Count |
|---|---:|
| Critical | 1 |
| High | 6 |
| Medium | 1 |
| Low | 1 |
| Info | 11 |

## Validation Result Matrix

| Parameter Key | Category | Result | Severity | Last Result |
|---|---|---|---|---|
| `account_enabled` | Security | pass | info | 14 enabled account(s) detected out of 14 total account(s) (100.0%) |
| `admin_consent_workflow` | Best Practice | fail | high | Admin consent workflow is not configured |
| `assigned_license` | Governance | fail | info | 0.0% of users have a recognized Copilot prerequisite license |
| `authentication_methods_enabled` | Security | pass | info | 4 authentication method(s) are enabled |
| `cap_policies_for_risky_sign_ins` | Security | fail | high | 0 enabled Conditional Access policy/policies target risky sign-ins |
| `conditional_access_policies_exclusion` | Security | pass | info | 0 Conditional Access policy/policies have user, group, or role exclusions |
| `devices_without_compliance_policies` | Security | fail | info | Request not applicable to target tenant. |
| `entra_tenant_creation_by_non_admin` | Best Practice | fail | critical | Non-admin tenant creation allowed: True |
| `entra_third_party_app_integrations` | Governance | fail | high | Users allowed to register applications: True |
| `global_administrator_accounts` | Best Practice | pass | info | 2 Global Administrator account(s) found |
| `guest_invite_settings` | Security | fail | medium | Guest invite setting is everyone |
| `guest_users_count` | Governance | pass | info | 0 guest user(s) detected out of 14 total user(s) (0.0%) |
| `non_admin_users_can_register_applications` | Security | fail | info | Non-admin application registration allowed: True |
| `restricted_access_to_microsoft_entra_admin_centre` | Best Practice | fail | info | Non-admin users allowed to read other users/admin center data: True |
| `self_service_password_reset_authentication_method` | Security | pass | info | 4 SSPR/authentication method(s) are enabled |
| `tenant_collaboration_invitations` | Governance | fail | high | Tenant collaboration appears open to any domain |
| `unused_licenses_count` | Entra ID | pass | info | 0 unused license(s) found across 0 SKU(s) |
| `user_consent_for_applications` | Best Practice | fail | high | Users can consent for applications |
| `user_information` | Best Practice | fail | low | 2 user account(s) have incomplete required profile information |
| `users_without_mfa` | Security | fail | high | 2 user(s) do not have a non-password MFA authentication method registered |

## Graph Endpoint Notes

`authentication_methods_enabled` and `self_service_password_reset_authentication_method` now use:

`https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy`

Live diagnostic showed the previous child endpoint returned:

`400 Resource not found for segment 'authenticationMethodsPolicy/authenticationMethodConfigurations'.`

The policy root endpoint returned `200` and included `authenticationMethodConfigurations`, so the collector now reads the real tenant data from that response.

`self_service_password_reset_authentication_method` also calls:

`/reports/authenticationMethods/userRegistrationDetails`

For this tenant, Microsoft Graph returned:

`403 Authentication_RequestFromNonPremiumTenantOrB2CTenant`

The collector now preserves that Graph error as evidence and continues with the authentication policy data instead of failing the whole assessment.

`devices_without_compliance_policies` calls:

`/deviceManagement/managedDevices`

For this tenant, Microsoft Graph returned:

`400 Request not applicable to target tenant.`

The collector now records that Graph response as evidence and creates a failed finding because managed device compliance data is not available for the tenant.

## Dashboard Integration

Added:

`GET /api/v1/assessments/{assessment_id}/readiness`

The endpoint returns live assessment-derived readiness breakdowns for:

- `identity_readiness`
- `security_readiness`
- `licensing_readiness`

The frontend API helper is:

`getAssessmentReadiness(assessmentId)`

No mock dashboard values were introduced.

## Verification

Backend syntax check:

`.\venv\Scripts\python.exe -m py_compile app\services\graph_cra_collector_service.py app\services\runtime_assessment_service.py app\services\assessment_service.py app\api\v1\assessments.py`

Result: passed.

Frontend build:

`npm run build`

Result: passed. Vite reported the existing chunk-size warning for the main bundle.

Live assessment:

Result: completed with 20/20 collectors executed, 20 artifacts, 20 findings, 20 recommendations, scores, and report rows.

## Coverage

| Coverage Area | Result |
|---|---:|
| Requested parameters implemented | 20 / 20 |
| Collectors registered | 20 / 20 |
| Collectors executed in live run | 20 / 20 |
| Artifacts generated | 20 / 20 |
| Findings generated | 20 / 20 |
| Recommendations generated | 20 / 20 |
| Report integration | 20 / 20 findings available to report bundle |
| Runtime coverage | 100% |

## Remaining Blockers

No code blocker remains for Phase 8.6 collector execution.

Tenant/data blockers observed in validation:

- The tenant has no returned subscribed SKU records, so license-based pass/fail results show 0 eligible users.
- Authentication registration report data requires a premium-capable tenant/license; Graph returned `Authentication_RequestFromNonPremiumTenantOrB2CTenant`.
- Intune managed device data is not applicable to this tenant; Graph returned `Request not applicable to target tenant`.
- Several failed findings are real tenant posture results, not collector failures.

