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
$collector = $CollectorJson | ConvertFrom-Json

$out = Initialize-CraArtifactDirectory -OutputRoot $OutputRoot -AssessmentId $AssessmentId -Domain "onedrive"
$files = New-Object System.Collections.Generic.List[string]

Connect-CraGraph -TenantId $TenantId -Scopes @("Reports.Read.All","Files.Read.All","Sites.Read.All") -Collector $collector | Out-Null

$period = "D180"
$usagePath = Join-Path $out "onedrive_usage.csv"
Get-MgReportOneDriveUsageAccountDetail -Period $period -OutFile $usagePath -ErrorAction Stop
if (-not (Test-Path $usagePath)) { throw "OneDrive usage CSV was not generated." }
$files.Add($usagePath)

$activityPath = Join-Path $out "onedrive_activity.csv"
Get-MgReportOneDriveActivityUserDetail -Period $period -OutFile $activityPath -ErrorAction Stop
if (-not (Test-Path $activityPath)) { throw "OneDrive activity CSV was not generated." }
$files.Add($activityPath)

$activityRows = Import-Csv $activityPath
$activeUserEvidence = $activityRows | Select-Object *,@{Name="status";Expression={ if ($_.'Last Activity Date') { "pass" } else { "fail" } }},@{Name="value";Expression={ "LastActivityDate=$($_.'Last Activity Date')" }},@{Name="evidence_source";Expression={ "Get-MgReportOneDriveActivityUserDetail" }}
Export-CraExpectedCsv $activeUserEvidence $out "total_active_users_on_onedrive.csv" $files "Get-MgReportOneDriveActivityUserDetail"

$retentionRows = @()
try {
  if (Get-Command Get-SPOTenant -ErrorAction SilentlyContinue) {
    $tenantSettings = Get-SPOTenant
    $retentionDays = $tenantSettings.OrphanedPersonalSitesRetentionPeriod
    $retentionRows = @([pscustomobject]@{
      OrphanedPersonalSitesRetentionPeriod = $retentionDays
      status = if ($retentionDays -and [int]$retentionDays -gt 0) { "pass" } else { "fail" }
      value = "OrphanedPersonalSitesRetentionPeriod=$retentionDays"
      evidence_source = "Get-SPOTenant"
    })
  }
} catch {
  $retentionRows = @([pscustomobject]@{
    OrphanedPersonalSitesRetentionPeriod = ""
    status = "not_collected"
    value = $_.Exception.Message
    evidence_source = "Get-SPOTenant"
  })
}
if (-not $retentionRows -or @($retentionRows).Count -eq 0) {
  $retentionRows = @([pscustomobject]@{
    OrphanedPersonalSitesRetentionPeriod = ""
    status = "not_collected"
    value = "SharePoint Online Management Shell is required to read deleted user's OneDrive retention setting."
    evidence_source = "Get-SPOTenant"
  })
}
$retentionPath = Join-Path $out "days_to_retain_a_deleted_user_s_onedrive.csv"
Export-CraCsv $retentionRows $retentionPath
$files.Add($retentionPath)

$externalSharingRows = @([pscustomobject]@{
  status = "not_collected"
  value = "OneDrive external sharing settings require SharePoint tenant settings via Get-SPOTenant or Graph SharePoint admin settings."
  evidence_source = "Get-SPOTenant"
})
$guestExpiryRows = @([pscustomobject]@{
  status = "not_collected"
  value = "SharePoint and OneDrive guest access expiry requires SharePoint tenant settings via Get-SPOTenant or Graph SharePoint admin settings."
  evidence_source = "Get-SPOTenant"
})
Export-CraExpectedCsv $externalSharingRows $out "external_sharing_settings.csv" $files "Get-SPOTenant"
Export-CraExpectedCsv $guestExpiryRows $out "sharepoint_and_onedrive_guest_access_expiry.csv" $files "Get-SPOTenant"

Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray()
