param(
  [string[]]$Modules = @(
    "Microsoft.Graph",
    "Microsoft.Graph.Beta",
    "ExchangeOnlineManagement",
    "MicrosoftTeams",
    "PnP.PowerShell",
    "Az.Accounts",
    "Az.Resources"
  ),
  [string]$LogPath = "artifacts/module-install.log"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$logDirectory = Split-Path -Parent $LogPath
if ($logDirectory -and -not (Test-Path $logDirectory)) {
  New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

function Write-InstallLog {
  param([string]$Message)
  $line = "$(Get-Date -Format o) $Message"
  Write-Host $line
  Add-Content -Path $LogPath -Value $line
}

Write-InstallLog "PowerShell version: $($PSVersionTable.PSVersion)"
$failures = New-Object System.Collections.Generic.List[string]

if (-not (Get-PSRepository -Name PSGallery -ErrorAction SilentlyContinue)) {
  Register-PSRepository -Default
}

Set-PSRepository -Name PSGallery -InstallationPolicy Trusted

foreach ($moduleName in $Modules) {
  $installed = Get-Module -ListAvailable -Name $moduleName | Sort-Object Version -Descending | Select-Object -First 1
  if ($installed) {
    Write-InstallLog "SKIP $moduleName version $($installed.Version) already installed"
    continue
  }

  try {
    Write-InstallLog "INSTALL $moduleName"
    Install-Module -Name $moduleName -Scope CurrentUser -AllowClobber -Force -ErrorAction Stop
    $resolved = Get-Module -ListAvailable -Name $moduleName | Sort-Object Version -Descending | Select-Object -First 1
    Write-InstallLog "OK $moduleName version $($resolved.Version)"
  } catch {
    Write-InstallLog "FAILED $moduleName :: $($_.Exception.Message)"
    $failures.Add($moduleName)
  }
}

if ($failures.Count -gt 0) {
  throw "Failed to install required Microsoft 365 modules: $($failures -join ', ')"
}
