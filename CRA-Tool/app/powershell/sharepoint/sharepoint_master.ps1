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

# Export a CSV only when there is at least one row, so an empty/failed site enumeration
# never binds $null to Export-Csv (which aborts the whole collector).
function Add-CraCsvIfAny {
  param($Data, [string]$Name, [string]$OutDir, $FileList)
  $rows = @($Data)
  if ($rows.Count -gt 0) {
    $p = Join-Path $OutDir $Name
    Export-CraCsv $rows $p
    $FileList.Add($p) | Out-Null
  }
}

# admin_url is tenant-specific and ships null in the manifest; the Python runtime derives
# it per tenant and passes it via CRA_SHAREPOINT_ADMIN_URL. Prefer the collector value,
# then the env var. Only if neither is available do we early-return.
$adminUrl = if ($collector.admin_url) { [string]$collector.admin_url }
            elseif ($env:CRA_SHAREPOINT_ADMIN_URL) { [string]$env:CRA_SHAREPOINT_ADMIN_URL }
            else { $null }
if (-not $adminUrl) {
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
Connect-CraPnP -Url $adminUrl -Collector $collector

# =====================================================================================
# Tenant settings (Get-PnPTenant) — the ONLY data the PowerShell-routed SharePoint
# parameters need. Computed and emitted FIRST so a slow/failing site enumeration below
# can never prevent these findings. Get-PnPTenant returns anonymous link types either as
# the AnonymousLinkType enum ("None"/"View"/"Edit") or its numeric value (0/1/2).
# =====================================================================================
function Convert-CraAnonLinkType {
  param($Value)
  switch -Regex ("$Value".Trim().ToLowerInvariant()) {
    '^(2|edit)$' { return "edit" }
    '^(1|view)$' { return "view" }
    '^(0|none)$' { return "none" }
    default      { return "$Value".Trim().ToLowerInvariant() }
  }
}

# parameter_key -> @{ status; message; severity }; emitted directly to the contract so the
# runtime persists the manual evaluated_value text (not the generic CSV placeholder).
$findingMap = @{}
try {
  $tenantSettings = Get-PnPTenant
  $modernAuth = @([pscustomobject]@{
    LegacyAuthProtocolsEnabled = $tenantSettings.LegacyAuthProtocolsEnabled
    status = if ($tenantSettings.LegacyAuthProtocolsEnabled -eq $false) { "pass" } else { "fail" }
    value = "LegacyAuthProtocolsEnabled=$($tenantSettings.LegacyAuthProtocolsEnabled)"
    evidence_source = "Get-PnPTenant"
  })
  # SharingCapability only (PreventExternalUsersFromResharing is a DIFFERENT control and
  # must not drive this parameter).
  $sharingSettings = @([pscustomobject]@{
    SharingCapability = $tenantSettings.SharingCapability
    OneDriveSharingCapability = $tenantSettings.OneDriveSharingCapability
    status = if ($tenantSettings.SharingCapability -match "ExternalUserAndGuestSharing|Anonymous") { "fail" } else { "pass" }
    value = "SharingCapability=$($tenantSettings.SharingCapability)"
    evidence_source = "Get-PnPTenant"
  })

  # E7 Guest Access Expiry: ExternalUserExpirationRequired must be True.
  $guestExpiryEnabled = ($tenantSettings.ExternalUserExpirationRequired -eq $true)
  $guestExpiry = @([pscustomobject]@{
    ExternalUserExpirationRequired = $tenantSettings.ExternalUserExpirationRequired
    ExternalUserExpireInDays = $tenantSettings.ExternalUserExpireInDays
    status = if ($guestExpiryEnabled) { "pass" } else { "fail" }
    value = "ExternalUserExpirationRequired=$($tenantSettings.ExternalUserExpirationRequired);ExternalUserExpireInDays=$($tenantSettings.ExternalUserExpireInDays)"
    evidence_source = "Get-PnPTenant"
  })
  $findingMap["sharepoint_and_onedrive_guest_access_expiry"] = @{
    status = if ($guestExpiryEnabled) { "pass" } else { "fail" }
    message = if ($guestExpiryEnabled) { "Enabled and set to $($tenantSettings.ExternalUserExpireInDays) days" } else { "Disabled" }
    severity = "critical"
  }

  # E5 Expiration Policy for Anyone Links: RequireAnonymousLinksExpireInDays must be > 0 (-1 = not set).
  $anyoneExpiryDays = $tenantSettings.RequireAnonymousLinksExpireInDays
  $anyoneExpiryEnabled = ($anyoneExpiryDays -gt 0)
  $anyoneExpiry = @([pscustomobject]@{
    RequireAnonymousLinksExpireInDays = $anyoneExpiryDays
    status = if ($anyoneExpiryEnabled) { "pass" } else { "fail" }
    value = "RequireAnonymousLinksExpireInDays=$anyoneExpiryDays"
    evidence_source = "Get-PnPTenant"
  })
  $findingMap["expiration_policy_for_anyone_links"] = @{
    status = if ($anyoneExpiryEnabled) { "pass" } else { "fail" }
    message = if ($anyoneExpiryEnabled) { "Anyone links expire in $anyoneExpiryDays days" } else { "No expiration policy set" }
    severity = "high"
  }

  # E6 Permissions for Anyone Links: neither file nor folder anonymous links may allow Edit.
  $fileLink = Convert-CraAnonLinkType $tenantSettings.FileAnonymousLinkType
  $folderLink = Convert-CraAnonLinkType $tenantSettings.FolderAnonymousLinkType
  $fileEdit = ($fileLink -eq "edit")
  $folderEdit = ($folderLink -eq "edit")
  $anyonePermissions = @([pscustomobject]@{
    FileAnonymousLinkType = $tenantSettings.FileAnonymousLinkType
    FolderAnonymousLinkType = $tenantSettings.FolderAnonymousLinkType
    status = if (-not $fileEdit -and -not $folderEdit) { "pass" } else { "fail" }
    value = "File=$fileLink;Folder=$folderLink"
    evidence_source = "Get-PnPTenant"
  })
  if ($fileEdit -and $folderEdit) {
    $permStatus = "fail"; $permMsg = "Set to edit for both files and folders"
  } elseif ($fileEdit) {
    $permStatus = "fail"; $permMsg = "Set to edit for files"
  } elseif ($folderEdit) {
    $permStatus = "fail"; $permMsg = "Set to edit for folders"
  } else {
    $permStatus = "pass"; $permMsg = "Anyone links restricted to view-only (files: $fileLink, folders: $folderLink)"
  }
  $findingMap["permission_setting_for_anyone_links"] = @{
    status = $permStatus
    message = $permMsg
    severity = "critical"
  }
} catch {
  $err = $_.Exception.Message
  $modernAuth = @([pscustomobject]@{ LegacyAuthProtocolsEnabled = ""; status = "not_collected"; value = $err; evidence_source = "Get-PnPTenant" })
  $sharingSettings = @([pscustomobject]@{ SharingCapability = ""; OneDriveSharingCapability = ""; status = "not_collected"; value = $err; evidence_source = "Get-PnPTenant" })
  $guestExpiry = @([pscustomobject]@{ ExternalUserExpirationRequired = ""; ExternalUserExpireInDays = ""; status = "not_collected"; value = $err; evidence_source = "Get-PnPTenant" })
  $anyoneExpiry = @([pscustomobject]@{ RequireAnonymousLinksExpireInDays = ""; status = "not_collected"; value = $err; evidence_source = "Get-PnPTenant" })
  $anyonePermissions = @([pscustomobject]@{ FileAnonymousLinkType = ""; FolderAnonymousLinkType = ""; status = "not_collected"; value = $err; evidence_source = "Get-PnPTenant" })
  foreach ($k in @("sharepoint_and_onedrive_guest_access_expiry","expiration_policy_for_anyone_links","permission_setting_for_anyone_links")) {
    $findingMap[$k] = @{ status = "fail"; message = "SharePoint PnP could not verify this setting: $err"; severity = "high" }
  }
}
$path = Join-Path $out "sharepoint_modern_authentication.csv"; Export-CraCsv $modernAuth $path; $files.Add($path)
$path = Join-Path $out "sharing_settings_external_internal.csv"; Export-CraCsv $sharingSettings $path; $files.Add($path)
$path = Join-Path $out "sharepoint_and_onedrive_guest_access_expiry.csv"; Export-CraCsv $guestExpiry $path; $files.Add($path)
$path = Join-Path $out "expiration_policy_for_anyone_links.csv"; Export-CraCsv $anyoneExpiry $path; $files.Add($path)
$path = Join-Path $out "permission_setting_for_anyone_links.csv"; Export-CraCsv $anyonePermissions $path; $files.Add($path)

# Fast path: these parameters are fully answered by Get-PnPTenant. Emit the real finding
# and stop BEFORE the (unrelated, potentially slow/failing) per-site enumeration below.
if ($findingMap.ContainsKey($ParameterKey)) {
  $f = $findingMap[$ParameterKey]
  Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray() -FindingStatus $f.status -FindingMessage $f.message -FindingSeverity $f.severity
  return
}

# =====================================================================================
# Site-level evidence (evidence CSVs only; the site-based parameters are evaluated via
# Microsoft Graph, so no parameter is scored from this section). Wrapped + null-safe so a
# failure never aborts the collector.
# =====================================================================================
try {
  $sites = @(Get-PnPTenantSite -Detailed |
    Select-Object Url,Title,Owner,Template,SharingCapability,StorageUsageCurrent,LastContentModifiedDate,LockState,SensitivityLabel)
} catch {
  $sites = @()
}
Add-CraCsvIfAny $sites "sharepoint_sites.csv" $out $files

$activeSitesEvidence = @($sites | Select-Object Url,Title,Owner,Template,LastContentModifiedDate,LockState,@{Name="status";Expression={ if ($_.LockState -eq "Unlock") { "pass" } else { "fail" } }},@{Name="value";Expression={ "LockState=$($_.LockState);LastContentModifiedDate=$($_.LastContentModifiedDate)" }},@{Name="evidence_source";Expression={ "Get-PnPTenantSite" }})
Export-CraExpectedCsv $activeSitesEvidence $out "active_sites_count.csv" $files "Get-PnPTenantSite"

$activeUsersEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "SharePoint active user counts require Microsoft Graph reports endpoint getSharePointActivityUserDetail or admin usage report export."
  evidence_source = "GET /reports/getSharePointActivityUserDetail"
})
Export-CraExpectedCsv $activeUsersEvidence $out "active_users_on_sharepoint.csv" $files "GET /reports/getSharePointActivityUserDetail"

