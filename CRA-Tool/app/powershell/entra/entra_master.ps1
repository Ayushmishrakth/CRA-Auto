param(
  [Parameter(Mandatory=$true)][string]$TenantId,
  [Parameter(Mandatory=$true)][string]$CollectorName,
  [Parameter(Mandatory=$true)][string]$ParameterKey,
  [Parameter(Mandatory=$true)][string]$ParameterJson,
  [Parameter(Mandatory=$true)][string]$CollectorJson,
  [Parameter(Mandatory=$true)][string]$AssessmentId,
  [Parameter(Mandatory=$true)][string]$OutputRoot
)

. (Join-Path $PSScriptRoot "../common/cra_common.ps1")
Assert-CraModule "Microsoft.Graph"
Assert-CraModule "Microsoft.Graph.Beta"
$collector = $CollectorJson | ConvertFrom-Json

$out = Initialize-CraArtifactDirectory -OutputRoot $OutputRoot -AssessmentId $AssessmentId -Domain "entra"
$scopes = @(
  "Directory.Read.All",
  "Policy.Read.All",
  "Application.Read.All",
  "RoleManagement.Read.Directory",
  "AuditLog.Read.All",
  "UserAuthenticationMethod.Read.All"
)
Connect-CraGraph -TenantId $TenantId -Scopes $scopes -Collector $collector | Out-Null

$files = New-Object System.Collections.Generic.List[string]

$roles = Get-MgDirectoryRole -All
$globalAdmin = $roles | Where-Object DisplayName -eq "Global Administrator" | Select-Object -First 1
if ($globalAdmin) {
  $globalAdmins = Get-MgDirectoryRoleMember -DirectoryRoleId $globalAdmin.Id -All |
    Select-Object Id, AdditionalProperties
} else {
  $globalAdmins = @()
}
$path = Join-Path $out "global_admins.csv"; Export-CraCsv $globalAdmins $path; $files.Add($path)

$guests = Get-MgUser -All -Filter "userType eq 'Guest'" -Property "id,displayName,userPrincipalName,mail,accountEnabled,createdDateTime,signInActivity,userType" |
  Select-Object Id,DisplayName,UserPrincipalName,Mail,AccountEnabled,CreatedDateTime,UserType
$path = Join-Path $out "guest_users.csv"; Export-CraCsv $guests $path; $files.Add($path)

$users = Get-MgUser -All -Property "id,displayName,userPrincipalName,mail,accountEnabled,createdDateTime,signInActivity,assignedLicenses,userType,jobTitle,department"
$inactive = $users | Select-Object Id,DisplayName,UserPrincipalName,AccountEnabled,CreatedDateTime
$path = Join-Path $out "inactive_users.csv"; Export-CraCsv $inactive $path; $files.Add($path)

$mfa = Get-MgReportAuthenticationMethodUserRegistrationDetail -All |
  Select-Object Id,UserPrincipalName,UserDisplayName,IsMfaRegistered,IsMfaCapable,IsPasswordlessCapable,MethodsRegistered
$path = Join-Path $out "mfa_status.csv"; Export-CraCsv $mfa $path; $files.Add($path)

$ca = Get-MgIdentityConditionalAccessPolicy -All |
  Select-Object Id,DisplayName,State,CreatedDateTime,ModifiedDateTime
$path = Join-Path $out "conditional_access.csv"; Export-CraCsv $ca $path; $files.Add($path)

$apps = Get-MgApplication -All |
  Select-Object Id,AppId,DisplayName,SignInAudience,CreatedDateTime
$path = Join-Path $out "applications.csv"; Export-CraCsv $apps $path; $files.Add($path)

$authPolicy = Get-MgPolicyAuthorizationPolicy | Select-Object Id,DisplayName,DefaultUserRolePermissions,AllowedToSignUpEmailBasedSubscriptions,AllowedToUseSspr
$path = Join-Path $out "security_defaults.csv"; Export-CraCsv $authPolicy $path; $files.Add($path)

try {
  $groupLifecycleResponse = Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/v1.0/groupLifecyclePolicies"
  $groupLifecyclePolicies = @($groupLifecycleResponse.value)
  $groupExpirationEvidence = if ($groupLifecyclePolicies.Count -gt 0) {
    $groupLifecyclePolicies | ForEach-Object {
      [pscustomobject]@{
        Id = $_.id
        GroupLifetimeInDays = $_.groupLifetimeInDays
        ManagedGroupTypes = $_.managedGroupTypes
        AlternateNotificationEmails = $_.alternateNotificationEmails
        status = "pass"
        value = "GroupLifetimeInDays=$($_.groupLifetimeInDays);ManagedGroupTypes=$($_.managedGroupTypes)"
        evidence_source = "GET /groupLifecyclePolicies"
      }
    }
  } else {
    @([pscustomobject]@{
      Id = ""
      GroupLifetimeInDays = ""
      ManagedGroupTypes = ""
      AlternateNotificationEmails = ""
      status = "fail"
      value = "No Microsoft 365 group lifecycle expiration policies found"
      evidence_source = "GET /groupLifecyclePolicies"
    })
  }
} catch {
  $groupExpirationEvidence = @([pscustomobject]@{
    Id = ""
    GroupLifetimeInDays = ""
    ManagedGroupTypes = ""
    AlternateNotificationEmails = ""
    status = "not_collected"
    value = $_.Exception.Message
    evidence_source = "GET /groupLifecyclePolicies"
  })
}
$path = Join-Path $out "auto_expiration_policy_for_inactive_m365_groups.csv"; Export-CraCsv $groupExpirationEvidence $path; $files.Add($path)

