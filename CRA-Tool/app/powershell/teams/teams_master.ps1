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
Assert-CraModule "MicrosoftTeams"
Assert-CraModule "Microsoft.Graph"
$collector = $CollectorJson | ConvertFrom-Json

$out = Initialize-CraArtifactDirectory -OutputRoot $OutputRoot -AssessmentId $AssessmentId -Domain "teams"
$files = New-Object System.Collections.Generic.List[string]

# Attempt Teams connection — emit a clean skipped contract if Teams admin access
# is unavailable (no credentials, wrong permissions, etc.) rather than crashing.
$teamsConnected = $false
try {
  Connect-CraTeams -TenantId $TenantId -Collector $collector
  # Validate by calling an actual Teams admin API — Get-CsTeamsMeetingPolicy throws
  # "You must call Connect-MicrosoftTeams" immediately when the session isn't established.
  $null = Get-CsTeamsMeetingPolicy -ErrorAction Stop
  $teamsConnected = $true
} catch {
  $teamsErrMsg = $_.Exception.Message
  # Emit a clean service_unavailable finding and exit
  [ordered]@{
    status    = "success"; collector = $CollectorName; tenant_id = $TenantId
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
    findings  = @([ordered]@{
      parameter_key      = $ParameterKey
      status             = "service_unavailable"
      severity           = "info"
      value              = "teams_unavailable"
      message            = "Microsoft Teams PowerShell is not available in this tenant (authentication failed or Teams not licensed). This module is skipped and excluded from scoring."
      score_contribution = 0
    })
    metrics  = [ordered]@{ generated_files = @(); generated_file_count = 0 }
    warnings = @("TEAMS_UNAVAILABLE: $teamsErrMsg"); errors = @()
  } | ConvertTo-Json -Depth 8 -Compress
  exit 0
}
Connect-CraGraph -TenantId $TenantId -Scopes @("Reports.Read.All","Group.Read.All","Team.ReadBasic.All") -Collector $collector | Out-Null

$teamInventoryParameters = @(
  "active_inactive_teams",
  "activer_inactive_teams_users",
  "minimum_number_of_owners",
  "orphan_teams",
  "teams_with_external_users",
  "teams_with_external_guest_as_owner"
)

