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
Assert-CraModule "ExchangeOnlineManagement"
$collector = $CollectorJson | ConvertFrom-Json

$out = Initialize-CraArtifactDirectory -OutputRoot $OutputRoot -AssessmentId $AssessmentId -Domain "purview"
$files = New-Object System.Collections.Generic.List[string]

Connect-CraPurview -Collector $collector

$dlp = Get-DlpCompliancePolicy | Select-Object Name,Mode,Enabled,Workload,ExchangeLocation,SharePointLocation,OneDriveLocation,TeamsLocation
$path = Join-Path $out "dlp_policies.csv"; Export-CraCsv $dlp $path; $files.Add($path)
$dlpEvidence = $dlp | ForEach-Object {
  [pscustomobject]@{
    Name = $_.Name
    Mode = $_.Mode
    Enabled = $_.Enabled
    Workload = ($_.Workload -join ";")
    status = if ($_.Enabled -eq $true) { "pass" } else { "fail" }
    value = "Enabled=$($_.Enabled);Mode=$($_.Mode)"
    evidence_source = "Get-DlpCompliancePolicy"
  }
}
$path = Join-Path $out "dlp_rules_configured.csv"; Export-CraCsv $dlpEvidence $path; $files.Add($path)

$retention = Get-RetentionCompliancePolicy | Select-Object Name,Enabled,Mode,ExchangeLocation,SharePointLocation,OneDriveLocation,TeamsLocation
$path = Join-Path $out "retention_policies.csv"; Export-CraCsv $retention $path; $files.Add($path)
$retentionRules = Get-RetentionComplianceRule | Select-Object Name,Policy,RetentionDuration,RetentionComplianceAction,ExpirationDateOption
$retentionEvidence = $retentionRules | ForEach-Object {
  [pscustomobject]@{
    Name = $_.Name
    Policy = $_.Policy
    RetentionDuration = $_.RetentionDuration
    RetentionComplianceAction = $_.RetentionComplianceAction
    ExpirationDateOption = $_.ExpirationDateOption
    status = if ($_.RetentionDuration) { "pass" } else { "fail" }
    value = "RetentionDuration=$($_.RetentionDuration);Action=$($_.RetentionComplianceAction)"
    evidence_source = "Get-RetentionComplianceRule"
  }
}
if (-not $retentionEvidence -or $retentionEvidence.Count -eq 0) {
  $retentionEvidence = @([pscustomobject]@{
    Name = ""
    Policy = ""
    RetentionDuration = ""
    RetentionComplianceAction = ""
    ExpirationDateOption = ""
    status = "fail"
    value = "No retention compliance rules returned"
    evidence_source = "Get-RetentionComplianceRule"
  })
}
$path = Join-Path $out "audit_log_retention_duration.csv"; Export-CraCsv $retentionEvidence $path; $files.Add($path)

$auditLogRetentionPolicies = Get-UnifiedAuditLogRetentionPolicy | Sort-Object -Property Priority -Descending | Select-Object Priority,Name,Description,RecordTypes,Operations,UserIds,RetentionDuration
$auditLogRetentionEvidence = @()

if ($auditLogRetentionPolicies -and $auditLogRetentionPolicies.Count -gt 0) {
  $auditLogRetentionEvidence = $auditLogRetentionPolicies | ForEach-Object {
    [pscustomobject]@{
      Priority = $_.Priority
      Name = $_.Name
      Description = $_.Description
      RecordTypes = ($_.RecordTypes -join ";")
      Operations = ($_.Operations -join ";")
      UserIds = ($_.UserIds -join ";")
      RetentionDuration = $_.RetentionDuration
      status = "pass"
      value = "Audit log retention policy configured: $($_.RetentionDuration)"
      evidence_source = "Get-UnifiedAuditLogRetentionPolicy"
    }
  }
} else {
  $auditLogRetentionEvidence = @([pscustomobject]@{
    Priority = ""
    Name = ""
    Description = ""
    RecordTypes = ""
    Operations = ""
    UserIds = ""
    RetentionDuration = ""
    status = "fail"
    value = "No audit log retention policy configured"
    evidence_source = "Get-UnifiedAuditLogRetentionPolicy"
  })
}
$path = Join-Path $out "unified_audit_log_retention_policy.csv"; Export-CraCsv $auditLogRetentionEvidence $path; $files.Add($path)

