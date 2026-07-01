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
Assert-CraModule "PnP.PowerShell"

$collector = $CollectorJson | ConvertFrom-Json
$out = Initialize-CraArtifactDirectory -OutputRoot $OutputRoot -AssessmentId $AssessmentId -Domain "sharepoint"
$files = New-Object System.Collections.Generic.List[string]

if (-not $collector.admin_url) {
  $outputFile = if ($collector.output_file) { [string]$collector.output_file } else { "$ParameterKey.csv" }
  $manual = @([pscustomobject]@{
    status = "not_collected"
    value = "SharePoint admin URL is required for tenant-level SharePoint validation."
    expected = "Configure collector admin_url, for example https://<tenant>-admin.sharepoint.com."
    evidence_source = "collector_manifest.admin_url"
  })
  $path = Join-Path $out $outputFile
  Export-CraCsv $manual $path
  $files.Add($path)
  Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray() -Warnings @("SharePoint admin_url missing; manual validation required.")
  return
}

Connect-CraGraph -TenantId $TenantId -Scopes @("Reports.Read.All","Sites.Read.All","Directory.Read.All") -Collector $collector | Out-Null
Connect-CraPnP -Url $collector.admin_url -Collector $collector

$sites = Get-PnPTenantSite -Detailed |
  Select-Object Url,Title,Owner,Template,SharingCapability,StorageUsageCurrent,LastContentModifiedDate,LockState,SensitivityLabel
$path = Join-Path $out "sharepoint_sites.csv"; Export-CraCsv $sites $path; $files.Add($path)

$activeSitesEvidence = $sites | Select-Object Url,Title,Owner,Template,LastContentModifiedDate,LockState,@{Name="status";Expression={ if ($_.LockState -eq "Unlock") { "pass" } else { "fail" } }},@{Name="value";Expression={ "LockState=$($_.LockState);LastContentModifiedDate=$($_.LastContentModifiedDate)" }},@{Name="evidence_source";Expression={ "Get-PnPTenantSite" }}
Export-CraExpectedCsv $activeSitesEvidence $out "active_sites_count.csv" $files "Get-PnPTenantSite"

$activeUsersEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "SharePoint active user counts require Microsoft Graph reports endpoint getSharePointActivityUserDetail or admin usage report export."
  evidence_source = "GET /reports/getSharePointActivityUserDetail"
})
Export-CraExpectedCsv $activeUsersEvidence $out "active_users_on_sharepoint.csv" $files "GET /reports/getSharePointActivityUserDetail"

$storageEvidence = $sites | Select-Object Url,Title,StorageUsageCurrent,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "StorageUsageCurrent=$($_.StorageUsageCurrent)" }},@{Name="evidence_source";Expression={ "Get-PnPTenantSite" }}
Export-CraExpectedCsv $storageEvidence $out "storage_quota_consumption.csv" $files "Get-PnPTenantSite"

$external = $sites | Select-Object Url,Title,SharingCapability,Owner
$path = Join-Path $out "external_sharing.csv"; Export-CraCsv $external $path; $files.Add($path)
$externalEvidence = $sites | ForEach-Object {
  [pscustomobject]@{
    Url = $_.Url
    Title = $_.Title
    SharingCapability = $_.SharingCapability
    status = if ($_.SharingCapability -match "ExternalUserAndGuestSharing|Anonymous") { "fail" } else { "pass" }
    value = "SharingCapability=$($_.SharingCapability)"
    evidence_source = "Get-PnPTenantSite"
  }
}
$path = Join-Path $out "external_sharing_settings.csv"; Export-CraCsv $externalEvidence $path; $files.Add($path)

$inactiveThreshold = (Get-Date).AddDays(-90)
$inactive = $sites | Where-Object { $_.LastContentModifiedDate -and $_.LastContentModifiedDate -lt $inactiveThreshold } |
  Select-Object Url,Title,Owner,LastContentModifiedDate,StorageUsageCurrent