if ($ParameterKey -in $teamInventoryParameters) {
  $teams = Get-Team | Where-Object { $_.GroupId } | Select-Object GroupId,DisplayName,Visibility,Archived,MailNickName,Description
  $path = Join-Path $out "teams_inventory.csv"; Export-CraCsv $teams $path; $files.Add($path)

  $externalUsers = foreach ($team in $teams) {
    try {
      Get-TeamUser -GroupId $team.GroupId -ErrorAction Stop | Where-Object { $_.User -match "#EXT#|\.onmicrosoft\.com" } |
        Select-Object @{Name="GroupId";Expression={$team.GroupId}}, @{Name="Team";Expression={$team.DisplayName}}, User, Role
    } catch {
      [pscustomobject]@{
        GroupId = $team.GroupId
        Team = $team.DisplayName
        User = ""
        Role = ""
        status = "not_collected"
        value = $_.Exception.Message
        evidence_source = "Get-TeamUser"
      }
    }
  }
  $path = Join-Path $out "teams_external_users.csv"; Export-CraCsv $externalUsers $path; $files.Add($path)
  $externalGuestOwners = $externalUsers | Where-Object { $_.Role -match "Owner" }
  $externalGuestOwnerEvidence = if (@($externalGuestOwners).Count -gt 0) {
    $externalGuestOwners | Select-Object GroupId,Team,User,Role,@{Name="status";Expression={"fail"}},@{Name="value";Expression={"External guest owner=$($_.User)"}},@{Name="evidence_source";Expression={"Get-TeamUser"}}
  } else {
    @([pscustomobject]@{ GroupId = ""; Team = ""; User = ""; Role = ""; status = "pass"; value = "No external guest owners found"; evidence_source = "Get-TeamUser" })
  }
  $path = Join-Path $out "teams_with_external_guest_as_owner.csv"; Export-CraCsv $externalGuestOwnerEvidence $path; $files.Add($path)

  $inactiveTeams = $teams | Where-Object { $_.Archived -eq $true } |
    Select-Object GroupId,DisplayName,Archived,Visibility
  $path = Join-Path $out "inactive_teams.csv"; Export-CraCsv $inactiveTeams $path; $files.Add($path)

  $activeTeamsEvidence = $teams | Select-Object GroupId,DisplayName,Archived,Visibility,@{Name="status";Expression={ if ($_.Archived -eq $true) { "fail" } else { "pass" } }},@{Name="value";Expression={ "Archived=$($_.Archived)" }},@{Name="evidence_source";Expression={ "Get-Team" }}
  Export-CraExpectedCsv $activeTeamsEvidence $out "active_inactive_teams.csv" $files "Get-Team"

  $activeUsersEvidence = $externalUsers | Select-Object GroupId,Team,User,Role,@{Name="status";Expression={ if ($_.status -eq "not_collected") { "not_collected" } else { "pass" } }},@{Name="value";Expression={ if ($_.value) { $_.value } else { "User=$($_.User);Role=$($_.Role)" } }},@{Name="evidence_source";Expression={ "Get-TeamUser" }}
  if (-not $activeUsersEvidence -or @($activeUsersEvidence).Count -eq 0) {
    $activeUsersEvidence = @([pscustomobject]@{ status = "pass"; value = "No external Teams users returned by Get-TeamUser"; evidence_source = "Get-TeamUser" })
  }
  Export-CraExpectedCsv $activeUsersEvidence $out "activer_inactive_teams_users.csv" $files "Get-TeamUser"
  Export-CraExpectedCsv $activeUsersEvidence $out "teams_with_external_users.csv" $files "Get-TeamUser"

  $ownerCounts = foreach ($team in $teams) {
    try {
      $owners = @(Get-TeamUser -GroupId $team.GroupId -Role Owner -ErrorAction Stop)
      [pscustomobject]@{
        GroupId = $team.GroupId
        Team = $team.DisplayName
        OwnerCount = $owners.Count
        status = if ($owners.Count -ge 2) { "pass" } else { "fail" }
        value = "OwnerCount=$($owners.Count)"
        evidence_source = "Get-TeamUser -Role Owner"
      }
    } catch {
      [pscustomobject]@{
        GroupId = $team.GroupId
        Team = $team.DisplayName
        OwnerCount = ""
        status = "not_collected"
        value = $_.Exception.Message
        evidence_source = "Get-TeamUser -Role Owner"
      }
    }
  }
  Export-CraExpectedCsv $ownerCounts $out "minimum_number_of_owners.csv" $files "Get-TeamUser -Role Owner"

  $orphanEvidence = $ownerCounts | Select-Object GroupId,Team,OwnerCount,@{Name="status";Expression={ if ($_.status -eq "not_collected") { "not_collected" } elseif ($_.OwnerCount -gt 0) { "pass" } else { "fail" } }},@{Name="value";Expression={ if ($_.value) { $_.value } else { "OwnerCount=$($_.OwnerCount)" } }},@{Name="evidence_source";Expression={ "Get-TeamUser -Role Owner" }}
  Export-CraExpectedCsv $orphanEvidence $out "orphan_teams.csv" $files "Get-TeamUser -Role Owner"
}

# Evaluate the org-wide Global meeting policy (the effective default for most users),
# matching how the manual assessment scores these controls. Reading ALL policies here
# would fail a control whenever any built-in/custom policy differs from Global, even
# though the tenant default passes (the CSV evaluator fails on any single "fail" row).
$meetingPolicies = Get-CsTeamsMeetingPolicy -Identity Global |
  Select-Object Identity,AllowCloudRecording,AllowTranscription,AllowAnonymousUsersToJoinMeeting,AutoAdmittedUsers,MeetingChatEnabledType,NewMeetingRecordingExpirationDays
$path = Join-Path $out "meeting_policies.csv"; Export-CraCsv $meetingPolicies $path; $files.Add($path)

# parameter_key -> @{ status; message; severity }; emitted directly to the contract so the
# runtime persists the manual evaluated_value text (not the generic CSV placeholder).
$findingMap = @{}

