$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

function Initialize-CraArtifactDirectory {
  param(
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [Parameter(Mandatory=$true)][string]$AssessmentId,
    [Parameter(Mandatory=$true)][string]$Domain
  )
  $path = Join-Path $OutputRoot $AssessmentId
  $path = Join-Path $path $Domain
  New-Item -ItemType Directory -Path $path -Force | Out-Null
  return (Resolve-Path $path).Path
}

function Assert-CraModule {
  param([Parameter(Mandatory=$true)][string]$Name)
  if (-not (Get-Module -ListAvailable -Name $Name)) {
    throw "Required PowerShell module '$Name' is not installed. Run scripts/install_m365_modules.ps1."
  }
  if ($Name -eq "Microsoft.Graph") {
    Import-Module "Microsoft.Graph.Authentication" -ErrorAction Stop
    return
  }
  if ($Name -eq "Microsoft.Graph.Beta") {
    # The beta package is a meta-module without a separate authentication
    # submodule. Specific beta command modules autoload when a beta cmdlet is
    # used; avoid importing the full meta-module during every collector run.
    return
  }
  Import-Module $Name -ErrorAction Stop
}

function Export-CraCsv {
  param(
    [Parameter(Mandatory=$true)]$InputObject,
    [Parameter(Mandatory=$true)][string]$Path
  )
  $InputObject | Export-Csv -Path $Path -NoTypeInformation -Encoding UTF8
  if (-not (Test-Path $Path)) {
    throw "CSV evidence file was not created: $Path"
  }
}

function Export-CraExpectedCsv {
  param(
    [Parameter(Mandatory=$true)]$InputObject,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [Parameter(Mandatory=$true)][string]$FileName,
    [Parameter(Mandatory=$true)]$Files,
    [Parameter(Mandatory=$true)][string]$EvidenceSource,
    [string]$FallbackMessage = "Collector returned no rows for this evidence source."
  )
  $rows = @($InputObject)
  if (-not $rows -or $rows.Count -eq 0) {
    $rows = @([pscustomobject]@{
      status = "not_collected"
      value = $FallbackMessage
      evidence_source = $EvidenceSource
    })
  }
  $path = Join-Path $OutputDirectory $FileName
  Export-CraCsv $rows $path
  $Files.Add($path) | Out-Null
}

function Get-CraAuthMode {
  param(
    [string]$SpecificEnvName,
    [object]$Collector
  )
  if ($Collector -and $Collector.auth_mode) {
    return [string]$Collector.auth_mode
  }
  if ($SpecificEnvName -and [Environment]::GetEnvironmentVariable($SpecificEnvName)) {
    return [Environment]::GetEnvironmentVariable($SpecificEnvName)
  }
  if ([Environment]::GetEnvironmentVariable("CRA_M365_AUTH_MODE")) {
    return [Environment]::GetEnvironmentVariable("CRA_M365_AUTH_MODE")
  }
  return "context"
}

function Assert-CraGraphContext {
  param(
    [Parameter(Mandatory=$true)][string]$TenantId,
    [Parameter(Mandatory=$true)][string[]]$Scopes
  )
  $context = Get-MgContext
  if (-not $context) {
    throw "Microsoft Graph context is not active. Run device-code validation first or set CRA_GRAPH_AUTH_MODE=device for an interactive validation run."
  }
  if ($TenantId -notin @("common", "organizations") -and $context.TenantId -ne $TenantId) {
    throw "Microsoft Graph context tenant '$($context.TenantId)' does not match required tenant '$TenantId'."
  }
  $granted = @($context.Scopes)
  $missing = @($Scopes | Where-Object { $_ -notin $granted })
  if ($missing.Count -gt 0) {
    throw "Microsoft Graph context is missing required scopes: $($missing -join ', ')."
  }
  return $context
}