$path = Join-Path $out "inactive_sites.csv"; Export-CraCsv $inactive $path; $files.Add($path)
$inactivePolicy = @([pscustomobject]@{
  InactiveSiteCount = @($inactive).Count
  TotalSiteCount = @($sites).Count
  PolicySignal = "LastContentModifiedDate older than 90 days"
  status = if (@($inactive).Count -eq 0) { "pass" } else { "fail" }
  value = "InactiveSites=$(@($inactive).Count);TotalSites=$(@($sites).Count)"
  evidence_source = "Get-PnPTenantSite"
})
$path = Join-Path $out "inactive_site_policies.csv"; Export-CraCsv $inactivePolicy $path; $files.Add($path)

$siteOwnership = foreach ($site in $sites) {
  [pscustomobject]@{
    Url = $site.Url
    Title = $site.Title
    Owner = $site.Owner
    status = if ([string]::IsNullOrWhiteSpace($site.Owner)) { "fail" } else { "pass" }
    value = "Owner=$($site.Owner)"
    evidence_source = "Get-PnPTenantSite"
  }
}
$path = Join-Path $out "site_ownership_policies.csv"; Export-CraCsv $siteOwnership $path; $files.Add($path)

$sharingLinks = foreach ($site in $sites) {
  [pscustomobject]@{
    Url = $site.Url
    Title = $site.Title
    SharingCapability = $site.SharingCapability
    status = if ($site.SharingCapability -match "ExternalUserAndGuestSharing|Anonymous") { "fail" } else { "pass" }
    value = "SharingCapability=$($site.SharingCapability)"
    EvidenceSource = "Get-PnPTenantSite"
  }
}
$path = Join-Path $out "sharing_links.csv"; Export-CraCsv $sharingLinks $path; $files.Add($path)
$path = Join-Path $out "checking_sharing_permissions_for_each_sites_on_a_tenant.csv"; Export-CraCsv $sharingLinks $path; $files.Add($path)

$keywordRows = foreach ($site in $sites) {
  $haystack = "$($site.Url) $($site.Title)".ToLowerInvariant()
  $matched = @("confidential","sensitive","restricted","secret","private") | Where-Object { $haystack.Contains($_) }
  [pscustomobject]@{
    Url = $site.Url
    Title = $site.Title
    MatchedKeywords = ($matched -join ";")
    SensitivityLabel = $site.SensitivityLabel
    status = if ($matched.Count -gt 0 -or $site.SensitivityLabel) { "pass" } else { "fail" }
    value = "MatchedKeywords=$($matched -join ';');SensitivityLabel=$($site.SensitivityLabel)"
    evidence_source = "Get-PnPTenantSite"
  }
}
$path = Join-Path $out "getting_all_sites_with_sensitivity_keywords_on_a_tenant.csv"; Export-CraCsv $keywordRows $path; $files.Add($path)

