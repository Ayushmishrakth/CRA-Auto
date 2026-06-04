# Default Value Root Cause

## Search Scope

Searched backend `app` and frontend `src` for fallback/default patterns including `or 0`, `or {}`, `or []`, `defaultdict`, `fallback`, `empty evidence`, and `not collected`.

## Relevant Findings

| File | Lines | Data-flow Impact |
| --- | --- | --- |
| `CRA-Tool/app/services/runtime_assessment_service.py` | 261-303 | Builds reconciled fallback evidence when collector_result is missing/failed; actual_value becomes "Collector did not return evidence" for collection_error. |
| `CRA-Tool/app/services/runtime_assessment_service.py` | 432-492 | Persists artifact payload/failure_details even when collector_result is null; failed PowerShell artifacts therefore store failure metadata, not tenant evidence. |
| `CRA-Tool/app/services/assessment_service.py` | 413-454 | Evidence API reads empty payload/raw_evidence defaults for failed artifacts and exposes failure reason. |
| `CRA-Tool/app/services/assessment_service.py` | 519-553 | Evidence API falls back to finding raw_value when artifact actual/raw evidence is absent. |
| `CRA-Tool/app/services/findings/finding_engine.py` | 18-32 | Generic finding engine can evaluate evidence or [] and store empty evidence; not the source of latest runtime collector failures. |
| `CRA-frontend/src/pages/AssessmentDetailPage.jsx` | 157-176 | Frontend falls back to []/{} if evidence API data is absent, affecting display only after API failure. |
| `CRA-frontend/src/pages/AssessmentEvidencePage.jsx` | 81-87 | Evidence page falls back to []/{} if payload is absent, affecting display only after API failure. |
| `CRA-frontend/src/utils/assessmentFormatters.js` | 57-76 | Finding normalization stringifies raw evidence fallback {} for missing raw values. |

## Runtime Conclusion

For the latest assessment, default/fallback values are not hiding successful tenant data for 64 parameters. Those parameters have no PowerShell stdout, no CSV file, no raw response, and failed artifact payloads with `exception_type=NotImplementedError`. The fallback text appears after collection failure so the UI/API can display a row, not because parser output overwrote real tenant data.
