param(
  [Parameter(Mandatory=$true)][string]$TenantId,
  [string]$OutputPath = "storage/validation/m365-graph-proof.json",
  [ValidateSet("Device", "Browser", "Context")]
  [string]$AuthMode = "Device"
)

$ErrorActionPreference = "Stop"

Import-Module Microsoft.Graph.Authentication -ErrorAction Stop
. (Join-Path $PSScriptRoot "../app/powershell/common/cra_common.ps1")

$scopes = @(
  "Directory.Read.All",
  "Policy.Read.All",
  "Application.Read.All",
  "RoleManagement.Read.Directory",
  "AuditLog.Read.All",
  "UserAuthenticationMethod.Read.All",
  "Reports.Read.All",
  "Group.Read.All",
  "Team.ReadBasic.All",
  "Sites.Read.All",
  "Files.Read.All"
)

$env:CRA_GRAPH_AUTH_MODE = $AuthMode.ToLowerInvariant()
$context = Connect-CraGraph -TenantId $TenantId -Scopes $scopes

$user = Get-MgUser -Top 1 -Property "id,displayName,userPrincipalName,mail" -ErrorAction Stop | Select-Object -First 1
if (-not $user) {
  throw "Get-MgUser returned no users for the signed-in tenant."
}

$organization = Get-MgOrganization -Top 1 -Property "id,displayName,verifiedDomains" -ErrorAction Stop | Select-Object -First 1
if (-not $organization) {
  throw "Get-MgOrganization returned no organization for the signed-in tenant."
}

$target = Resolve-Path -Path "." | Select-Object -ExpandProperty Path
$fullOutput = Join-Path $target $OutputPath
$outputDir = Split-Path -Parent $fullOutput
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$proof = [ordered]@{
  status = "success"
  tenant_id = $context.TenantId
  account = $context.Account
  auth_type = $context.AuthType
  scopes = $context.Scopes
  required_scopes = $scopes
  missing_scopes = @($scopes | Where-Object { $_ -notin @($context.Scopes) })
  get_mg_user_returned = $true
  get_mg_organization_returned = $true
  sample_user_id = $user.Id
  sample_user_principal_name = $user.UserPrincipalName
  organization_id = $organization.Id
  organization_display_name = $organization.DisplayName
  timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
}

$proof | ConvertTo-Json -Depth 6 | Set-Content -Path $fullOutput -Encoding UTF8
$proof | ConvertTo-Json -Depth 6
