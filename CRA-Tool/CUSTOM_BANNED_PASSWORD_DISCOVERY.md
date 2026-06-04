# Custom Banned Password Discovery

Generated: 2026-06-04

## Parameter

- Parameter key: `custom_banned_password_list`
- Parameter name: Custom Banned Password List
- Manual validation path: Admin Center -> Identity -> Entra ID -> Authentication Methods -> Password Protection
- CRA pass requirement: Password Protection is enabled and the custom banned password list contains one or more custom terms.
- CRA fail requirement: Password Protection is disabled, or no custom banned password terms are configured.

## Existing CRA Implementation Search

Search terms used:

- `Password Protection`
- `Banned Password`
- `Authentication Methods`
- `Entra Password Protection`
- `EnableBannedPasswordCheck`
- `CustomBannedPassword`
- `SmartLockout`
- `PasswordProtectionMode`
- `PasswordProtectionState`

Findings:

| Location | Finding |
| --- | --- |
| `app/services/graph_cra_collector_service.py:2010` | Active collector `collect_custom_banned_password_list`. It attempts Microsoft Graph beta endpoints and can return PASS/FAIL only if password protection fields are exposed. |
| `app/services/graph_cra_collector_service.py:2153` | Parser searches for `isCustomBannedPasswordListEnabled`, `customBannedPasswordListEnabled`, `enableBannedPasswordCheck`, `passwordProtectionEnabled`, `customBannedPasswords`, `customWords`, `customBannedPasswordCount`, `passwordProtectionMode`, and equivalent field names. |
| `app/powershell/entra/entra_master.ps1:184` | Legacy PowerShell script emits `not_collected` for this control with message that Entra Password Protection policy access is not available from the generic Graph script path. |
| `app/config/assessment_registry/collectors.json:1061` | Registry marks this as a Graph collector: `graph.custom_banned_password_list`. |

## Microsoft API And PowerShell Discovery

| Collection path | Endpoint or command | Permission required | Example response observed/documented | Tenant evidence available |
| --- | --- | --- | --- | --- |
| Microsoft Graph v1.0 | `GET /policies/authenticationMethodsPolicy` | `Policy.Read.AuthenticationMethod` or `Policy.Read.All` | Returns authentication methods policy and `authenticationMethodConfigurations` for methods such as FIDO2, Microsoft Authenticator, SMS, Temporary Access Pass, Software OATH, Voice, Email, X509Certificate, VerifiableCredentials, QRCodePin. No password protection fields. | NO |
| Microsoft Graph beta | `GET /policies/authenticationMethodsPolicy` | `Policy.Read.AuthenticationMethod` or `Policy.Read.All` | Returns authentication methods policy plus beta-only authentication method settings. No `CustomBannedPasswordList`, `PasswordProtectionState`, `SmartLockoutState`, or equivalent password protection fields. | NO |
| Microsoft Graph v1.0/beta direct config | `GET /policies/authenticationMethodsPolicy/authenticationMethodConfigurations/password` | `Policy.Read.AuthenticationMethod` or `Policy.Read.All` | Live tenant returned `404 resourceNotFound`, `Invalid authMethodType Provided password`. | NO |
| Microsoft Graph PowerShell SDK | `Get-MgPolicyAuthenticationMethodPolicy` and `Get-MgPolicyAuthenticationMethodPolicyAuthenticationMethodConfiguration` | Same Graph permissions as the REST API | PowerShell SDK wraps the Graph authentication methods policy resource. Installed commands exist, but no password protection configuration object is exposed. | NO |
| Microsoft Graph Beta PowerShell SDK | `Get-MgBetaPolicyAuthenticationMethodPolicy` and `Get-MgBetaPolicyAuthenticationMethodPolicyAuthenticationMethodConfiguration` | Same Graph beta permissions as the REST API | Installed commands exist. Same beta Graph policy object; live beta REST response did not expose password protection fields. | NO |
| Microsoft Entra PowerShell module | Search for `*Password*Protection*`, `*Banned*Password*` | N/A | No installed Entra/AzureAD/MSOnline command was found for custom banned password list retrieval. | NO |
| AzureAD / MSOnline module | Search for `*Password*Protection*`, `*Banned*Password*` | N/A | No command surfaced locally for reading the custom banned password list. | NO |
| CRA internal policy endpoints | `/policies/authorizationPolicy`, `/policies/adminConsentRequestPolicy`, `/policies/crossTenantAccessPolicy`, `/policies/authenticationMethodsPolicy` | Varies by endpoint | Existing CRA policy endpoints collect authorization, consent, cross-tenant, and authentication method settings. None expose Entra Password Protection custom banned terms. | NO |

## Requested Field Availability

| Field | Found in live tenant API response |
| --- | --- |
| `EnableBannedPasswordCheck` | NO |
| `CustomBannedPasswordList` | NO |
| `CustomBannedPasswordCount` | NO |
| `PasswordProtectionState` | NO |
| `SmartLockoutState` | NO |
| `PasswordProtectionMode` | NO |

## Documentation Evidence

Microsoft documents that custom banned password lists are configured through Microsoft Entra Password Protection and are used with the global banned password list. Microsoft also documents the Graph authentication methods policy as controlling authentication/MFA method registration, not Entra Password Protection custom banned terms.

Official references:

- Microsoft Entra Password Protection: https://learn.microsoft.com/en-us/entra/identity/authentication/concept-password-ban-bad
- Microsoft Graph `authenticationMethodsPolicy`: https://learn.microsoft.com/en-us/graph/api/resources/authenticationmethodspolicy?view=graph-rest-1.0
- Microsoft Graph Get `authenticationMethodsPolicy`: https://learn.microsoft.com/en-us/graph/api/authenticationmethodspolicy-get?view=graph-rest-1.0
- Microsoft Graph `authenticationMethodConfiguration` derived types: https://learn.microsoft.com/en-us/graph/api/resources/authenticationmethodconfiguration?view=graph-rest-1.0
- Graph PowerShell cmdlet: https://learn.microsoft.com/en-us/powershell/module/microsoft.graph.identity.signins/get-mgpolicyauthenticationmethodpolicyauthenticationmethodconfiguration?view=graph-powershell-1.0

## Discovery Conclusion

The CRA platform has exhausted the available Graph v1.0, Graph beta, Graph PowerShell, local PowerShell command discovery, and existing internal CRA policy endpoints. The required Custom Banned Password List fields are not exposed to the current runtime.

Definitive discovery result: Microsoft exposes insufficient data for automated PASS/FAIL determination in this tenant/runtime.