$storageEvidence = @($sites | Select-Object Url,Title,StorageUsageCurrent,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "StorageUsageCurrent=$($_.StorageUsageCurrent)" }},@{Name="evidence_source";Expression={ "Get-PnPTenantSite" }})
Export-CraExpectedCsv $storageEvidence $out "storage_quota_consumption.csv" $files "Get-PnPTenantSite"

$external = @($sites | Select-Object Url,Title,SharingCapability,Owner)
Add-CraCsvIfAny $external "external_sharing.csv" $out $files
$externalEvidence = @($sites | ForEach-Object {
  [pscustomobject]@{
    Url = $_.Url
    Title = $_.Title
    SharingCapability = $_.SharingCapability
    status = if ($_.SharingCapability -match "ExternalUserAndGuestSharing|Anonymous") { "fail" } else { "pass" }
    value = "SharingCapability=$($_.SharingCapability)"
    evidence_source = "Get-PnPTenantSite"
  }
})
Add-CraCsvIfAny $externalEvidence "external_sharing_settings.csv" $out $files

$inactiveThreshold = (Get-Date).AddDays(-90)
$inactive = @($sites | Where-Object { $_.LastContentModifiedDate -and $_.LastContentModifiedDate -lt $inactiveThreshold } |
  Select-Object Url,Title,Owner,LastContentModifiedDate,StorageUsageCurrent)
