# First Operational CRA Collector Implementation Plan

Date: 2026-05-31

## Source Of Truth

This implementation follows `COLLECTOR_AUDIT.md`.

The easiest collector to complete first is:

```text
global_administrator_accounts
```

Reasons:

- Highest priority in the requested order.
- Existing deployment already requests required Graph permissions.
- Evidence can be collected with Microsoft Graph application permissions.
- Evaluation rule is deterministic: Global Administrator count must be between 2 and 5 inclusive.

## Implemented Slice

### Collector

Added:

```text
app/services/graph_cra_collector_service.py
```

Collector:

```text
collect_global_administrator_accounts()
```

Authentication:

```text
client_credentials
tenant.app_client_id
tenant.encrypted_client_secret
scope=https://graph.microsoft.com/.default
```

Graph calls:

```text
GET /directoryRoles?$filter=displayName eq 'Global Administrator'
GET /directoryRoles/{id}/members?$select=id,displayName,userPrincipalName,mail
```

Required permissions:

```text
Directory.Read.All
RoleManagement.Read.Directory
```

These are already included in `REQUIRED_APPLICATION_PERMISSIONS`.

### Evidence Shape

The collector returns:

```json
{
  "parameter_key": "global_administrator_accounts",
  "tenant_id": "...",
  "role": {},
  "admin_count": 0,
  "members": [],
  "criteria": {
    "pass": "Global Administrator count is between 2 and 5 inclusive",
    "fail": "Global Administrator count is less than 2 or greater than 5"
  },
  "raw_response": {
    "directoryRoles": {},
    "members": {}
  }
}
```

### Finding

Runtime now persists an `AssessmentFinding` for this parameter when Graph evidence is returned.

Status logic:

```text
PASS: 2 <= global_admin_count <= 5
FAIL: global_admin_count < 2 or global_admin_count > 5
```

### Score

Runtime now reaches `apply_scores()` when this first collector succeeds.

Logged:

```text
SCORE_CREATED
```

### Recommendation

Recommendation persistence now creates a recommendation record for every finding:

- Failed finding: remediation recommendation.
- Passing finding: maintain/monitor recommendation.

This guarantees the first operational parameter produces a recommendation record end-to-end.

### Debug Endpoint

Added:

```text
GET /api/v1/assessment/debug/latest
```

Response:

```json
{
  "collectors_run": 1,
  "findings_created": 1,
  "scores_created": 1,
  "graph_calls": 2,
  "failures": []
}
```

Actual values depend on whether Graph role resolution finds the active Global Administrator role.

## Runtime Change

`runtime_assessment_service` now runs only the first operational parameter:

```text
global_administrator_accounts
```

The remaining 64 parameters are intentionally not executed in this slice. This prevents unfinished collectors from marking the assessment incomplete and blocking scoring/report flow.

## Logging Added

```text
COLLECTOR_STARTED
GRAPH_REQUEST
GRAPH_RESPONSE
FINDING_CREATED
SCORE_CREATED
```

## Verification

Automated tests:

```text
tests/test_phase7_runtime.py
6 passed
```

Full backend suite:

```text
88 passed, 3 xfailed
```

## End-To-End Flow Now Available

```text
Start Assessment
  -> run one operational collector
  -> obtain Graph app token
  -> call Graph directory role endpoints
  -> build evidence object
  -> persist finding
  -> create score
  -> create recommendation
  -> complete assessment
```

## Remaining Work After This Slice

Implement the remaining priority collectors one at a time:

1. `guest_users_count`
2. `users_without_mfa`
3. `active_users_on_sharepoint`
4. `orphan_teams`

Each should follow the same contract:

```text
Graph token
Graph request
Graph response
Evidence object
Finding
Score
Recommendation
Debug counters
```