$audit = Get-AdminAuditLogConfig | Select-Object UnifiedAuditLogIngestionEnabled,AdminAuditLogEnabled,TestCmdletLoggingEnabled
$path = Join-Path $out "audit_logging.csv"; Export-CraCsv $audit $path; $files.Add($path)
$auditEvidence = $audit | Select-Object UnifiedAuditLogIngestionEnabled,AdminAuditLogEnabled,TestCmdletLoggingEnabled,@{Name="status";Expression={ if ($_.UnifiedAuditLogIngestionEnabled -eq $true -or $_.AdminAuditLogEnabled -eq $true) { "pass" } else { "fail" } }},@{Name="value";Expression={ "UnifiedAuditLogIngestionEnabled=$($_.UnifiedAuditLogIngestionEnabled);AdminAuditLogEnabled=$($_.AdminAuditLogEnabled)" }},@{Name="evidence_source";Expression={ "Get-AdminAuditLogConfig" }}
Export-CraExpectedCsv $auditEvidence $out "audit_logs_enabled.csv" $files "Get-AdminAuditLogConfig"

$labels = Get-Label | Select-Object Name,DisplayName,ContentType,Disabled
$labelEvidence = $labels | ForEach-Object {
  [pscustomobject]@{
    Name = $_.Name
    DisplayName = $_.DisplayName
    ContentType = ($_.ContentType -join ";")
    Disabled = $_.Disabled
    status = if ($_.Disabled -eq $false) { "pass" } else { "fail" }
    value = "Disabled=$($_.Disabled);ContentType=$($_.ContentType -join ';')"
    evidence_source = "Get-Label"
  }
}
if (-not $labelEvidence -or $labelEvidence.Count -eq 0) {
  $labelEvidence = @([pscustomobject]@{
    Name = ""
    DisplayName = ""
    ContentType = ""
    Disabled = ""
    status = "fail"
    value = "No sensitivity labels returned"
    evidence_source = "Get-Label"
  })
}
$path = Join-Path $out "information_protection_labels_applied.csv"; Export-CraCsv $labelEvidence $path; $files.Add($path)
$path = Join-Path $out "sensitivity_labels_configured_and_applied.csv"; Export-CraCsv $labelEvidence $path; $files.Add($path)
$path = Join-Path $out "sensitivity_labels_are_applied.csv"; Export-CraCsv $labelEvidence $path; $files.Add($path)
Export-CraExpectedCsv $labelEvidence $out "sensitivity_labels_applied_to_teams.csv" $files "Get-Label"

$meetingRecordingEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "Meeting recording retention is a Teams meeting policy setting and must be collected through MicrosoftTeams Get-CsTeamsMeetingPolicy."
  evidence_source = "Get-CsTeamsMeetingPolicy"
})
Export-CraExpectedCsv $meetingRecordingEvidence $out "meeting_recording_retention_policies.csv" $files "Get-CsTeamsMeetingPolicy"

$siteKeywordEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "Sensitivity keyword site inventory requires SharePoint site enumeration plus label/keyword policy matching."
  evidence_source = "Get-PnPTenantSite / Get-Label"
})
Export-CraExpectedCsv $siteKeywordEvidence $out "getting_all_sites_with_sensitivity_keywords_on_a_tenant.csv" $files "Get-PnPTenantSite / Get-Label"

$secureScoreEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "Secure Score requires Microsoft Graph security secureScores endpoint."
  evidence_source = "GET /security/secureScores"
})
Export-CraExpectedCsv $secureScoreEvidence $out "secure_score_percentage.csv" $files "GET /security/secureScores"

$complianceScoreEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "Compliance Score overview requires Microsoft Purview Compliance Manager export; no stable app-only endpoint is wired in this script."
  evidence_source = "Microsoft Purview Compliance Manager"
})
Export-CraExpectedCsv $complianceScoreEvidence $out "compliance_score_overview.csv" $files "Microsoft Purview Compliance Manager"

try {
  Connect-CraExchange -Collector $collector
  $lockbox = Get-OrganizationConfig | Select-Object Identity,CustomerLockBoxEnabled
  $lockboxEvidence = $lockbox | ForEach-Object {
    [pscustomobject]@{
      Identity = $_.Identity
      CustomerLockBoxEnabled = $_.CustomerLockBoxEnabled
      status = if ($_.CustomerLockBoxEnabled -eq $true) { "pass" } else { "fail" }
      value = "CustomerLockBoxEnabled=$($_.CustomerLockBoxEnabled)"
      evidence_source = "Get-OrganizationConfig"
    }
  }
} catch {
  $lockboxEvidence = @([pscustomobject]@{
    Identity = ""
    CustomerLockBoxEnabled = ""
    status = "not_collected"
    value = "Customer Lockbox query failed: $($_.Exception.Message)"
    evidence_source = "Get-OrganizationConfig"
  })
}
$path = Join-Path $out "customer_lockbox.csv"; Export-CraCsv $lockboxEvidence $path; $files.Add($path)

Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray()