function Connect-CraGraph {
  param(
    [Parameter(Mandatory=$true)][string]$TenantId,
    [Parameter(Mandatory=$true)][string[]]$Scopes,
    [object]$Collector = $null
  )
  Assert-CraModule "Microsoft.Graph"
  $mode = (Get-CraAuthMode -SpecificEnvName "CRA_GRAPH_AUTH_MODE" -Collector $Collector).ToLowerInvariant()
  $clientTimeout = 600
  if ([Environment]::GetEnvironmentVariable("CRA_GRAPH_CLIENT_TIMEOUT_SECONDS")) {
    $clientTimeout = [int][Environment]::GetEnvironmentVariable("CRA_GRAPH_CLIENT_TIMEOUT_SECONDS")
  }
  $accessToken = [Environment]::GetEnvironmentVariable("CRA_GRAPH_ACCESS_TOKEN")
  if ($accessToken) {
    $secureToken = ConvertTo-SecureString $accessToken -AsPlainText -Force
    Connect-MgGraph -AccessToken $secureToken -NoWelcome -ErrorAction Stop | Out-Null
    $validated = Assert-CraGraphContext -TenantId $TenantId -Scopes $Scopes
    Get-MgOrganization -Top 1 -ErrorAction Stop | Out-Null
    return $validated
  }
  $context = Get-MgContext
  if ($context) {
    try {
      Assert-CraGraphContext -TenantId $TenantId -Scopes $Scopes | Out-Null
      return $context
    } catch {
      if ($mode -eq "context") { throw }
    }
  }

  if ($mode -eq "context") {
    throw "Microsoft Graph auth mode is 'context' but no valid persisted context exists. Run scripts/validate_m365_connection.ps1 -TenantId <tenant> -AuthMode Device first."
  }

  if ($mode -in @("app", "application", "client_credentials", "clientsecret")) {
    $clientId = [Environment]::GetEnvironmentVariable("CRA_GRAPH_CLIENT_ID")
    $clientSecret = [Environment]::GetEnvironmentVariable("CRA_GRAPH_CLIENT_SECRET")
    if (-not $clientId -or -not $clientSecret) {
      throw "Microsoft Graph app auth requires CRA_GRAPH_CLIENT_ID and CRA_GRAPH_CLIENT_SECRET."
    }
    $secureSecret = ConvertTo-SecureString $clientSecret -AsPlainText -Force
    $credential = [System.Management.Automation.PSCredential]::new($clientId, $secureSecret)
    Connect-MgGraph -TenantId $TenantId -ClientSecretCredential $credential -NoWelcome -ErrorAction Stop | Out-Null
    $validated = Get-MgContext
    if (-not $validated) {
      throw "Microsoft Graph app auth did not create a valid context."
    }
    Get-MgOrganization -Top 1 -ErrorAction Stop | Out-Null
    return $validated
  }

  if ($mode -eq "device") {
    Connect-MgGraph -TenantId $TenantId -Scopes $Scopes -UseDeviceCode -ContextScope CurrentUser -ClientTimeout $clientTimeout -NoWelcome -ErrorAction Stop | Out-Null
  } elseif ($mode -in @("browser", "interactive", "delegated")) {
    try {
      Connect-MgGraph -TenantId $TenantId -Scopes $Scopes -ContextScope CurrentUser -ClientTimeout $clientTimeout -NoWelcome -ErrorAction Stop | Out-Null
    } catch {
      throw "Browser Graph auth failed. On Windows embedded terminals this is often a WAM window-handle issue; retry with CRA_GRAPH_AUTH_MODE=device. Original error: $($_.Exception.Message)"
    }
  } else {
    throw "Unsupported Microsoft Graph auth mode '$mode'. Use context, device, browser, interactive, or delegated."
  }

  $validated = Assert-CraGraphContext -TenantId $TenantId -Scopes $Scopes
  Get-MgOrganization -Top 1 -ErrorAction Stop | Out-Null
  return $validated
}