try {
  $tenantSettings = Get-PnPTenant
  $modernAuth = @([pscustomobject]@{
    LegacyAuthProtocolsEnabled = $tenantSettings.LegacyAuthProtocolsEnabled
    status = if ($tenantSettings.LegacyAuthProtocolsEnabled -eq $false) { "pass" } else { "fail" }
    value = "LegacyAuthProtocolsEnabled=$($tenantSettings.LegacyAuthProtocolsEnabled)"
    evidence_source = "Get-PnPTenant"
  })
  $sharingSettings = @([pscustomobject]@{
    SharingCapability = $tenantSettings.SharingCapability
    OneDriveSharingCapability = $tenantSettings.OneDriveSharingCapability
    PreventExternalUsersFromResharing = $tenantSettings.PreventExternalUsersFromResharing
    status = if ($tenantSettings.PreventExternalUsersFromResharing -eq $true) { "pass" } else { "fail" }
    value = "SharingCapability=$($tenantSettings.SharingCapability);PreventExternalUsersFromResharing=$($tenantSettings.PreventExternalUsersFromResharing)"
    evidence_source = "Get-PnPTenant"
  })
  # Guest Access Expiry (E7): ExternalUserExpirationRequired must be True.
  $guestExpiry = @([pscustomobject]@{
    RequireAnonymousLinksExpireInDays = $tenantSettings.RequireAnonymousLinksExpireInDays
    ExternalUserExpirationRequired = $tenantSettings.ExternalUserExpirationRequired
    ExternalUserExpireInDays = $tenantSettings.ExternalUserExpireInDays
    status = if ($tenantSettings.ExternalUserExpirationRequired -eq $true) { "pass" } else { "fail" }
    value = "ExternalUserExpirationRequired=$($tenantSettings.ExternalUserExpirationRequired);ExternalUserExpireInDays=$($tenantSettings.ExternalUserExpireInDays)"
    evidence_source = "Get-PnPTenant"
  })
  # Expiration Policy for Anyone Links (E5): RequireAnonymousLinksExpireInDays must be > 0 (-1 means not set).
  $anyoneExpiry = @([pscustomobject]@{
    RequireAnonymousLinksExpireInDays = $tenantSettings.RequireAnonymousLinksExpireInDays
    status = if ($tenantSettings.RequireAnonymousLinksExpireInDays -gt 0) { "pass" } else { "fail" }
    value = "RequireAnonymousLinksExpireInDays=$($tenantSettings.RequireAnonymousLinksExpireInDays)"
    evidence_source = "Get-PnPTenant"
  })
  # Permissions for Anyone Links (E6): neither file nor folder anonymous links may allow Edit.
  $anyonePermissions = @([pscustomobject]@{
    FileAnonymousLinkType = $tenantSettings.FileAnonymousLinkType
    FolderAnonymousLinkType = $tenantSettings.FolderAnonymousLinkType
    status = if ($tenantSettings.FileAnonymousLinkType -ne "Edit" -and $tenantSettings.FolderAnonymousLinkType -ne "Edit") { "pass" } else { "fail" }
    value = "File=$($tenantSettings.FileAnonymousLinkType);Folder=$($tenantSettings.FolderAnonymousLinkType)"
    evidence_source = "Get-PnPTenant"
  })
} catch {
  $modernAuth = @([pscustomobject]@{ LegacyAuthProtocolsEnabled = ""; status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-PnPTenant" })
  $sharingSettings = @([pscustomobject]@{ SharingCapability = ""; OneDriveSharingCapability = ""; PreventExternalUsersFromResharing = ""; status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-PnPTenant" })
  $guestExpiry = @([pscustomobject]@{ RequireAnonymousLinksExpireInDays = ""; ExternalUserExpirationRequired = ""; ExternalUserExpireInDays = ""; status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-PnPTenant" })
  $anyoneExpiry = @([pscustomobject]@{ RequireAnonymousLinksExpireInDays = ""; status = "fail"; value = $_.Exception.Message; evidence_source = "Get-PnPTenant" })
  $anyonePermissions = @([pscustomobject]@{ FileAnonymousLinkType = ""; FolderAnonymousLinkType = ""; status = "fail"; value = $_.Exception.Message; evidence_source = "Get-PnPTenant" })
}
$path = Join-Path $out "sharepoint_modern_authentication.csv"; Export-CraCsv $modernAuth $path; $files.Add($path)
$path = Join-Path $out "sharing_settings_external_internal.csv"; Export-CraCsv $sharingSettings $path; $files.Add($path)
$path = Join-Path $out "sharepoint_and_onedrive_guest_access_expiry.csv"; Export-CraCsv $guestExpiry $path; $files.Add($path)
$path = Join-Path $out "expiration_policy_for_anyone_links.csv"; Export-CraCsv $anyoneExpiry $path; $files.Add($path)
$path = Join-Path $out "permission_setting_for_anyone_links.csv"; Export-CraCsv $anyonePermissions $path; $files.Add($path)

Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray()