# meeting_policies_configuration: recommended = cloud recording + transcription enabled.
$mpRecommended = ($meetingPolicies.AllowCloudRecording -eq $true -and $meetingPolicies.AllowTranscription -eq $true)
$findingMap["meeting_policies_configuration"] = @{ status = if ($mpRecommended) { "pass" } else { "fail" }; message = if ($mpRecommended) { "Recommended settings are configured" } else { "Recommended settings are not configured" }; severity = "medium" }

# meeting_transcription_enabled
$trOn = ($meetingPolicies.AllowTranscription -eq $true)
$findingMap["meeting_transcription_enabled"] = @{ status = if ($trOn) { "pass" } else { "fail" }; message = if ($trOn) { "Meeting transcription is enabled" } else { "Meeting transcription is disabled" }; severity = "low" }

# meeting_recording_retention_policies: recording enabled AND an expiration configured.
$recOn = ($meetingPolicies.AllowCloudRecording -eq $true -and $meetingPolicies.NewMeetingRecordingExpirationDays)
$findingMap["meeting_recording_retention_policies"] = @{ status = if ($recOn) { "pass" } else { "fail" }; message = if ($recOn) { "Retention policy is enabled expiration is set to $($meetingPolicies.NewMeetingRecordingExpirationDays) days" } else { "Retention policy is not enabled" }; severity = "medium" }

# teams_lobby_bypass: restrictive lobby (not Everyone / EveryoneInCompany / federated) is a pass.
$lobbyDesc = switch ("$($meetingPolicies.AutoAdmittedUsers)") {
  "Everyone" { "Everyone (including anonymous users)" }
  "EveryoneInCompany" { "Everyone in the organisation" }
  "EveryoneInSameAndFederatedCompany" { "Everyone in the organisation and federated organisations" }
  "EveryoneInCompanyExcludingGuests" { "Everyone in the organisation excluding guests" }
  "OrganizerOnly" { "Organizer only" }
  "InvitedUsers" { "Invited users only" }
  default { "$($meetingPolicies.AutoAdmittedUsers)" }
}
$lobbyPass = ($meetingPolicies.AutoAdmittedUsers -and ($meetingPolicies.AutoAdmittedUsers -notin @("Everyone","EveryoneInCompany","EveryoneInSameAndFederatedCompany")))
$findingMap["teams_lobby_bypass"] = @{ status = if ($lobbyPass) { "pass" } else { "fail" }; message = $lobbyDesc; severity = "medium" }

# teams_meeting_chat: manual baseline treats MeetingChatEnabledType=Enabled as a pass.
$chatOn = ("$($meetingPolicies.MeetingChatEnabledType)" -eq "Enabled")
$findingMap["teams_meeting_chat"] = @{ status = if ($chatOn) { "pass" } else { "fail" }; message = if ($chatOn) { "Enabled on global policy" } else { "$($meetingPolicies.MeetingChatEnabledType)" }; severity = "low" }