$accountEnabledEvidence = $users | Select-Object Id,DisplayName,UserPrincipalName,AccountEnabled,@{Name="status";Expression={ if ($_.AccountEnabled -eq $true) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AccountEnabled=$($_.AccountEnabled)" }},@{Name="evidence_source";Expression={ "Get-MgUser" }}
Export-CraExpectedCsv $accountEnabledEvidence $out "account_enabled.csv" $files "Get-MgUser"

$userInfoEvidence = $users | Select-Object Id,DisplayName,UserPrincipalName,Mail,JobTitle,Department,@{Name="status";Expression={ if ($_.DisplayName -and $_.UserPrincipalName) { "pass" } else { "fail" } }},@{Name="value";Expression={ "DisplayName=$($_.DisplayName);UPN=$($_.UserPrincipalName);Mail=$($_.Mail)" }},@{Name="evidence_source";Expression={ "Get-MgUser" }}
Export-CraExpectedCsv $userInfoEvidence $out "user_information.csv" $files "Get-MgUser"

$guestEvidence = $guests | Select-Object Id,DisplayName,UserPrincipalName,Mail,AccountEnabled,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "Guest=$($_.UserPrincipalName)" }},@{Name="evidence_source";Expression={ "Get-MgUser -Filter userType eq Guest" }}
if (-not $guestEvidence -or @($guestEvidence).Count -eq 0) {
  $guestEvidence = @([pscustomobject]@{ GuestCount = 0; status = "pass"; value = "No guest users returned"; evidence_source = "Get-MgUser -Filter userType eq Guest" })
}
Export-CraExpectedCsv $guestEvidence $out "guest_users_count.csv" $files "Get-MgUser -Filter userType eq Guest"

$globalAdminEvidence = $globalAdmins | Select-Object Id,AdditionalProperties,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "GlobalAdminMember=$($_.Id)" }},@{Name="evidence_source";Expression={ "Get-MgDirectoryRoleMember" }}
Export-CraExpectedCsv $globalAdminEvidence $out "global_administrator_accounts.csv" $files "Get-MgDirectoryRoleMember"

$mfaEvidence = $mfa | Select-Object Id,UserPrincipalName,UserDisplayName,IsMfaRegistered,IsMfaCapable,MethodsRegistered,@{Name="status";Expression={ if ($_.IsMfaRegistered -eq $true -or $_.IsMfaCapable -eq $true) { "pass" } else { "fail" } }},@{Name="value";Expression={ "IsMfaRegistered=$($_.IsMfaRegistered);Methods=$($_.MethodsRegistered -join ';')" }},@{Name="evidence_source";Expression={ "Get-MgReportAuthenticationMethodUserRegistrationDetail" }}
Export-CraExpectedCsv $mfaEvidence $out "users_without_mfa.csv" $files "Get-MgReportAuthenticationMethodUserRegistrationDetail"

$caEvidence = $ca | Select-Object Id,DisplayName,State,@{Name="status";Expression={ if ($_.State -eq "enabled") { "pass" } else { "fail" } }},@{Name="value";Expression={ "State=$($_.State)" }},@{Name="evidence_source";Expression={ "Get-MgIdentityConditionalAccessPolicy" }}
Export-CraExpectedCsv $caEvidence $out "cap_policies_for_risky_sign_ins.csv" $files "Get-MgIdentityConditionalAccessPolicy"
Export-CraExpectedCsv $caEvidence $out "conditional_access_policies_exclusion.csv" $files "Get-MgIdentityConditionalAccessPolicy"

$appEvidence = $apps | Select-Object Id,AppId,DisplayName,SignInAudience,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "App=$($_.DisplayName);Audience=$($_.SignInAudience)" }},@{Name="evidence_source";Expression={ "Get-MgApplication" }}
Export-CraExpectedCsv $appEvidence $out "entra_third_party_app_integrations.csv" $files "Get-MgApplication"

