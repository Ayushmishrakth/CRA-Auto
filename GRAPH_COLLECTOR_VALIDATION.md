# Graph Collector Validation

Fresh assessment `2bbbf23c-114c-4360-9f1f-8220f59598f8`.

| Parameter | Runtime Selected | Collector | Graph Endpoint | Raw Response Present | Artifact Status | Finding Status | Evidence Value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `guest_users_count` | `graph` | `powershell.guest_users_count` | `/users?$select=id,displayName,userPrincipalName,mail,userType` | True | `collected` | `pass` | {"guest_count": 0, "total_users": 14, "guest_ratio_percent": 0.0} |
| `account_enabled` | `graph` | `powershell.account_enabled` | `/users?$select=id,displayName,userPrincipalName,accountEnabled,userType` | True | `collected` | `pass` | {"enabled_count": 14, "total_users": 14, "enabled_percent": 100.0} |
| `users_without_mfa` | `graph` | `powershell.users_without_mfa` | `/users + /users/{id}/authentication/methods` | True | `collected` | `fail` | {"users_without_mfa": 2, "total_users": 14} |
| `authentication_methods_enabled` | `graph` | `powershell.authentication_methods_enabled` | `https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy` | True | `collected` | `pass` | {"enabled_methods": 4, "methods": [{"method": "MicrosoftAuthenticator", "state": "enabled"}, {"method": "Tempo... |
| `admin_consent_workflow` | `graph` | `powershell.admin_consent_workflow` | `/policies/adminConsentRequestPolicy` | True | `collected` | `fail` | {"@odata.context": "https://graph.microsoft.com/v1.0/$metadata#policies/adminConsentRequestPolicy/$entity", "i... |
| `conditional_access_policies_exclusion` | `graph` | `powershell.conditional_access_policies_exclusion` | `/identity/conditionalAccess/policies?$select=id,displayName,state,conditions,grantControls` | True | `collected` | `pass` | {"policies_with_exclusions": 0, "exclusions": []} |
| `secure_score_percentage` | `graph` | `portal.secure_score_percentage` | `/security/secureScores?$top=1` | True | `collected` | `pass` | {"current_score": 54.0, "max_score": 64.0, "secure_score_percentage": 84.38} |
| `devices_without_compliance_policies` | `graph` | `powershell.devices_without_compliance_policies` | `/deviceManagement/managedDevices` | True | `collected` | `fail` | {"managed_devices_available": false, "error": {"code": "BadRequest", "message": "Request not applicable to tar... |
| `assigned_license` | n/a | n/a | n/a | n/a | n/a | n/a | Not in official 65 registry; legacy manifest only. |
| `user_information` | `graph` | `powershell.user_information` | `/users?$select=id,displayName,userPrincipalName,mail,jobTitle,department` | True | `collected` | `fail` | {"complete_users": 12, "total_users": 14, "incomplete_users": 2} |
| `tenant_collaboration_invitations` | `graph` | `powershell.tenant_collaboration_invitations` | `/policies/crossTenantAccessPolicy + /policies/crossTenantAccessPolicy/partners` | True | `collected` | `fail` | {"partner_count": 0, "default": {}} |