Add-CraCsvIfAny $inactive "inactive_sites.csv" $out $files
$inactivePolicy = @([pscustomobject]@{
  InactiveSiteCount = @($inactive).Count
  TotalSiteCount = @($sites).Count
  PolicySignal = "LastContentModifiedDate older than 90 days"
  status = if (@($inactive).Count -eq 0) { "pass" } else { "fail" }
  value = "InactiveSites=$(@($inactive).Count);TotalSites=$(@($sites).Count)"
  evidence_source = "Get-PnPTenantSite"
})
$path = Join-Path $out "inactive_site_policies.csv"; Export-CraCsv $inactivePolicy $path; $files.Add($path)

$siteOwnership = @(foreach ($site in $sites) {
  [pscustomobject]@{
    Url = $site.Url
    Title = $site.Title
    Owner = $site.Owner
    status = if ([string]::IsNullOrWhiteSpace($site.Owner)) { "fail" } else { "pass" }
    value = "Owner=$($site.Owner)"
    evidence_source = "Get-PnPTenantSite"
  }
})
Add-CraCsvIfAny $siteOwnership "site_ownership_policies.csv" $out $files

$sharingLinks = @(foreach ($site in $sites) {
  [pscustomobject]@{
    Url = $site.Url
    Title = $site.Title
    SharingCapability = $site.SharingCapability
    status = if ($site.SharingCapability -match "ExternalUserAndGuestSharing|Anonymous") { "fail" } else { "pass" }
    value = "SharingCapability=$($site.SharingCapability)"
    EvidenceSource = "Get-PnPTenantSite"
  }
})
Add-CraCsvIfAny $sharingLinks "sharing_links.csv" $out $files
Add-CraCsvIfAny $sharingLinks "checking_sharing_permissions_for_each_sites_on_a_tenant.csv" $out $files

$keywordRows = @(foreach ($site in $sites) {
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
})
Add-CraCsvIfAny $keywordRows "getting_all_sites_with_sensitivity_keywords_on_a_tenant.csv" $out $files

Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray()
