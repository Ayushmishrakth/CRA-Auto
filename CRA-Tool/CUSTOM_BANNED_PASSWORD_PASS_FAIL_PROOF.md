# Custom Banned Password PASS/FAIL Proof

Generated: 2026-06-04

## Required PASS/FAIL Logic

PASS can be assigned only when both are proven from tenant evidence:

```json
{
  "enabled": true,
  "custom_word_count": 1,
  "enforcement_mode": "enforced",
  "status": "pass"
}
```

FAIL can be assigned only when tenant evidence proves one of these states:

```json
{
  "enabled": false,
  "custom_word_count": 0,
  "enforcement_mode": "disabled",
  "status": "fail"
}
```

or:

```json
{
  "enabled": true,
  "custom_word_count": 0,
  "enforcement_mode": "enforced",
  "status": "fail"
}
```

## Actual Tenant Evidence

Live tenant: `fe4eff9a-f69c-48c0-921d-8006a6d5beb2`

Actual evidence available from Microsoft Graph:

```json
{
  "enabled": null,
  "custom_word_count": null,
  "enforcement_mode": "not_exposed",
  "status": "manual_validation_required"
}
```

The values are `null` because Microsoft Graph successfully returned authentication methods policy data but did not expose any field that proves:

- Password Protection enabled state
- Custom banned password list enabled state
- Custom banned password list terms
- Custom banned password count
- Enforcement mode
- Smart lockout state
- Password protection state

## Why PASS Cannot Be Proven

PASS requires proof that the feature is enabled and at least one custom term exists.

The live API responses contained no equivalent of:

- `enabled = true`
- `custom_word_count > 0`
- `CustomBannedPasswordList`
- `CustomBannedPasswordCount`

Therefore PASS cannot be determined automatically.

## Why FAIL Cannot Be Proven

FAIL requires proof that the feature is disabled or that the custom banned password list is empty.

The live API responses contained no equivalent of:

- `enabled = false`
- `custom_word_count = 0`
- empty custom banned password list

An absent field is not proof of disabled configuration. It only proves the current API response does not expose the configuration.

Therefore FAIL cannot be determined automatically.

## Code-Level Proof

The collector already contains deterministic PASS/FAIL logic if Microsoft exposes the required data:

- `app/services/graph_cra_collector_service.py:2029` sets `pass` when `enabled and custom_word_count > 0`; otherwise `fail`.
- `app/services/graph_cra_collector_service.py:2153` parses possible Microsoft field names such as `isCustomBannedPasswordListEnabled`, `enableBannedPasswordCheck`, `customBannedPasswords`, `customBannedPasswordCount`, `passwordProtectionEnabled`, and `passwordProtectionMode`.
- `app/services/graph_cra_collector_service.py:2257` returns manual validation only after a Graph endpoint succeeds but no configuration fields are exposed.

The legacy PowerShell script does not provide independent evidence:

- `app/powershell/entra/entra_master.ps1:184` emits `not_collected`.
- `app/powershell/entra/entra_master.ps1:186` states that the custom banned password list requires Entra Password Protection policy access not available from that generic Graph script path.

## PowerShell Proof

Installed Microsoft Graph PowerShell commands found:

- `Get-MgPolicyAuthenticationMethodPolicy`
- `Get-MgPolicyAuthenticationMethodPolicyAuthenticationMethodConfiguration`
- `Get-MgBetaPolicyAuthenticationMethodPolicy`
- `Get-MgBetaPolicyAuthenticationMethodPolicyAuthenticationMethodConfiguration`

No installed command was found for:

- `*Password*Protection*`
- `*Banned*Password*`

The Graph PowerShell commands map to the same Graph authentication methods policy resource that was already tested and did not expose the required fields.

## Final Determination

Definitive answer: C) Microsoft exposes insufficient data and this parameter must remain MANUAL_VALIDATION.

This is not because the CRA collector is missing, and not because the CRA app failed to authenticate. The runtime authenticated successfully and received Microsoft Graph policy responses. The missing piece is Microsoft API data exposure for the Custom Banned Password List configuration.

Until Microsoft exposes the custom banned password list enabled state and count through a supported tenant API or PowerShell cmdlet, the platform cannot honestly classify this parameter as PASS or FAIL from automated evidence.