function Connect-CraTeams {
  param(
    [Parameter(Mandatory=$true)][string]$TenantId,
    [object]$Collector = $null
  )
  Assert-CraModule "MicrosoftTeams"
  $mode = (Get-CraAuthMode -SpecificEnvName "CRA_TEAMS_AUTH_MODE" -Collector $Collector).ToLowerInvariant()
  if ($mode -in @("app", "application", "client_credentials")) {
    # App-only auth: requires application_access permission granted via admin consent
    $clientId     = [Environment]::GetEnvironmentVariable("CRA_GRAPH_CLIENT_ID")
    $clientSecret = [Environment]::GetEnvironmentVariable("CRA_GRAPH_CLIENT_SECRET")
    if (-not $clientId -or -not $clientSecret) {
      throw "[CRA_TEAMS_SKIP] Teams app auth requires CRA_GRAPH_CLIENT_ID and CRA_GRAPH_CLIENT_SECRET env vars."
    }
    $secureSecret = ConvertTo-SecureString $clientSecret -AsPlainText -Force
    Connect-MicrosoftTeams -ApplicationId $clientId -ClientSecret $secureSecret -TenantId $TenantId -ErrorAction Stop | Out-Null
  } elseif ($mode -eq "device") {
    Connect-MicrosoftTeams -TenantId $TenantId -UseDeviceAuthentication -ErrorAction Stop | Out-Null
  } elseif ($mode -in @("browser", "interactive", "delegated")) {
    Connect-MicrosoftTeams -TenantId $TenantId -ErrorAction Stop | Out-Null
  } elseif ($mode -in @("skip", "none", "disabled")) {
    throw "[CRA_TEAMS_SKIP] Teams auth is disabled for automated runs (CRA_TEAMS_AUTH_MODE=skip). Configure app or device auth for Teams collection."
  } else {
    # context mode: never open browser; fail cleanly if no active session
    throw "[CRA_TEAMS_SKIP] Teams PowerShell requires delegated or app auth. Set CRA_TEAMS_AUTH_MODE=app for automated runs, or CRA_TEAMS_AUTH_MODE=device for interactive auth."
  }
}

function Connect-CraExchange {
  param([object]$Collector = $null)
  Assert-CraModule "ExchangeOnlineManagement"
  $mode = (Get-CraAuthMode -SpecificEnvName "CRA_EXCHANGE_AUTH_MODE" -Collector $Collector).ToLowerInvariant()
  if ($mode -in @("app", "application", "client_credentials")) {
    # App-only auth: use a pre-fetched Exchange Online access token.
    # The Python runtime acquires this token via client_credentials against
    # https://outlook.office365.com/.default and passes it as CRA_EXCHANGE_ACCESS_TOKEN.
    $tok = [Environment]::GetEnvironmentVariable("CRA_EXCHANGE_ACCESS_TOKEN")
    $org = [Environment]::GetEnvironmentVariable("CRA_EXCHANGE_ORGANIZATION")
    if (-not $tok) { throw "[CRA_EXCHANGE_SKIP] CRA_EXCHANGE_ACCESS_TOKEN is not set. Exchange app auth requires Exchange.ManageAsApp consent and a pre-fetched token." }
    if (-not $org) { throw "[CRA_EXCHANGE_SKIP] CRA_EXCHANGE_ORGANIZATION is not set. Set it to the tenant's primary .onmicrosoft.com domain." }
    Connect-ExchangeOnline -AccessToken (ConvertTo-SecureString $tok -AsPlainText -Force) -Organization $org -ShowBanner:$false -ErrorAction Stop
  } elseif ($mode -eq "device") {
    Connect-ExchangeOnline -Device -ShowBanner:$false -ErrorAction Stop
  } elseif ($mode -in @("browser", "interactive", "delegated")) {
    Connect-ExchangeOnline -DisableWAM -ShowBanner:$false -ErrorAction Stop
  } elseif ($mode -in @("skip", "none", "disabled")) {
    throw "[CRA_EXCHANGE_SKIP] Exchange Online auth is disabled for automated runs (CRA_EXCHANGE_AUTH_MODE=skip). Configure app auth to enable Exchange collection."
  } elseif ($mode -eq "token") {
    $tok = [Environment]::GetEnvironmentVariable("CRA_EXCHANGE_ACCESS_TOKEN")
    $org = [Environment]::GetEnvironmentVariable("CRA_EXCHANGE_ORGANIZATION")
    if (-not $tok) { throw "[CRA_EXCHANGE_SKIP] CRA_EXCHANGE_ACCESS_TOKEN is not set." }
    if ($org) {
      Connect-ExchangeOnline -AccessToken (ConvertTo-SecureString $tok -AsPlainText -Force) -Organization $org -ShowBanner:$false -ErrorAction Stop
    } else {
      Connect-ExchangeOnline -AccessToken (ConvertTo-SecureString $tok -AsPlainText -Force) -ShowBanner:$false -ErrorAction Stop
    }
  } else {
    # context mode: only use an already-established session — never open a browser
    try {
      $conn = Get-ConnectionInformation -ErrorAction SilentlyContinue
      if (-not $conn) { throw "no active session" }
    } catch {
      throw "[CRA_EXCHANGE_SKIP] Exchange Online: no active context session. Run Connect-ExchangeOnline manually first, or set CRA_EXCHANGE_AUTH_MODE=device for interactive auth."
    }
  }
}

