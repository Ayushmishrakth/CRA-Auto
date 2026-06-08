param(
    [string]$TenantId = "fe4eff9a-f69c-48c0-921d-8006a6d5beb2",
    [string]$ClientId = "33688cf5-d33b-4483-992a-d3e2ce6e1b15",
    [string[]]$SpaRedirectUris = @(
        "http://localhost:3000/tenant/deployment-success",
        "http://localhost:3000"
    )
)

$ErrorActionPreference = "Stop"

if (-not (Get-Module Microsoft.Graph.Authentication -ListAvailable)) {
    throw "Microsoft.Graph.Authentication module is not installed. Run: Install-Module Microsoft.Graph -Scope CurrentUser"
}

Import-Module Microsoft.Graph.Authentication

try {
    Connect-MgGraph -TenantId $TenantId -Scopes "Application.ReadWrite.All" -UseDeviceCode -NoWelcome
} catch {
    Connect-MgGraph -TenantId $TenantId -Scopes "Application.ReadWrite.All" -UseDeviceAuthentication -NoWelcome
}

$encodedFilter = [uri]::EscapeDataString("appId eq '$ClientId'")
$appResponse = Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/v1.0/applications?`$filter=$encodedFilter&`$select=id,appId,displayName,web,spa"
$app = @($appResponse.value)[0]

if (-not $app) {
    throw "Application with client ID '$ClientId' was not found in tenant '$TenantId'."
}

$currentWeb = @($app.web.redirectUris) | Where-Object { $_ }
$currentSpa = @($app.spa.redirectUris) | Where-Object { $_ }

# Browser MSAL redirects must not be registered as Web, or Entra returns AADSTS9002326.
$newWeb = @($currentWeb | Where-Object { $SpaRedirectUris -notcontains $_ })
$newSpa = @($currentSpa + $SpaRedirectUris | Where-Object { $_ } | Select-Object -Unique)

$body = @{
    web = @{
        redirectUris = @($newWeb)
    }
    spa = @{
        redirectUris = @($newSpa)
    }
} | ConvertTo-Json -Depth 10

Invoke-MgGraphRequest -Method PATCH -Uri "https://graph.microsoft.com/v1.0/applications/$($app.id)" -Body $body -ContentType "application/json"

$verified = Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/v1.0/applications/$($app.id)?`$select=id,appId,displayName,web,spa"

Write-Host "Application repaired:" $verified.displayName
Write-Host "Client ID:" $verified.appId
Write-Host "Web redirect URIs:"
@($verified.web.redirectUris) | ForEach-Object { Write-Host "  $_" }
Write-Host "SPA redirect URIs:"
@($verified.spa.redirectUris) | ForEach-Object { Write-Host "  $_" }
