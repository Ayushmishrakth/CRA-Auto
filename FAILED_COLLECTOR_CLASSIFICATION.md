# Failed Collector Classification

Generated: 2026-06-03 21:01:19

## Summary

| Classification | Count |
| --- | --- |
| MANUAL_VALIDATION_REQUIRED | 12 |

| Parameter | Classification | Reason | Action Taken |
| --- | --- | --- | --- |
| audit_log_retention_duration | MANUAL_VALIDATION_REQUIRED | Delegated PowerShell session / WAM window handle; use device/auth context or manual validation. | Runtime now maps this dependency to MANUAL_VALIDATION instead of FAILED_COLLECTOR. |
| auto_expiration_policy_for_inactive_m365_groups | MANUAL_VALIDATION_REQUIRED | Collector exceeded configured timeout; retest classified as manual validation instead of failed collector. | Runtime now maps this dependency to MANUAL_VALIDATION instead of FAILED_COLLECTOR. |
| customer_lockbox | MANUAL_VALIDATION_REQUIRED | Delegated PowerShell session / WAM window handle; use device/auth context or manual validation. | Runtime now maps this dependency to MANUAL_VALIDATION instead of FAILED_COLLECTOR. |
| days_to_retain_a_deleted_user_s_onedrive | MANUAL_VALIDATION_REQUIRED | Collector exceeded configured timeout; retest classified as manual validation instead of failed collector. | Runtime now maps this dependency to MANUAL_VALIDATION instead of FAILED_COLLECTOR. |
| expiration_policy_for_anyone_links | MANUAL_VALIDATION_REQUIRED | SharePoint tenant admin URL required, e.g. https://<tenant>-admin.sharepoint.com. | SharePoint script now emits not_collected CSV evidence when admin_url is missing; finding becomes MANUAL_VALIDATION. |
| external_storage_providers_in_owa | MANUAL_VALIDATION_REQUIRED | Delegated PowerShell session / WAM window handle; use device/auth context or manual validation. | Runtime now maps this dependency to MANUAL_VALIDATION instead of FAILED_COLLECTOR. |
| full_calendar_schedules_able_to_be_shared_externally | MANUAL_VALIDATION_REQUIRED | Delegated PowerShell session / WAM window handle; use device/auth context or manual validation. | Runtime now maps this dependency to MANUAL_VALIDATION instead of FAILED_COLLECTOR. |
| inactive_site_policies | MANUAL_VALIDATION_REQUIRED | SharePoint tenant admin URL required, e.g. https://<tenant>-admin.sharepoint.com. | SharePoint script now emits not_collected CSV evidence when admin_url is missing; finding becomes MANUAL_VALIDATION. |
| permission_setting_for_anyone_links | MANUAL_VALIDATION_REQUIRED | SharePoint tenant admin URL required, e.g. https://<tenant>-admin.sharepoint.com. | SharePoint script now emits not_collected CSV evidence when admin_url is missing; finding becomes MANUAL_VALIDATION. |
| sharepoint_and_onedrive_guest_access_expiry | MANUAL_VALIDATION_REQUIRED | Collector exceeded configured timeout; retest classified as manual validation instead of failed collector. | Runtime now maps this dependency to MANUAL_VALIDATION instead of FAILED_COLLECTOR. |
| site_ownership_policies | MANUAL_VALIDATION_REQUIRED | SharePoint tenant admin URL required, e.g. https://<tenant>-admin.sharepoint.com. | SharePoint script now emits not_collected CSV evidence when admin_url is missing; finding becomes MANUAL_VALIDATION. |
| teams_with_external_guest_as_owner | MANUAL_VALIDATION_REQUIRED | Collector exceeded configured timeout; retest classified as manual validation instead of failed collector. | Runtime now maps this dependency to MANUAL_VALIDATION instead of FAILED_COLLECTOR. |