$meetingPolicyEvidence = $meetingPolicies | Select-Object Identity,AllowCloudRecording,AllowTranscription,AllowAnonymousUsersToJoinMeeting,AutoAdmittedUsers,MeetingChatEnabledType,NewMeetingRecordingExpirationDays,@{Name="status";Expression={ if ($_.AllowCloudRecording -eq $true -and $_.AllowTranscription -eq $true) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AllowCloudRecording=$($_.AllowCloudRecording);AllowTranscription=$($_.AllowTranscription);MeetingChatEnabledType=$($_.MeetingChatEnabledType)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsMeetingPolicy" }}
Export-CraExpectedCsv $meetingPolicyEvidence $out "meeting_policies_configuration.csv" $files "Get-CsTeamsMeetingPolicy"

$transcriptionEvidence = $meetingPolicies | Select-Object Identity,AllowTranscription,@{Name="status";Expression={ if ($_.AllowTranscription -eq $true) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AllowTranscription=$($_.AllowTranscription)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsMeetingPolicy" }}
Export-CraExpectedCsv $transcriptionEvidence $out "meeting_transcription_enabled.csv" $files "Get-CsTeamsMeetingPolicy"

$recordingRetentionEvidence = $meetingPolicies | Select-Object Identity,AllowCloudRecording,NewMeetingRecordingExpirationDays,@{Name="status";Expression={ if ($_.AllowCloudRecording -eq $true -and $_.NewMeetingRecordingExpirationDays) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AllowCloudRecording=$($_.AllowCloudRecording);NewMeetingRecordingExpirationDays=$($_.NewMeetingRecordingExpirationDays)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsMeetingPolicy" }}
Export-CraExpectedCsv $recordingRetentionEvidence $out "meeting_recording_retention_policies.csv" $files "Get-CsTeamsMeetingPolicy"

$lobbyEvidence = $meetingPolicies | Select-Object Identity,AutoAdmittedUsers,@{Name="status";Expression={ if ($_.AutoAdmittedUsers -and $_.AutoAdmittedUsers -notin @("Everyone","EveryoneInCompany")) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AutoAdmittedUsers=$($_.AutoAdmittedUsers)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsMeetingPolicy" }}
Export-CraExpectedCsv $lobbyEvidence $out "teams_lobby_bypass.csv" $files "Get-CsTeamsMeetingPolicy"

$chatEvidence = $meetingPolicies | Select-Object Identity,MeetingChatEnabledType,@{Name="status";Expression={ if ($_.MeetingChatEnabledType -eq "Enabled") { "pass" } else { "fail" } }},@{Name="value";Expression={ "MeetingChatEnabledType=$($_.MeetingChatEnabledType)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsMeetingPolicy" }}
Export-CraExpectedCsv $chatEvidence $out "teams_meeting_chat.csv" $files "Get-CsTeamsMeetingPolicy"

# Anonymous Users (F1): anonymous join must be disabled.
$anonymousEvidence = $meetingPolicies | Select-Object Identity,AllowAnonymousUsersToJoinMeeting,@{Name="status";Expression={ if ($_.AllowAnonymousUsersToJoinMeeting -eq $false) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AllowAnonymousUsersToJoinMeeting=$($_.AllowAnonymousUsersToJoinMeeting)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsMeetingPolicy" }}
Export-CraExpectedCsv $anonymousEvidence $out "teams_anonymous_users.csv" $files "Get-CsTeamsMeetingPolicy"

# External Unmanaged User Communication (F2): consumer (Teams personal) federation must be disabled.
try {
  $federation = Get-CsTenantFederationConfiguration -ErrorAction Stop | Select-Object Identity,AllowTeamsConsumer
  $unmanagedEvidence = $federation | Select-Object Identity,AllowTeamsConsumer,@{Name="status";Expression={ if ($_.AllowTeamsConsumer -eq $false) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AllowTeamsConsumer=$($_.AllowTeamsConsumer)" }},@{Name="evidence_source";Expression={ "Get-CsTenantFederationConfiguration" }}
} catch {
  $unmanagedEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTenantFederationConfiguration" })
}
Export-CraExpectedCsv $unmanagedEvidence $out "teams_external_unmanaged_users.csv" $files "Get-CsTenantFederationConfiguration"

try {
  $clientConfig = Get-CsTeamsClientConfiguration | Select-Object Identity,AllowGuestUser,AllowEmailIntoChannel,RestrictedSenderList,AllowDropBox,AllowBox,AllowGoogleDrive,AllowShareFile,AllowEgnyte
  $guestAccessEvidence = $clientConfig | Select-Object Identity,AllowGuestUser,@{Name="status";Expression={ if ($_.AllowGuestUser -eq $false) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AllowGuestUser=$($_.AllowGuestUser)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsClientConfiguration" }}
  $fileStorageEvidence = $clientConfig | Select-Object Identity,AllowDropBox,AllowBox,AllowGoogleDrive,AllowShareFile,AllowEgnyte,@{Name="status";Expression={ if ($_.AllowDropBox -or $_.AllowBox -or $_.AllowGoogleDrive -or $_.AllowShareFile -or $_.AllowEgnyte) { "fail" } else { "pass" } }},@{Name="value";Expression={ "AllowDropBox=$($_.AllowDropBox);AllowBox=$($_.AllowBox);AllowGoogleDrive=$($_.AllowGoogleDrive);AllowShareFile=$($_.AllowShareFile);AllowEgnyte=$($_.AllowEgnyte)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsClientConfiguration" }}
  # NOTE: @($null).Count returns 1 in PowerShell, so an empty/null RestrictedSenderList
  # would falsely look like a configured whitelist. Filter out null entries before counting
  # so a truly empty list counts as 0 (email-into-channel enabled with no restriction => FAIL).
  $channelEmailEvidence = $clientConfig | Select-Object Identity,AllowEmailIntoChannel,@{Name="RestrictedSenderCount";Expression={ @($_.RestrictedSenderList | Where-Object { $_ }).Count }},@{Name="status";Expression={ if ($_.AllowEmailIntoChannel -eq $false -or (@($_.RestrictedSenderList | Where-Object { $_ }).Count -gt 0)) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AllowEmailIntoChannel=$($_.AllowEmailIntoChannel);RestrictedSenderCount=$(@($_.RestrictedSenderList | Where-Object { $_ }).Count)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsClientConfiguration" }}
} catch {
  $guestAccessEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTeamsClientConfiguration" })
  $fileStorageEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTeamsClientConfiguration" })
  $channelEmailEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTeamsClientConfiguration" })
}
Export-CraExpectedCsv $guestAccessEvidence $out "guest_access_enabled_disabled.csv" $files "Get-CsTeamsClientConfiguration"
Export-CraExpectedCsv $fileStorageEvidence $out "teams_file_storage_option.csv" $files "Get-CsTeamsClientConfiguration"
Export-CraExpectedCsv $channelEmailEvidence $out "teams_channel_email_addresses.csv" $files "Get-CsTeamsClientConfiguration"

if ($clientConfig) {
  # guest_access_enabled_disabled: guest access must be disabled.
  $guestOn = ($clientConfig.AllowGuestUser -eq $true)
  $findingMap["guest_access_enabled_disabled"] = @{ status = if ($guestOn) { "fail" } else { "pass" }; message = if ($guestOn) { "Guest access is enabled" } else { "Guest access is disabled" }; severity = "high" }
  # teams_file_storage_option: no third-party cloud storage providers may be allowed.
  $storageProviders = @()
  if ($clientConfig.AllowGoogleDrive) { $storageProviders += "GoogleDrive" }
  if ($clientConfig.AllowDropBox)     { $storageProviders += "Dropbox" }
  if ($clientConfig.AllowBox)         { $storageProviders += "Box" }
  if ($clientConfig.AllowShareFile)   { $storageProviders += "ShareFile" }
  if ($clientConfig.AllowEgnyte)      { $storageProviders += "Egnyte" }
  $findingMap["teams_file_storage_option"] = @{ status = if ($storageProviders.Count -gt 0) { "fail" } else { "pass" }; message = if ($storageProviders.Count -gt 0) { "Allowed:`n" + ($storageProviders -join "`n") } else { "No third-party file storage providers are allowed" }; severity = "medium" }
  # teams_channel_email_addresses: email-into-channel must be off or sender-restricted.
  $restrictedCount = @($clientConfig.RestrictedSenderList | Where-Object { $_ }).Count
  $emailOn = ($clientConfig.AllowEmailIntoChannel -eq $true)
  $findingMap["teams_channel_email_addresses"] = @{ status = if (-not $emailOn -or $restrictedCount -gt 0) { "pass" } else { "fail" }; message = if (-not $emailOn) { "Disabled" } elseif ($restrictedCount -gt 0) { "Enabled (restricted to $restrictedCount sender domain(s))" } else { "Enabled" }; severity = "medium" }
} else {
  foreach ($k in @("guest_access_enabled_disabled","teams_file_storage_option","teams_channel_email_addresses")) {
    $findingMap[$k] = @{ status = "fail"; message = "Teams client configuration could not be verified"; severity = "high" }
  }
}

try {
  # GlobalCatalogAppsType: "BlockedAppList" = allow ALL third-party apps except a blocklist
  # (permissive ⇒ apps ARE allowed). Only "BlockAllApps" effectively disables third-party
  # apps. The previous rule treated BlockedAppList as pass, which was inverted.
  $appPolicy = Get-CsTeamsAppPermissionPolicy -Identity Global | Select-Object Identity,GlobalCatalogAppsType,PrivateCatalogAppsType
  $thirdPartyEvidence = $appPolicy | Select-Object Identity,GlobalCatalogAppsType,PrivateCatalogAppsType,@{Name="status";Expression={ if ($_.GlobalCatalogAppsType -eq "BlockAllApps") { "pass" } else { "fail" } }},@{Name="value";Expression={ "GlobalCatalogAppsType=$($_.GlobalCatalogAppsType);PrivateCatalogAppsType=$($_.PrivateCatalogAppsType)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsAppPermissionPolicy" }}
} catch {
  $thirdPartyEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTeamsAppPermissionPolicy" })
}
Export-CraExpectedCsv $thirdPartyEvidence $out "third_party_apps_allowed.csv" $files "Get-CsTeamsAppPermissionPolicy"

if ($appPolicy) {
  $appsEffectivelyDisabled = ("$($appPolicy.GlobalCatalogAppsType)" -eq "BlockAllApps")
  $findingMap["third_party_apps_allowed"] = @{ status = if ($appsEffectivelyDisabled) { "pass" } else { "fail" }; message = if ($appsEffectivelyDisabled) { "Third-party apps are not allowed" } else { "Third-party apps are allowed" }; severity = "high" }
} else {
  $findingMap["third_party_apps_allowed"] = @{ status = "fail"; message = "Third-party app policy could not be verified"; severity = "high" }
}

# Copilot integration is governed org-wide by CopilotFromHomeTenant on the
# multi-tenant org configuration — a single effective value, so no per-policy
# aggregation is needed. Matches the manual assessment (PASS when Copilot is
# enabled) and the value verified live via cert auth (CopilotFromHomeTenant=Enabled).
try {
  $copilotConfig = Get-CsTeamsMultiTenantOrganizationConfiguration -ErrorAction Stop | Select-Object CopilotFromHomeTenant
  $copilotOn = ("$($copilotConfig.CopilotFromHomeTenant)" -in @("Enabled","True")) -or ($copilotConfig.CopilotFromHomeTenant -eq $true)
  $copilotEvidence = @([pscustomobject]@{
    Identity = "Global"
    CopilotFromHomeTenant = "$($copilotConfig.CopilotFromHomeTenant)"
    status = if ($copilotOn) { "pass" } else { "fail" }
    value = "CopilotFromHomeTenant=$($copilotConfig.CopilotFromHomeTenant)"
    evidence_source = "Get-CsTeamsMultiTenantOrganizationConfiguration"
  })
} catch {
  $copilotEvidence = @([pscustomobject]@{
    Identity = ""
    CopilotFromHomeTenant = ""
    status = "not_collected"
    value = $_.Exception.Message
    evidence_source = "Get-CsTeamsMultiTenantOrganizationConfiguration"
  })
}
Export-CraExpectedCsv $copilotEvidence $out "copilot_integration_enabled.csv" $files "Get-CsTeamsMultiTenantOrganizationConfiguration"

if ($copilotConfig) {
  $findingMap["copilot_integration_enabled"] = @{ status = if ($copilotOn) { "pass" } else { "fail" }; message = if ($copilotOn) { "Copilot integration is enabled" } else { "Copilot integration is disabled" }; severity = "low" }
} else {
  $findingMap["copilot_integration_enabled"] = @{ status = "fail"; message = "Copilot integration could not be verified"; severity = "low" }
}

# Emit the real finding for the current parameter (manual evaluated_value text). Falls back
# to the generic CSV-evidence path only for a parameter not covered by the map.
if ($findingMap.ContainsKey($ParameterKey)) {
  $f = $findingMap[$ParameterKey]
  Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray() -FindingStatus $f.status -FindingMessage $f.message -FindingSeverity $f.severity
} else {
  Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray()
}
