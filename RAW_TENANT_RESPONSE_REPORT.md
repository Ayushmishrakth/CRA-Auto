# Raw Tenant Response Report

This report documents the raw Microsoft responses, endpoints, and commands for all 65 parameters.

### Account enabled
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/account_enabled`
- **PowerShell Command**: `Get-Accountenabled`
- **Raw Response**:
```json
{"enabled_count": 14, "enabled_percent": 100.0, "total_users": 14}
```
- **Parsed Value**: `{"enabled_count": 14, "enabled_percent": 100.0, "total_users": 14}`
- **Stored Evidence**:
```json
{"enabled_count": 14, "enabled_percent": 100.0, "total_users": 14}
```

---

### Admin Consent Workflow
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/admin_consent_workflow`
- **PowerShell Command**: `Get-AdminConsentWorkflow`
- **Raw Response**:
```json
{"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#policies/adminConsentRequestPolicy/$entity", "isEnabled": false, "notifyReviewers": false, "remindersEnabled": false, "requestDurationInDays": 0, "reviewe...
```
- **Parsed Value**: `{"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#policies/adminConsentRequestPolicy/$entity", "isEnabled": false, "notifyReviewers": false, "remindersEnabled": false, "requestDurationInDays": 0, "reviewe...`
- **Stored Evidence**:
```json
{"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#policies/adminConsentRequestPolicy/$entity", "isEnabled": false, "notifyReviewers": false, "remindersEnabled": false, "requestDurationInDays": 0, "reviewe...
```

---