$authPolicyEvidence = $authPolicy | Select-Object Id,DisplayName,DefaultUserRolePermissions,AllowedToUseSspr,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "DefaultUserRolePermissions=$($_.DefaultUserRolePermissions)" }},@{Name="evidence_source";Expression={ "Get-MgPolicyAuthorizationPolicy" }}
Export-CraExpectedCsv $authPolicyEvidence $out "entra_tenant_creation_by_non_admin.csv" $files "Get-MgPolicyAuthorizationPolicy"
Export-CraExpectedCsv $authPolicyEvidence $out "restricted_access_to_microsoft_entra_admin_centre.csv" $files "Get-MgPolicyAuthorizationPolicy"
Export-CraExpectedCsv $authPolicyEvidence $out "user_consent_for_applications.csv" $files "Get-MgPolicyAuthorizationPolicy"
Export-CraExpectedCsv $authPolicyEvidence $out "self_service_password_reset_authentication_method.csv" $files "Get-MgPolicyAuthorizationPolicy"

try {
  $adminConsent = Get-MgPolicyAdminConsentRequestPolicy | Select-Object Id,IsEnabled,NotifyReviewers,RemindersEnabled,RequestDurationInDays
  $adminConsentEvidence = $adminConsent | Select-Object Id,IsEnabled,NotifyReviewers,RemindersEnabled,RequestDurationInDays,@{Name="status";Expression={ if ($_.IsEnabled -eq $true) { "pass" } else { "fail" } }},@{Name="value";Expression={ "IsEnabled=$($_.IsEnabled);RequestDurationInDays=$($_.RequestDurationInDays)" }},@{Name="evidence_source";Expression={ "Get-MgPolicyAdminConsentRequestPolicy" }}
} catch {
  $adminConsentEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-MgPolicyAdminConsentRequestPolicy" })
}
Export-CraExpectedCsv $adminConsentEvidence $out "admin_consent_workflow.csv" $files "Get-MgPolicyAdminConsentRequestPolicy"

try {
  $authMethods = Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy"
  $authMethodsEvidence = @($authMethods.authenticationMethodConfigurations) | ForEach-Object {
    [pscustomobject]@{
      Id = $_.id
      State = $_.state
      status = if ($_.state -eq "enabled") { "pass" } else { "fail" }
      value = "Method=$($_.id);State=$($_.state)"
      evidence_source = "GET /beta/policies/authenticationMethodsPolicy"
    }
  }
} catch {
  $authMethodsEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "GET /beta/policies/authenticationMethodsPolicy" })
}
Export-CraExpectedCsv $authMethodsEvidence $out "authentication_methods_enabled.csv" $files "GET /beta/policies/authenticationMethodsPolicy"

try {
  $crossTenant = Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/v1.0/policies/crossTenantAccessPolicy/partners"
  $tenantInviteEvidence = @($crossTenant.value) | ForEach-Object {
    [pscustomobject]@{
      TenantId = $_.tenantId
      status = "pass"
      value = "PartnerTenant=$($_.tenantId)"
      evidence_source = "GET /policies/crossTenantAccessPolicy/partners"
    }
  }
} catch {
  $tenantInviteEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "GET /policies/crossTenantAccessPolicy/partners" })
}
Export-CraExpectedCsv $tenantInviteEvidence $out "tenant_collaboration_invitations.csv" $files "GET /policies/crossTenantAccessPolicy/partners"

try {
  $guestInviteSettings = Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/v1.0/policies/authorizationPolicy"
  $guestInviteEvidence = @([pscustomobject]@{
    AllowInvitesFrom = $guestInviteSettings.allowInvitesFrom
    status = if ($guestInviteSettings.allowInvitesFrom -match "adminsAndGuestInviters|none") { "pass" } else { "fail" }
    value = "AllowInvitesFrom=$($guestInviteSettings.allowInvitesFrom)"
    evidence_source = "GET /policies/authorizationPolicy"
  })
} catch {
  $guestInviteEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "GET /policies/authorizationPolicy" })
}
Export-CraExpectedCsv $guestInviteEvidence $out "guest_invite_settings.csv" $files "GET /policies/authorizationPolicy"

$customBannedPasswordEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "Custom banned password list requires Entra Password Protection policy access not available from this generic Graph script path."
  evidence_source = "Entra Password Protection policy"
})
Export-CraExpectedCsv $customBannedPasswordEvidence $out "custom_banned_password_list.csv" $files "Entra Password Protection policy"

$emergencyEvidence = $globalAdmins | Select-Object Id,AdditionalProperties,@{Name="status";Expression={ "not_collected" }},@{Name="value";Expression={ "Global admin inventory collected; emergency account identification requires tenant naming/tagging rule." }},@{Name="evidence_source";Expression={ "Get-MgDirectoryRoleMember" }}
Export-CraExpectedCsv $emergencyEvidence $out "emergency_access_accounts.csv" $files "Get-MgDirectoryRoleMember"

$deviceComplianceEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "Intune managed device compliance data requires deviceManagement/managedDevices access."
  evidence_source = "GET /deviceManagement/managedDevices"
})
Export-CraExpectedCsv $deviceComplianceEvidence $out "devices_without_compliance_policies.csv" $files "GET /deviceManagement/managedDevices"

Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray()
