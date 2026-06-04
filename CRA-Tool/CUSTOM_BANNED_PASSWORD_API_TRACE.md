# Custom Banned Password API Trace

Generated: 2026-06-04

## Tenant Trace Context

- Tenant ID: `fe4eff9a-f69c-48c0-921d-8006a6d5beb2`
- Tenant status: `ACTIVE`
- Token path: CRA app-only Microsoft Graph token
- Request header: `Authorization: Bearer <redacted>`
- Permission used by runtime: configured CRA application permissions
- Target parameter: `custom_banned_password_list`

## Live API Trace

| Method | Endpoint | HTTP status | Result | Password protection fields found |
| --- | --- | ---: | --- | --- |
| GET | `/v1.0/policies/authenticationMethodsPolicy` | 200 | Returned authentication methods policy | NO |
| GET | `/beta/policies/authenticationMethodsPolicy` | 200 | Returned authentication methods policy | NO |
| GET | `/v1.0/policies/authenticationMethodsPolicy/authenticationMethodConfigurations` | 400 | `Resource not found for segment 'authenticationMethodsPolicy/authenticationMethodConfigurations'.` | NO |
| GET | `/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations` | 400 | `Resource not found for segment 'authenticationMethodsPolicy/authenticationMethodConfigurations'.` | NO |
| GET | `/v1.0/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/password` | 404 | `Invalid authMethodType Provided password` | NO |
| GET | `/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/password` | 404 | `Invalid authMethodType Provided password` | NO |
| GET | `/v1.0/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/Password` | 404 | `Invalid authMethodType Provided Password` | NO |
| GET | `/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/Password` | 404 | `Invalid authMethodType Provided Password` | NO |
| GET | `/v1.0/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/passwordAuthenticationMethodConfiguration` | 404 | `Policy configuration for authentication method passwordAuthenticationMethodConfiguration not found` | NO |
| GET | `/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/passwordAuthenticationMethodConfiguration` | 404 | `Policy configuration for authentication method passwordAuthenticationMethodConfiguration not found` | NO |
| GET | `/v1.0/directory/authorizationPolicy` | 400 | Incorrect endpoint form; CRA uses `/policies/authorizationPolicy` elsewhere | NO |
| GET | `/beta/directory/authorizationPolicy` | 400 | Incorrect endpoint form; CRA uses `/policies/authorizationPolicy` elsewhere | NO |

## Successful Graph Response Summary

`GET /v1.0/policies/authenticationMethodsPolicy` returned:

```json
{
  "id": "authenticationMethodsPolicy",
  "displayName": "Authentication Methods Policy",
  "policyVersion": "2.0",
  "authenticationMethodConfigurations_count": 10,
  "authenticationMethodConfigurations_ids": [
    "Fido2",
    "MicrosoftAuthenticator",
    "Sms",
    "TemporaryAccessPass",
    "SoftwareOath",
    "Voice",
    "Email",
    "X509Certificate",
    "VerifiableCredentials",
    "QRCodePin"
  ],
  "found_password_protection_fields": {}
}
```

`GET /beta/policies/authenticationMethodsPolicy` returned:

```json
{
  "id": "authenticationMethodsPolicy",
  "displayName": "Authentication Methods Policy",
  "policyVersion": "2.0",
  "authenticationMethodConfigurations_count": 12,
  "authenticationMethodConfigurations_ids": [
    "Fido2",
    "MicrosoftAuthenticator",
    "Sms",
    "TemporaryAccessPass",
    "HardwareOath",
    "SoftwareOath",
    "Voice",
    "Email",
    "X509Certificate",
    "VerifiableCredentials",
    "QRCodePin",
    "FederatedIdentityCredential"
  ],
  "found_password_protection_fields": {}
}
```

## Field Scan Result

The trace recursively scanned every successful response for these fields:

- `EnableBannedPasswordCheck`
- `enableBannedPasswordCheck`
- `CustomBannedPasswordList`
- `customBannedPasswordList`
- `CustomBannedPasswordCount`
- `customBannedPasswordCount`
- `PasswordProtectionState`
- `passwordProtectionState`
- `SmartLockoutState`
- `smartLockoutState`
- `PasswordProtectionMode`
- `passwordProtectionMode`
- `isCustomBannedPasswordListEnabled`
- `customBannedPasswordListEnabled`
- `customBannedPasswords`
- `customWords`
- `customBannedPasswordTerms`
- `passwordProtectionEnabled`
- `isPasswordProtectionEnabled`
- `enforcementMode`

Result:

```json
{}
```

No required password protection or custom banned password fields were present.

## CRA Collector Runtime Trace

The active CRA collector attempted:

1. `https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/password`
2. `https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy`

Runtime outcome:

```json
{
  "parameter_key": "custom_banned_password_list",
  "status": "manual_validation_required",
  "actual_value": {
    "collection_status": "MANUAL_VALIDATION_REQUIRED",
    "reason": "Microsoft Graph was reachable but did not expose Custom Banned Password List fields for this tenant/runtime.",
    "enabled": null,
    "custom_word_count": null
  }
}
```

## API Trace Conclusion

Authentication is not the blocker. Microsoft Graph was reachable and returned policy data successfully.

The blocker is data exposure: the live Graph responses do not contain the Custom Banned Password List configuration or count needed to determine PASS or FAIL.