function Connect-CraPurview {
  param([object]$Collector = $null)
  Assert-CraModule "ExchangeOnlineManagement"
  $mode = (Get-CraAuthMode -SpecificEnvName "CRA_PURVIEW_AUTH_MODE" -Collector $Collector).ToLowerInvariant()
  if ($mode -in @("skip", "none", "disabled")) {
    throw "[CRA_PURVIEW_SKIP] Purview auth is disabled for automated runs (CRA_PURVIEW_AUTH_MODE=skip)."
  } elseif ($mode -in @("browser", "interactive", "delegated", "device")) {
    Connect-IPPSSession -DisableWAM -ErrorAction Stop | Out-Null
  } else {
    # context mode: never open browser; fail if no active session
    try {
      $conn = Get-ConnectionInformation -ErrorAction SilentlyContinue
      if (-not $conn) { throw "no active session" }
    } catch {
      throw "[CRA_PURVIEW_SKIP] Purview/IPPSSession: no active context session. Set CRA_PURVIEW_AUTH_MODE=device for interactive auth."
    }
  }
}

function Connect-CraPnP {
  param(
    [Parameter(Mandatory=$true)][string]$Url,
    [object]$Collector = $null
  )
  Assert-CraModule "PnP.PowerShell"
  $mode = (Get-CraAuthMode -SpecificEnvName "CRA_PNP_AUTH_MODE" -Collector $Collector).ToLowerInvariant()
  if ($mode -eq "device") {
    Connect-PnPOnline -Url $Url -DeviceLogin -PersistLogin -ErrorAction Stop
  } elseif ($mode -in @("browser", "interactive", "delegated")) {
    Connect-PnPOnline -Url $Url -Interactive -PersistLogin -ErrorAction Stop
  } else {
    Connect-PnPOnline -Url $Url -ValidateConnection -ErrorAction Stop
  }
}

function Write-CraContract {
  param(
    [Parameter(Mandatory=$true)][string]$CollectorName,
    [Parameter(Mandatory=$true)][string]$TenantId,
    [Parameter(Mandatory=$true)][string]$ParameterKey,
    [Parameter(Mandatory=$true)][string[]]$GeneratedFiles,
    [string[]]$Warnings = @()
  )
  $result = [ordered]@{
    status = "success"
    collector = $CollectorName
    tenant_id = $TenantId
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
    findings = @(
      [ordered]@{
        parameter_key = $ParameterKey
        status = "not_collected"
        severity = "info"
        value = [ordered]@{
          generated_files = $GeneratedFiles
        }
        message = "Evidence CSV files were generated; finding evaluation must be performed by the CSV finding engine."
        score_contribution = 0
      }
    )
    metrics = [ordered]@{
      generated_files = $GeneratedFiles
      generated_file_count = $GeneratedFiles.Count
    }
    warnings = $Warnings
    errors = @()
  }
  $result | ConvertTo-Json -Depth 8 -Compress
}
