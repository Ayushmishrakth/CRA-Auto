<#
.SYNOPSIS
  One-time setup so the CRA app registration can run PowerShell collectors
  (PnP/SharePoint + Teams) using CERTIFICATE app-only auth.

  MUST be run interactively by a Global Administrator (or Application
  Administrator + Privileged Role Administrator) of the target tenant.
  The CRA backend cannot perform these steps itself: its app-only token
  lacks Application.ReadWrite.All and admin consent requires a human admin.

.WHAT IT DOES
  1. Uploads the public certificate (.cer) to the app registration.
  2. Adds the SharePoint Online API application permission
     Sites.FullControl.All (resource 00000003-0000-0ff1-ce00-000000000000).
  3. Grants tenant admin consent for that permission.
  4. Prints the remaining manual step for Teams app-only authorization.

.PARAMETER AppId        The CRA app (client) id, e.g. 7f7fa622-...
.PARAMETER TenantId     The tenant id (GUID).
.PARAMETER CerPath      Path to the public certificate exported by cert generation.
#>
param(
  [Parameter(Mandatory=$true)][string]$AppId,
  [Parameter(Mandatory=$true)][string]$TenantId,
  [string]$CerPath = "$PSScriptRoot\..\secrets\cra_cert.cer"
)

$ErrorActionPreference = "Stop"

# SharePoint Online API + the Sites.FullControl.All APPLICATION role id.
$SPO_RESOURCE_APPID = "00000003-0000-0ff1-ce00-000000000000"
$SPO_SITES_FULLCONTROL_ALL = "678536fe-1083-478a-9c59-b99265e6b0d3"  # Sites.FullControl.All (Role)

Write-Host "Connecting to Microsoft Graph as an admin (interactive)..." -ForegroundColor Cyan
Connect-MgGraph -TenantId $TenantId -Scopes @(
  "Application.ReadWrite.All",
  "AppRoleAssignment.ReadWrite.All",
  "Directory.ReadWrite.All"
) -NoWelcome

# Resolve the application object id from the app (client) id.
$app = Get-MgApplication -Filter "appId eq '$AppId'"
if (-not $app) { throw "Application with appId $AppId not found in tenant $TenantId." }
$appObjectId = $app.Id
Write-Host "App object id: $appObjectId" -ForegroundColor Green

# --- 1. Upload the certificate to the app registration ----------------------
if (-not (Test-Path $CerPath)) { throw "Certificate not found at $CerPath" }
$certBytes = [IO.File]::ReadAllBytes((Resolve-Path $CerPath))
$existingKeys = @($app.KeyCredentials)
$newKey = @{
  type  = "AsymmetricX509Cert"
  usage = "Verify"
  key   = $certBytes
  displayName = "CRA-CertAuth"
}
Update-MgApplication -ApplicationId $appObjectId -KeyCredentials ($existingKeys + $newKey)
Write-Host "Certificate uploaded to app registration." -ForegroundColor Green

# --- 2. Add the SharePoint Online API application permission -----------------
$rra = @($app.RequiredResourceAccess)
$spoBlock = $rra | Where-Object { $_.ResourceAppId -eq $SPO_RESOURCE_APPID } | Select-Object -First 1
if (-not $spoBlock) {
  $spoBlock = @{ ResourceAppId = $SPO_RESOURCE_APPID; ResourceAccess = @() }
  $rra += $spoBlock
}
if (-not ($spoBlock.ResourceAccess | Where-Object { $_.Id -eq $SPO_SITES_FULLCONTROL_ALL })) {
  $spoBlock.ResourceAccess += @{ Id = $SPO_SITES_FULLCONTROL_ALL; Type = "Role" }
}
Update-MgApplication -ApplicationId $appObjectId -RequiredResourceAccess $rra
Write-Host "SharePoint Online API Sites.FullControl.All added to required permissions." -ForegroundColor Green

# --- 3. Grant admin consent (create the app role assignment) -----------------
$clientSp = Get-MgServicePrincipal -Filter "appId eq '$AppId'"
$spoSp    = Get-MgServicePrincipal -Filter "appId eq '$SPO_RESOURCE_APPID'"
if (-not $clientSp) { throw "Service principal for app $AppId not found. Create it (New-MgServicePrincipal) then re-run." }
if (-not $spoSp)    { throw "SharePoint Online service principal not found in tenant." }

$already = Get-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $clientSp.Id |
  Where-Object { $_.AppRoleId -eq $SPO_SITES_FULLCONTROL_ALL -and $_.ResourceId -eq $spoSp.Id }
if (-not $already) {
  New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $clientSp.Id -PrincipalId $clientSp.Id `
    -ResourceId $spoSp.Id -AppRoleId $SPO_SITES_FULLCONTROL_ALL | Out-Null
  Write-Host "Admin consent granted for SharePoint Sites.FullControl.All." -ForegroundColor Green
} else {
  Write-Host "SharePoint Sites.FullControl.All consent already present." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==== DONE (SharePoint / PnP cert auth is now configured) ====" -ForegroundColor Cyan
Write-Host "Set these env vars for the CRA backend so collectors use cert auth:" -ForegroundColor Cyan
Write-Host "  CRA_PNP_AUTH_MODE=certificate"
Write-Host "  CRA_CERT_PFX_PATH=<path to secrets\cra_cert.pfx>"
Write-Host "  CRA_CERT_PFX_PASSWORD=<pfx password>"
Write-Host "  CRA_PNP_TENANT=$TenantId"
Write-Host ""
Write-Host "==== TEAMS — separate manual step ====" -ForegroundColor Yellow
Write-Host "MicrosoftTeams 7.x app-only requires CERTIFICATE auth too. After this script:" -ForegroundColor Yellow
Write-Host '  1. Ensure the same cert is on the app (done above).'
Write-Host "  2. Assign the app the 'Teams Administrator' directory role so Get-CsTeams* reads succeed app-only:"
Write-Host '       New-MgRoleManagementDirectoryRoleAssignment -PrincipalId (clientSpId) -RoleDefinitionId 69091246-20e8-4a56-aa4d-066075b2a7a8 -DirectoryScopeId "/"'
Write-Host '       (69091246-20e8-4a56-aa4d-066075b2a7a8 = Teams Administrator role template)'
Write-Host "  3. Then connect with: Connect-MicrosoftTeams -CertificateThumbprint (thumb) -ApplicationId $AppId -TenantId $TenantId"
Write-Host ""
Write-Host "==== EXCHANGE ====" -ForegroundColor Yellow
Write-Host "Exchange Online is currently disabled in this tenant (AADSTS500014 / ServicePrincipalDisabled)."
Write-Host "Exchange PS collectors stay BLOCKED until the Exchange Online service principal is enabled and"
Write-Host "Exchange.ManageAsApp + the cert are granted."