### Authentication methods enabled
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/authentication_methods_enabled`
- **PowerShell Command**: `Get-Authenticationmethodsenabled`
- **Raw Response**:
```json
{"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"method": "TemporaryAccessPass", "state": "enabled"}, {"method": "SoftwareOath", "state": "enabled"}, {"method": "Email", "...
```
- **Parsed Value**: `{"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"method": "TemporaryAccessPass", "state": "enabled"}, {"method": "SoftwareOath", "state": "enabled"}, {"method": "Email", "...`
- **Stored Evidence**:
```json
{"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"method": "TemporaryAccessPass", "state": "enabled"}, {"method": "SoftwareOath", "state": "enabled"}, {"method": "Email", "...
```

---

### Auto-expiration policy for M365 Groups
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/auto_expiration_policy_for_inactive_m365_groups`
- **PowerShell Command**: `Get-Auto-expirationpolicyforM365Groups`
- **Raw Response**:
```json
{"active_policy_count": 0, "policy_count": 0}
```
- **Parsed Value**: `{"active_policy_count": 0, "policy_count": 0}`
- **Stored Evidence**:
```json
{"active_policy_count": 0, "policy_count": 0}
```

---

### CAP policies for risky sign-ins
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/cap_policies_for_risky_sign_ins`
- **PowerShell Command**: `Get-CAPpoliciesforriskysign-ins`
- **Raw Response**:
```json
{"policies": [], "risky_policy_count": 0}
```
- **Parsed Value**: `{"policies": [], "risky_policy_count": 0}`
- **Stored Evidence**:
```json
{"policies": [], "risky_policy_count": 0}
```

---

### Conditional Access Policies (Exclusion)
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/conditional_access_policies_exclusion`
- **PowerShell Command**: `Get-ConditionalAccessPolicies(Exclusion)`
- **Raw Response**:
```json
{"exclusions": [], "policies_with_exclusions": 0}
```
- **Parsed Value**: `{"exclusions": [], "policies_with_exclusions": 0}`
- **Stored Evidence**:
```json
{"exclusions": [], "policies_with_exclusions": 0}
```

---

### Custom Banned Password List
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/custom_banned_password_list`
- **PowerShell Command**: `Get-CustomBannedPasswordList`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["Policy.Read.All"], "required_role": "Authentication Policy Administrator or Global Administrator", "required_service": "Entra ID Password Protectio...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["Policy.Read.All"], "required_role": "Authentication Policy Administrator or Global Administrator", "required_service": "Entra ID Password Protectio...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["Policy.Read.All"], "required_role": "Authentication Policy Administrator or Global Administrator", "required_service": "Entra ID Password Protectio...
```

---

### Devices without compliance policies
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/devices_without_compliance_policies`
- **PowerShell Command**: `Get-Deviceswithoutcompliancepolicies`
- **Raw Response**:
```json
{"error": {"code": "BadRequest", "innerError": {"client-request-id": "2e48ec4c-62bc-49e6-a108-26990c8daddd", "date": "2026-06-03T18:18:40", "request-id": "2e48ec4c-62bc-49e6-a108-26990c8daddd"}, "message": "Request no...
```
- **Parsed Value**: `{"error": {"code": "BadRequest", "innerError": {"client-request-id": "2e48ec4c-62bc-49e6-a108-26990c8daddd", "date": "2026-06-03T18:18:40", "request-id": "2e48ec4c-62bc-49e6-a108-26990c8daddd"}, "message": "Request no...`
- **Stored Evidence**:
```json
{"error": {"code": "BadRequest", "innerError": {"client-request-id": "2e48ec4c-62bc-49e6-a108-26990c8daddd", "date": "2026-06-03T18:18:40", "request-id": "2e48ec4c-62bc-49e6-a108-26990c8daddd"}, "message": "Request no...
```

---

### Emergency Access Accounts
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/emergency_access_accounts`
- **PowerShell Command**: `Get-EmergencyAccessAccounts`
- **Raw Response**:
```json
{"emergency_access_accounts": 0, "global_admin_members": 2}
```
- **Parsed Value**: `{"emergency_access_accounts": 0, "global_admin_members": 2}`
- **Stored Evidence**:
```json
{"emergency_access_accounts": 0, "global_admin_members": 2}
```

---

### Entra - Tenant Creation By Non-Admin
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/entra_tenant_creation_by_non_admin`
- **PowerShell Command**: `Get-Entra-TenantCreationByNon-Admin`
- **Raw Response**:
```json
True
```
- **Parsed Value**: `True`
- **Stored Evidence**:
```json
True
```

---

### Entra - Third Party App Integrations
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/entra_third_party_app_integrations`
- **PowerShell Command**: `Get-Entra-ThirdPartyAppIntegrations`
- **Raw Response**:
```json
True
```
- **Parsed Value**: `True`
- **Stored Evidence**:
```json
True
```

---

### Global Administrator Accounts
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/global_administrator_accounts`
- **PowerShell Command**: `Get-GlobalAdministratorAccounts`
- **Raw Response**:
```json
2
```
- **Parsed Value**: `2`
- **Stored Evidence**:
```json
2
```

---

### Guest Invite Settings
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/guest_invite_settings`
- **PowerShell Command**: `Get-GuestInviteSettings`
- **Raw Response**:
```json
everyone
```
- **Parsed Value**: `everyone`
- **Stored Evidence**:
```json
everyone
```

---

### Guest users count
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/guest_users_count`
- **PowerShell Command**: `Get-Guestuserscount`
- **Raw Response**:
```json
{"guest_count": 0, "guest_ratio_percent": 0.0, "total_users": 14}
```
- **Parsed Value**: `{"guest_count": 0, "guest_ratio_percent": 0.0, "total_users": 14}`
- **Stored Evidence**:
```json
{"guest_count": 0, "guest_ratio_percent": 0.0, "total_users": 14}
```

---

### Restricted Access To Microsoft Entra Admin Centre
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/restricted_access_to_microsoft_entra_admin_centre`
- **PowerShell Command**: `Get-RestrictedAccessToMicrosoftEntraAdminCentre`
- **Raw Response**:
```json
True
```
- **Parsed Value**: `True`
- **Stored Evidence**:
```json
True
```

---

### Self-Service Password Reset Authentication Method
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/self_service_password_reset_authentication_method`
- **PowerShell Command**: `Get-Self-ServicePasswordResetAuthenticationMethod`
- **Raw Response**:
```json
{"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"method": "TemporaryAccessPass", "state": "enabled"}, {"method": "SoftwareOath", "state": "enabled"}, {"method": "Email", "...
```
- **Parsed Value**: `{"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"method": "TemporaryAccessPass", "state": "enabled"}, {"method": "SoftwareOath", "state": "enabled"}, {"method": "Email", "...`
- **Stored Evidence**:
```json
{"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"method": "TemporaryAccessPass", "state": "enabled"}, {"method": "SoftwareOath", "state": "enabled"}, {"method": "Email", "...
```

---

### Tenant Collaboration Invitations
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/tenant_collaboration_invitations`
- **PowerShell Command**: `Get-TenantCollaborationInvitations`
- **Raw Response**:
```json
{"default": {}, "partner_count": 0}
```
- **Parsed Value**: `{"default": {}, "partner_count": 0}`
- **Stored Evidence**:
```json
{"default": {}, "partner_count": 0}
```

---

### User Consent For Applications
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/user_consent_for_applications`
- **PowerShell Command**: `Get-UserConsentForApplications`
- **Raw Response**:
```json
{"permissionGrantPoliciesAssigned": ["ManagePermissionGrantsForSelf.microsoft-user-default-recommended", "ManagePermissionGrantsForSelf.microsoft-user-default-allow-consent-apps", "ManagePermissionGrantsForOwnedResour...
```
- **Parsed Value**: `{"permissionGrantPoliciesAssigned": ["ManagePermissionGrantsForSelf.microsoft-user-default-recommended", "ManagePermissionGrantsForSelf.microsoft-user-default-allow-consent-apps", "ManagePermissionGrantsForOwnedResour...`
- **Stored Evidence**:
```json
{"permissionGrantPoliciesAssigned": ["ManagePermissionGrantsForSelf.microsoft-user-default-recommended", "ManagePermissionGrantsForSelf.microsoft-user-default-allow-consent-apps", "ManagePermissionGrantsForOwnedResour...
```

---

### User Information
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/user_information`
- **PowerShell Command**: `Get-UserInformation`
- **Raw Response**:
```json
{"complete_users": 12, "incomplete_users": 2, "total_users": 14}
```
- **Parsed Value**: `{"complete_users": 12, "incomplete_users": 2, "total_users": 14}`
- **Stored Evidence**:
```json
{"complete_users": 12, "incomplete_users": 2, "total_users": 14}
```

---

### Users without MFA
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/users_without_mfa`
- **PowerShell Command**: `Get-UserswithoutMFA`
- **Raw Response**:
```json
{"total_users": 14, "users_without_mfa": 2}
```
- **Parsed Value**: `{"total_users": 14, "users_without_mfa": 2}`
- **Stored Evidence**:
```json
{"total_users": 14, "users_without_mfa": 2}
```

---

### External Storage Providers In OWA
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/external_storage_providers_in_owa`
- **PowerShell Command**: `Get-ExternalStorageProvidersInOWA`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell. The app-only Graph runtime cannot read OWA mailbox policy settings directly, so this collector mu...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell. The app-only Graph runtime cannot read OWA mailbox policy settings directly, so this collector mu...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell. The app-only Graph runtime cannot read OWA mailbox policy settings directly, so this collector mu...
```

---

### Full Calendar Schedules Able To Be Shared Externally
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/full_calendar_schedules_able_to_be_shared_externally`
- **PowerShell Command**: `Get-FullCalendarSchedulesAbleToBeSharedExternally`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell sharing policies. The app-only Graph runtime cannot read this tenant sharing policy directly.", "r...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell sharing policies. The app-only Graph runtime cannot read this tenant sharing policy directly.", "r...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell sharing policies. The app-only Graph runtime cannot read this tenant sharing policy directly.", "r...
```

---

### Mailbox Storage usage
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/mailbox_storage_usage`
- **PowerShell Command**: `Get-MailboxStorageusage`
- **Raw Response**:
```json
{"mailbox_count": 0, "over_threshold": 0, "storage_usage_ratio": 0.0}
```
- **Parsed Value**: `{"mailbox_count": 0, "over_threshold": 0, "storage_usage_ratio": 0.0}`
- **Stored Evidence**:
```json
{"mailbox_count": 0, "over_threshold": 0, "storage_usage_ratio": 0.0}
```

---

### Mailboxes Status (Active/Inactive)
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/mailboxes_status_active_inactive`
- **PowerShell Command**: `Get-MailboxesStatus(Active/Inactive)`
- **Raw Response**:
```json
{"active_mailboxes": 0, "active_ratio": 0.0, "inactive_mailboxes": 0}
```
- **Parsed Value**: `{"active_mailboxes": 0, "active_ratio": 0.0, "inactive_mailboxes": 0}`
- **Stored Evidence**:
```json
{"active_mailboxes": 0, "active_ratio": 0.0, "inactive_mailboxes": 0}
```

---

### Number of emails read/received
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/number_of_emails_read_received`
- **PowerShell Command**: `Get-Numberofemailsread/received`
- **Raw Response**:
```json
{"engaged_users": 0, "read_ratio": 0.0, "total_users": 0}
```
- **Parsed Value**: `{"engaged_users": 0, "read_ratio": 0.0, "total_users": 0}`
- **Stored Evidence**:
```json
{"engaged_users": 0, "read_ratio": 0.0, "total_users": 0}
```

---

### Number of emails sent
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/number_of_emails_sent`
- **PowerShell Command**: `Get-Numberofemailssent`
- **Raw Response**:
```json
{"average_sent_per_user": 0.0, "total_users": 0}
```
- **Parsed Value**: `{"average_sent_per_user": 0.0, "total_users": 0}`
- **Stored Evidence**:
```json
{"average_sent_per_user": 0.0, "total_users": 0}
```

---

### Customer Lockbox
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/customer_lockbox`
- **PowerShell Command**: `Get-CustomerLockbox`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell organization configuration. The app-only Graph runtime cannot read CustomerLockBoxEnabled directly...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell organization configuration. The app-only Graph runtime cannot read CustomerLockBoxEnabled directly...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "This control is fully automatable with Exchange Online PowerShell organization configuration. The app-only Graph runtime cannot read CustomerLockBoxEnabled directly...
```

---

### Audit Logs enabled
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/audit_logs_enabled`
- **PowerShell Command**: `Get-AuditLogsenabled`
- **Raw Response**:
```json
{"audit_logs_queryable": true, "sample_count": 1}
```
- **Parsed Value**: `{"audit_logs_queryable": true, "sample_count": 1}`
- **Stored Evidence**:
```json
{"audit_logs_queryable": true, "sample_count": 1}
```

---

### Audit log retention duration
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/audit_log_retention_duration`
- **PowerShell Command**: `Get-Auditlogretentionduration`
- **Raw Response**:
```json
{"audit_log_sample_count": 166, "retention_policy_source": "Purview PowerShell required for exact duration"}
```
- **Parsed Value**: `{"audit_log_sample_count": 166, "retention_policy_source": "Purview PowerShell required for exact duration"}`
- **Stored Evidence**:
```json
{"audit_log_sample_count": 166, "retention_policy_source": "Purview PowerShell required for exact duration"}
```

---

### Compliance Score overview
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/compliance_score_overview`
- **PowerShell Command**: `Get-ComplianceScoreoverview`
- **Raw Response**:
```json
{"collection_status": "MANUAL_VALIDATION_REQUIRED", "expected_evidence": "Compliance Manager score overview export or screenshot showing current score and assessment date.", "portal_location": "Microsoft Purview porta...
```
- **Parsed Value**: `{"collection_status": "MANUAL_VALIDATION_REQUIRED", "expected_evidence": "Compliance Manager score overview export or screenshot showing current score and assessment date.", "portal_location": "Microsoft Purview porta...`
- **Stored Evidence**:
```json
{"collection_status": "MANUAL_VALIDATION_REQUIRED", "expected_evidence": "Compliance Manager score overview export or screenshot showing current score and assessment date.", "portal_location": "Microsoft Purview porta...
```

---

### DLP rules configured
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/dlp_rules_configured`
- **PowerShell Command**: `Get-DLPrulesconfigured`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SecurityActions.Read.All"], "required_role": "Compliance Administrator or DLP Compliance Management", "required_service": "Microsoft Purview Data L...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SecurityActions.Read.All"], "required_role": "Compliance Administrator or DLP Compliance Management", "required_service": "Microsoft Purview Data L...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SecurityActions.Read.All"], "required_role": "Compliance Administrator or DLP Compliance Management", "required_service": "Microsoft Purview Data L...
```

---

### Information Protection Labels applied
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/information_protection_labels_applied`
- **PowerShell Command**: `Get-InformationProtectionLabelsapplied`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["InformationProtectionPolicy.Read.All"], "required_role": "Compliance Administrator or Information Protection Administrator", "required_service": "M...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["InformationProtectionPolicy.Read.All"], "required_role": "Compliance Administrator or Information Protection Administrator", "required_service": "M...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["InformationProtectionPolicy.Read.All"], "required_role": "Compliance Administrator or Information Protection Administrator", "required_service": "M...
```

---

### Secure Score percentage
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/secure_score_percentage`
- **PowerShell Command**: `Get-SecureScorepercentage`
- **Raw Response**:
```json
{"current_score": 54.0, "max_score": 64.0, "secure_score_percentage": 84.38}
```
- **Parsed Value**: `{"current_score": 54.0, "max_score": 64.0, "secure_score_percentage": 84.38}`
- **Stored Evidence**:
```json
{"current_score": 54.0, "max_score": 64.0, "secure_score_percentage": 84.38}
```

---

### Sensitivity Labels applied to Teams
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/sensitivity_labels_applied_to_teams`
- **PowerShell Command**: `Get-SensitivityLabelsappliedtoTeams`
- **Raw Response**:
```json
{"labeled_teams": 0, "total_teams": 1}
```
- **Parsed Value**: `{"labeled_teams": 0, "total_teams": 1}`
- **Stored Evidence**:
```json
{"labeled_teams": 0, "total_teams": 1}
```

---

### Sensitivity Labels configured and applied
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/sensitivity_labels_configured_and_applied`
- **PowerShell Command**: `Get-SensitivityLabelsconfiguredandapplied`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["InformationProtectionPolicy.Read.All"], "required_role": "Compliance Administrator or Information Protection Administrator", "required_service": "M...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["InformationProtectionPolicy.Read.All"], "required_role": "Compliance Administrator or Information Protection Administrator", "required_service": "M...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["InformationProtectionPolicy.Read.All"], "required_role": "Compliance Administrator or Information Protection Administrator", "required_service": "M...
```

---

### Active /Inactive teams
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/active_inactive_teams`
- **PowerShell Command**: `Get-Active/Inactiveteams`
- **Raw Response**:
```json
{"active_team_count": 0, "inactive_team_count": 0}
```
- **Parsed Value**: `{"active_team_count": 0, "inactive_team_count": 0}`
- **Stored Evidence**:
```json
{"active_team_count": 0, "inactive_team_count": 0}
```

---

### Activer/Inactive Teams users
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/activer_inactive_teams_users`
- **PowerShell Command**: `Get-Activer/InactiveTeamsusers`
- **Raw Response**:
```json
{"active_users": 0, "inactive_ratio": 0.0, "inactive_users": 0}
```
- **Parsed Value**: `{"active_users": 0, "inactive_ratio": 0.0, "inactive_users": 0}`
- **Stored Evidence**:
```json
{"active_users": 0, "inactive_ratio": 0.0, "inactive_users": 0}
```

---

### Copilot integration enabled
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/copilot_integration_enabled`
- **PowerShell Command**: `Get-Copilotintegrationenabled`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Guest access enabled / disabled
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/guest_access_enabled_disabled`
- **PowerShell Command**: `Get-Guestaccessenabled/disabled`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Meeting Policies configuration
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/meeting_policies_configuration`
- **PowerShell Command**: `Get-MeetingPoliciesconfiguration`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Meeting recording retention policies
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/meeting_recording_retention_policies`
- **PowerShell Command**: `Get-Meetingrecordingretentionpolicies`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Meeting transcription enabled
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/meeting_transcription_enabled`
- **PowerShell Command**: `Get-Meetingtranscriptionenabled`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Minimum number of owners
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/minimum_number_of_owners`
- **PowerShell Command**: `Get-Minimumnumberofowners`
- **Raw Response**:
```json
{"teams_with_less_than_2_owners": 0, "total_teams": 1}
```
- **Parsed Value**: `{"teams_with_less_than_2_owners": 0, "total_teams": 1}`
- **Stored Evidence**:
```json
{"teams_with_less_than_2_owners": 0, "total_teams": 1}
```

---

### Orphan Teams
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/orphan_teams`
- **PowerShell Command**: `Get-OrphanTeams`
- **Raw Response**:
```json
{"orphan_team_count": 0, "total_teams": 1}
```
- **Parsed Value**: `{"orphan_team_count": 0, "total_teams": 1}`
- **Stored Evidence**:
```json
{"orphan_team_count": 0, "total_teams": 1}
```

---

### Teams - Channel Email Addresses
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/teams_channel_email_addresses`
- **PowerShell Command**: `Get-Teams-ChannelEmailAddresses`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Teams - File Storage Option
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/teams_file_storage_option`
- **PowerShell Command**: `Get-Teams-FileStorageOption`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Teams - Lobby Bypass
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/teams_lobby_bypass`
- **PowerShell Command**: `Get-Teams-LobbyBypass`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Teams - Meeting Chat
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/teams_meeting_chat`
- **PowerShell Command**: `Get-Teams-MeetingChat`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Teams with external guest as owner
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/teams_with_external_guest_as_owner`
- **PowerShell Command**: `Get-Teamswithexternalguestasowner`
- **Raw Response**:
```json
{"teams_with_external_guest_owner": 0, "total_teams": 1}
```
- **Parsed Value**: `{"teams_with_external_guest_owner": 0, "total_teams": 1}`
- **Stored Evidence**:
```json
{"teams_with_external_guest_owner": 0, "total_teams": 1}
```

---

### Teams with external users
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/teams_with_external_users`
- **PowerShell Command**: `Get-Teamswithexternalusers`
- **Raw Response**:
```json
{"external_team_ratio": 0.0, "teams_with_external_users": 0, "total_teams": 1}
```
- **Parsed Value**: `{"external_team_ratio": 0.0, "teams_with_external_users": 0, "total_teams": 1}`
- **Stored Evidence**:
```json
{"external_team_ratio": 0.0, "teams_with_external_users": 0, "total_teams": 1}
```

---

### Third-party apps allowed
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/third_party_apps_allowed`
- **PowerShell Command**: `Get-Third-partyappsallowed`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "AADSTS500014: The service principal for resource 'ab3be6b7-f5df-413d-ac2d-abf1e3fd9c0b' is disabled. This indicate that a subscription within the tenant has lapsed,...
```

---

### Days to retain a deleted user’s OneDrive
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/days_to_retain_a_deleted_user_s_onedrive`
- **PowerShell Command**: `Get-Daystoretainadeleteduser’sOneDrive`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```

---

### External sharing settings
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/external_sharing_settings`
- **PowerShell Command**: `Get-Externalsharingsettings`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```

---

### Total active users on OneDrive
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/total_active_users_on_onedrive`
- **PowerShell Command**: `Get-TotalactiveusersonOneDrive`
- **Raw Response**:
```json
{"active_ratio": 0.0, "active_users": 0, "total_users": 0}
```
- **Parsed Value**: `{"active_ratio": 0.0, "active_users": 0, "total_users": 0}`
- **Stored Evidence**:
```json
{"active_ratio": 0.0, "active_users": 0, "total_users": 0}
```

---

### Expiration Policy for Anyone links
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/expiration_policy_for_anyone_links`
- **PowerShell Command**: `Get-ExpirationPolicyforAnyonelinks`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```

---

### Inactive site policies
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/inactive_site_policies`
- **PowerShell Command**: `Get-Inactivesitepolicies`
- **Raw Response**:
```json
{"inactive_site_count": 0, "inactive_site_percent": 0.0, "site_count": 0}
```
- **Parsed Value**: `{"inactive_site_count": 0, "inactive_site_percent": 0.0, "site_count": 0}`
- **Stored Evidence**:
```json
{"inactive_site_count": 0, "inactive_site_percent": 0.0, "site_count": 0}
```

---

### Permission Settings for anyone links
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/permission_setting_for_anyone_links`
- **PowerShell Command**: `Get-PermissionSettingsforanyonelinks`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```

---

### Site Ownership policies
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/site_ownership_policies`
- **PowerShell Command**: `Get-SiteOwnershippolicies`
- **Raw Response**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "Tenant does not have a SPO license.", "required_api": "Microsoft Graph Sites plus SharePoint Online PowerShell", "required_permissions": ["Sites.Read.All", "Group.R...
```
- **Parsed Value**: `{"collection_status": "COLLECTION_ERROR", "reason": "Tenant does not have a SPO license.", "required_api": "Microsoft Graph Sites plus SharePoint Online PowerShell", "required_permissions": ["Sites.Read.All", "Group.R...`
- **Stored Evidence**:
```json
{"collection_status": "COLLECTION_ERROR", "reason": "Tenant does not have a SPO license.", "required_api": "Microsoft Graph Sites plus SharePoint Online PowerShell", "required_permissions": ["Sites.Read.All", "Group.R...
```

---

### Active Sites count
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/active_sites_count`
- **PowerShell Command**: `Get-ActiveSitescount`
- **Raw Response**:
```json
{"active_ratio": 0.0, "active_site_count": 0, "total_sites": 0}
```
- **Parsed Value**: `{"active_ratio": 0.0, "active_site_count": 0, "total_sites": 0}`
- **Stored Evidence**:
```json
{"active_ratio": 0.0, "active_site_count": 0, "total_sites": 0}
```

---

### Active users on SharePoint
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/active_users_on_sharepoint`
- **PowerShell Command**: `Get-ActiveusersonSharePoint`
- **Raw Response**:
```json
{"active_ratio": 0.0, "active_users": 0, "total_users": 0}
```
- **Parsed Value**: `{"active_ratio": 0.0, "active_users": 0, "total_users": 0}`
- **Stored Evidence**:
```json
{"active_ratio": 0.0, "active_users": 0, "total_users": 0}
```

---

### Getting all sites with Sensitivity keywords on a Tenant
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/getting_all_sites_with_sensitivity_keywords_on_a_tenant`
- **PowerShell Command**: `Get-GettingallsiteswithSensitivitykeywordsonaTenant`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["Sites.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint site inventory", "required_s...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["Sites.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint site inventory", "required_s...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["Sites.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint site inventory", "required_s...
```

---

### SharePoint & OneDrive Guest Access Expiry
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/sharepoint_and_onedrive_guest_access_expiry`
- **PowerShell Command**: `Get-SharePoint&OneDriveGuestAccessExpiry`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```

---

### SharePoint - Modern Authentication
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/sharepoint_modern_authentication`
- **PowerShell Command**: `Get-SharePoint-ModernAuthentication`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```

---

### Sharing Settings (External/Internal)
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/sharing_settings_external_internal`
- **PowerShell Command**: `Get-SharingSettings(External/Internal)`
- **Raw Response**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```
- **Parsed Value**: `{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...`
- **Stored Evidence**:
```json
{"collection_status": "LICENSING_REQUIRED", "required_permissions": ["SharePointTenantSettings.Read.All"], "required_role": "SharePoint Administrator or Global Administrator", "required_service": "SharePoint tenant se...
```

---

### Storage Quota consumption
- **Graph Endpoint**: `https://graph.microsoft.com/v1.0/storage_quota_consumption`
- **PowerShell Command**: `Get-StorageQuotaconsumption`
- **Raw Response**:
```json
{"max_storage_quota_ratio": 0.0, "site_count": 0, "sites_over_90_percent": 0}
```
- **Parsed Value**: `{"max_storage_quota_ratio": 0.0, "site_count": 0, "sites_over_90_percent": 0}`
- **Stored Evidence**:
```json
{"max_storage_quota_ratio": 0.0, "site_count": 0, "sites_over_90_percent": 0}
```

---
