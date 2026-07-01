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

$meetingPolicies = Get-CsTeamsMeetingPolicy |
  Select-Object Identity,AllowCloudRecording,AllowTranscription,AllowAnonymousUsersToJoinMeeting,AutoAdmittedUsers,MeetingChatEnabledType,NewMeetingRecordingExpirationDays
$path = Join-Path $out "meeting_policies.csv"; Export-CraCsv $meetingPolicies $path; $files.Add($path)

$meetingPolicyEvidence = $meetingPolicies | Select-Object Identity,AllowCloudRecording,AllowTranscription,AllowAnonymousUsersToJoinMeeting,AutoAdmittedUsers,MeetingChatEnabledType,NewMeetingRecordingExpirationDays,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "AllowCloudRecording=$($_.AllowCloudRecording);AllowTranscription=$($_.AllowTranscription);MeetingChatEnabledType=$($_.MeetingChatEnabledType)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsMeetingPolicy" }}
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
  $channelEmailEvidence = $clientConfig | Select-Object Identity,AllowEmailIntoChannel,@{Name="RestrictedSenderCount";Expression={ @($_.RestrictedSenderList).Count }},@{Name="status";Expression={ if ($_.AllowEmailIntoChannel -eq $false -or (@($_.RestrictedSenderList).Count -gt 0)) { "pass" } else { "fail" } }},@{Name="value";Expression={ "AllowEmailIntoChannel=$($_.AllowEmailIntoChannel);RestrictedSenderCount=$(@($_.RestrictedSenderList).Count)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsClientConfiguration" }}
} catch {
  $guestAccessEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTeamsClientConfiguration" })
  $fileStorageEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTeamsClientConfiguration" })
  $channelEmailEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTeamsClientConfiguration" })
}
Export-CraExpectedCsv $guestAccessEvidence $out "guest_access_enabled_disabled.csv" $files "Get-CsTeamsClientConfiguration"
Export-CraExpectedCsv $fileStorageEvidence $out "teams_file_storage_option.csv" $files "Get-CsTeamsClientConfiguration"
Export-CraExpectedCsv $channelEmailEvidence $out "teams_channel_email_addresses.csv" $files "Get-CsTeamsClientConfiguration"

try {
  $appPolicy = Get-CsTeamsAppPermissionPolicy | Select-Object Identity,GlobalCatalogAppsType,PrivateCatalogAppsType
  $thirdPartyEvidence = $appPolicy | Select-Object Identity,GlobalCatalogAppsType,PrivateCatalogAppsType,@{Name="status";Expression={ if ($_.GlobalCatalogAppsType -eq "BlockedAppList") { "pass" } else { "fail" } }},@{Name="value";Expression={ "GlobalCatalogAppsType=$($_.GlobalCatalogAppsType);PrivateCatalogAppsType=$($_.PrivateCatalogAppsType)" }},@{Name="evidence_source";Expression={ "Get-CsTeamsAppPermissionPolicy" }}
} catch {
  $thirdPartyEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-CsTeamsAppPermissionPolicy" })
}
Export-CraExpectedCsv $thirdPartyEvidence $out "third_party_apps_allowed.csv" $files "Get-CsTeamsAppPermissionPolicy"

try {
  $copilotApps = @(Get-TeamsApp -DisplayName "Copilot" -ErrorAction Stop)
  $setupPolicies = @(Get-CsTeamsAppSetupPolicy -ErrorAction Stop | Select-Object Identity,AllowUserPinning,PinnedAppBarApps,PinnedMessageBarApps,AppPresetList)
  $permissionPolicies = @(Get-CsTeamsAppPermissionPolicy -ErrorAction Stop | Select-Object Identity,DefaultCatalogAppsType,GlobalCatalogAppsType,PrivateCatalogAppsType,DefaultCatalogApps,GlobalCatalogApps,PrivateCatalogApps)
  $copilotEvidence = foreach ($policy in $permissionPolicies) {
    $allowsMicrosoftApps = $policy.DefaultCatalogAppsType -ne "AllowedAppList" -or @($policy.DefaultCatalogApps).Count -gt 0
    [pscustomobject]@{
      Identity = $policy.Identity
      CopilotAppMatches = @($copilotApps).Count
      DefaultCatalogAppsType = $policy.DefaultCatalogAppsType
      GlobalCatalogAppsType = $policy.GlobalCatalogAppsType
      PrivateCatalogAppsType = $policy.PrivateCatalogAppsType
      SetupPolicyCount = @($setupPolicies).Count
      AllowsMicrosoftApps = $allowsMicrosoftApps
      status = if (@($copilotApps).Count -gt 0 -and $allowsMicrosoftApps) { "pass" } else { "fail" }
      value = "CopilotAppMatches=$(@($copilotApps).Count);DefaultCatalogAppsType=$($policy.DefaultCatalogAppsType);AllowsMicrosoftApps=$allowsMicrosoftApps"
      evidence_source = "Get-TeamsApp / Get-CsTeamsAppPermissionPolicy / Get-CsTeamsAppSetupPolicy"
    }
  }
  if (-not $copilotEvidence -or @($copilotEvidence).Count -eq 0) {
    $copilotEvidence = @([pscustomobject]@{
      Identity = ""
      CopilotAppMatches = @($copilotApps).Count
      DefaultCatalogAppsType = ""
      GlobalCatalogAppsType = ""
      PrivateCatalogAppsType = ""
      SetupPolicyCount = @($setupPolicies).Count
      AllowsMicrosoftApps = $false
      status = if (@($copilotApps).Count -gt 0) { "pass" } else { "fail" }
      value = "CopilotAppMatches=$(@($copilotApps).Count);No app permission policies returned"
      evidence_source = "Get-TeamsApp / Get-CsTeamsAppPermissionPolicy / Get-CsTeamsAppSetupPolicy"
    })
  }
} catch {
  $copilotEvidence = @([pscustomobject]@{
    Identity = ""
    CopilotAppMatches = ""
    DefaultCatalogAppsType = ""
    GlobalCatalogAppsType = ""
    PrivateCatalogAppsType = ""
    SetupPolicyCount = ""
    AllowsMicrosoftApps = ""
    status = "not_collected"
    value = $_.Exception.Message
    evidence_source = "Get-TeamsApp / Get-CsTeamsAppPermissionPolicy / Get-CsTeamsAppSetupPolicy"
  })
}
Export-CraExpectedCsv $copilotEvidence $out "copilot_integration_enabled.csv" $files "Get-TeamsApp / Get-CsTeamsAppPermissionPolicy / Get-CsTeamsAppSetupPolicy"

Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray()
