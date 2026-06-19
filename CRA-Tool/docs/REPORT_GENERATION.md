# Report Generation

## Main Report Flow

Report generation is handled by `CRA-Tool/app/services/reporting/cra_report_service.py`.

Primary flow:

```text
API route
  -> CRAReportService.generate_report_bundle()
  -> CRAReportService.build_report_data()
  -> report_builder.build_docx_report()
  -> generated DOCX file
  -> PDF generated from the DOCX path
```

Important files:

- `CRA-Tool/app/services/reporting/cra_report_service.py`
- `CRA-Tool/app/services/reporting/report_builder.py`
- `CRA-Tool/app/services/reporting/pdf_report_generator.py`
- `CRA-Tool/app/services/reporting/chart_generator.py`
- `CRA-Tool/app/services/reporting/report_customization.py`
- `CRA-Tool/reports/`

## API Routes

Report generation can be reached from assessment routes and report routes:

| Method | Route |
|---|---|
| POST | `/api/v1/assessments/{assessment_id}/generate-report` |
| GET | `/api/v1/assessments/{assessment_id}/report` |
| GET | `/api/v1/assessments/{assessment_id}/report/download` |
| GET | `/api/v1/reports/assessments/{assessment_id}` |
| POST | `/api/v1/reports/assessments/{assessment_id}/generate` |
| POST | `/api/v1/reports/assessments/{assessment_id}/customize` |

All listed report routes require authentication.

## Report Data Source

`build_report_data()` collects persisted data from the database and prepares a normalized dictionary for the DOCX builder.

The report uses:

- Assessment row from `assessments`
- Findings from `assessment_findings`
- Runtime evidence from `assessment_artifacts`
- Parameters from the registry and/or `assessment_parameters`
- Tenant metadata from `connected_tenants`
- Report metadata from `assessment_reports`

## Important `report_data` Keys

The report data object contains assessment, score, finding, chart, and observation fields. Important keys include:

- `assessment`
- `tenant`
- `tenant_name`
- `assessment_id`
- `generated_at`
- `parameters`
- `findings`
- `artifacts`
- `recommendations`
- `total_parameters`
- `passed_parameters`
- `failed_parameters`
- `readiness_score`
- `readiness_level`
- `license_counts`
- `user_info_fields`
- `user_info_total`
- `activity_counts`
- Service-level counts and summaries used by the dashboard/report sections

If a specific key is not present in `build_report_data()`, it should be treated as not found instead of assumed.

## Page Structure

The DOCX report is built in `report_builder.py`. The exact visual layout is controlled there, not by the frontend.

Observed report structure includes:

1. Cover and introductory pages.
2. Executive summary and readiness score sections.
3. Service and pillar summary sections.
4. Key Observations section.
5. Parameter/finding detail sections.
6. Recommendations and supporting details.

The Key Observations page path has been traced through:

```text
generate_report_bundle()
  -> build_report_data()
  -> build_docx_report()
  -> _add_page9_executive_charts()
```

## Parameter Section Contents

Parameter sections should be built from real finding and artifact data:

- Parameter name/key
- Service/category
- Pass/fail status
- Severity
- Expected value
- Actual value
- Raw evidence where available
- Recommendation text where available
- Collector/source details where available

Do not change stored findings, scores, or database values in the report builder. The report should render the persisted assessment state.

## Charts

Chart-related report code is in:

- `CRA-Tool/app/services/reporting/chart_generator.py`
- `CRA-Tool/app/services/reporting/report_builder.py`

The Key Observations section can include:

- Licenses assigned data
- User information details
- SharePoint account activity
- OneDrive account activity
- Teams usage
- Outlook usage

These charts should use real data from `report_data`, which is built from the database. If the database does not contain a value, the report should show the real missing/zero state instead of a mock value.

## DOCX And PDF Output

The service generates a DOCX report first. The PDF output is generated from the DOCX path in the current report service flow.

Generated report files are stored under `CRA-Tool/reports/` and linked to the assessment through report paths and/or `assessment_reports` rows.

## Debugging Report Generation

Useful routes:

- `GET /api/v1/assessment/report-debug/{assessment_id}`
- `GET /api/v1/report-debug/{assessment_id}`
- `GET /api/v1/assessments/{assessment_id}/report`
- `GET /api/v1/assessments/{assessment_id}/report/download`

Useful checks:

- Confirm the assessment exists and is not deleted.
- Confirm findings exist for the assessment.
- Confirm artifacts exist for the assessment.
- Confirm `report_path` or `assessment_reports.storage_path` points to an existing file.
- Confirm DOCX content is produced before checking PDF conversion.
- For chart/image issues, inspect the generated DOCX ZIP media files and `word/document.xml`.
