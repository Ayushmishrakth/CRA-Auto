# Implementation Gap Audit

Generated: `2026-06-04T00:42:10`

## Summary

- Approved parameters: `65`
- Missing manifest entries: `0`
- Missing scripts: `0`
- Missing expected output contracts: `0`
- `NotImplementedError` in backend app: `0`
- Collector mock/fake response markers in production app: `0`

## Implementation Markers

| File | Line | Marker | Text | Disposition |
| --- | --- | --- | --- | --- |
| app/api/v1/websocket.py | 78 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/api/v1/websocket.py | 124 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/db/models/base_model.py | 18 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/services/event_bus.py | 130 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/services/registry_service.py | 19 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/services/csv_ingestion/csv_ingestion_service.py | 11 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/services/domain_runtimes/base.py | 11 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/services/findings/rule_engine.py | 7 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/services/graph/graph_auth_service.py | 5 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |
| app/services/powershell/powershell_result_parser.py | 16 | pass | pass | REVIEWED_NON_COLLECTOR_OR_TEST_HELPER |

## Missing Manifest/Script/Output Contracts

| Type | Parameter | Detail |
| --- | --- | --- |
| CLEAR | N/A | All approved parameters have manifest, script, and output contract. |