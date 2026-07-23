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

# The collector's ONLY stdout output must be the JSON contract. Silence the non-error
# streams (progress/warning/verbose/information/debug) so module import banners,
# Connect-ExchangeOnline notices, and Install-Module chatter can never be interleaved with
# the JSON payload on stdout. Errors still flow to stderr and are captured separately.
$ProgressPreference    = 'SilentlyContinue'
$WarningPreference     = 'SilentlyContinue'
$InformationPreference = 'SilentlyContinue'
$VerbosePreference     = 'SilentlyContinue'
$DebugPreference       = 'SilentlyContinue'

$collector = $CollectorJson | ConvertFrom-Json
$parameter = $ParameterJson | ConvertFrom-Json
$paramSeverity = if ($parameter.severity) { [string]$parameter.severity } else { "medium" }

# Any Exchange prerequisite / authentication / permission problem is an INTERNAL collection
# (infrastructure) failure. It is reported as a non-tenant-FAIL "warning" with a neutral
# message, and it NEVER surfaces implementation details (modules, cmdlets, roles, environment
# variables) or a tenant-configuration verdict. This prevents a collection problem from being
# misread as a tenant misconfiguration. The technical cause is returned as Detail for the
# internal warnings/telemetry channel only.
function Get-CraExchangeFailure {
  param([string]$Message)
  return @{
    status   = "warning"
    severity = "info"
    message  = "Exchange Online configuration could not be automatically retrieved during this assessment run."
    detail   = [string]$Message
  }
}

# Emit a single-finding collector contract for no-evidence outcomes (module / auth / consent /
# certificate / RBAC), where no CSV evidence is produced. Mirrors Write-CraContract's schema
# but permits an empty generated_files set (the shared helper marks -GeneratedFiles mandatory).
# Any technical Detail is carried only in the internal warnings channel, never in the finding
# message shown to the customer.
function Write-CraExchangeContract {
  param(
    [Parameter(Mandatory=$true)][string]$Status,
    [Parameter(Mandatory=$true)][string]$Message,
    [string]$Severity = "info",
    [string]$Detail = ""
  )
  $contractWarnings = @()
  if ($Detail) { $contractWarnings = @("EXCHANGE_COLLECTION_DETAIL: $Detail") }
  [ordered]@{
    status    = "success"
    collector = $CollectorName
    tenant_id = $TenantId
    timestamp = (Get-Date).ToUniversalTime().ToString("o")
    findings  = @(
      [ordered]@{
        parameter_key      = $ParameterKey
        status             = $Status
        severity           = $Severity
        value              = [ordered]@{ generated_files = @() }
        message            = $Message
        score_contribution = $(if ($Status -eq "pass") { 0 } else { $null })
      }
    )
    metrics   = [ordered]@{ generated_files = @(); generated_file_count = 0 }
    warnings  = $contractWarnings
    errors    = @()
  } | ConvertTo-Json -Depth 8 -Compress
}

# Full automatic validation: ensure the ExchangeOnlineManagement module is available. If it is
# missing, attempt a best-effort automatic install into the current-user scope so the
# assessment can proceed and return the ACTUAL tenant configuration. The collector never
# immediately fails for a missing module and never emits a customer-facing "install module"
# instruction; a genuinely unavailable module becomes an internal collection warning.
function Ensure-CraExchangeModule {
  # All install/import output streams are redirected to $null (*> $null) so nothing can leak
  # onto stdout; a terminating error (-ErrorAction Stop) still propagates to the catch block.
  if (Get-Module -ListAvailable -Name "ExchangeOnlineManagement") {
    try { Import-Module ExchangeOnlineManagement -ErrorAction Stop *> $null; return @{ ok = $true; detail = "" } }
    catch { return @{ ok = $false; detail = "Module import failed: $($_.Exception.Message)" } }
  }
  try {
    try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch {}
    if (-not (Get-PackageProvider -Name NuGet -ErrorAction SilentlyContinue)) {
      Install-PackageProvider -Name NuGet -Scope CurrentUser -Force -ErrorAction SilentlyContinue *> $null
    }
    Install-Module -Name ExchangeOnlineManagement -Scope CurrentUser -Force -AllowClobber -ErrorAction Stop *> $null
    Import-Module ExchangeOnlineManagement -ErrorAction Stop *> $null
    return @{ ok = $true; detail = "auto-installed" }
  } catch {
    return @{ ok = $false; detail = "Automatic module install failed: $($_.Exception.Message)" }
  }
}

$moduleState = Ensure-CraExchangeModule
if (-not $moduleState.ok) {
  $mf = Get-CraExchangeFailure -Message $moduleState.detail
  Write-CraExchangeContract -Status $mf.status -Severity $mf.severity -Message $mf.message -Detail $mf.detail
  exit 0
}

$out = Initialize-CraArtifactDirectory -OutputRoot $OutputRoot -AssessmentId $AssessmentId -Domain "exchange"
$files = New-Object System.Collections.Generic.List[string]

# Attempt Exchange connection. Any auth / admin consent / certificate / RBAC / service
# failure is converted into an accurate, scored finding (see Get-CraExchangeFailure)
# instead of crashing the assessment or emitting a hard-coded "Unauthorized".
try {
  Connect-CraExchange -Collector $collector
} catch {
  $f = Get-CraExchangeFailure -Message $_.Exception.Message
  Write-CraExchangeContract -Status $f.status -Severity $f.severity -Message $f.message -Detail $f.detail
  exit 0
}

# =====================================================================================
# Real evaluated findings for the three Exchange parameters routed to this script. Each is
# answered by a single org-level cmdlet (no mailbox enumeration needed), so they are
# computed here and emitted directly with the manual evaluated_value text (not the generic
# CSV path). mailbox_storage_usage / mailboxes_status / email activity route to Graph.
# =====================================================================================
$findingMap = @{}

# customer_lockbox: Customer Lockbox must be ENABLED.
try {
  $orgConfig = Get-OrganizationConfig
  $lockboxOn = ($orgConfig.CustomerLockBoxEnabled -eq $true)
  $lockboxEvidence = @([pscustomobject]@{ Identity = $orgConfig.Identity; CustomerLockBoxEnabled = $orgConfig.CustomerLockBoxEnabled; status = if ($lockboxOn) { "pass" } else { "fail" }; value = "CustomerLockBoxEnabled=$($orgConfig.CustomerLockBoxEnabled)"; evidence_source = "Get-OrganizationConfig" })
  $findingMap["customer_lockbox"] = @{
    status = if ($lockboxOn) { "pass" } else { "fail" }
    message = if ($lockboxOn) { "Customer Lockbox is enabled" } else { "Customer lockbox is not enabled. No one is assigned the Customer Lockbox Access Approver" }
    severity = "medium"
  }
} catch {
  $f = Get-CraExchangeFailure -Message $_.Exception.Message
  $lockboxEvidence = @([pscustomobject]@{ Identity = ""; CustomerLockBoxEnabled = ""; status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-OrganizationConfig" })
  $findingMap["customer_lockbox"] = @{ status = $f.status; message = $f.message; severity = $f.severity; detail = $f.detail }
}
$path = Join-Path $out "customer_lockbox.csv"; Export-CraCsv $lockboxEvidence $path; $files.Add($path)

# external_storage_providers_in_owa: additional (third-party) storage providers must be OFF.
try {
  $owaPolicies = @(Get-OwaMailboxPolicy)
  $anyProviders = (@($owaPolicies | Where-Object { $_.AdditionalStorageProvidersAvailable -eq $true }).Count -gt 0)
  $owaEvidence = @($owaPolicies | ForEach-Object { [pscustomobject]@{ Policy = $_.Identity; AdditionalStorageProvidersAvailable = $_.AdditionalStorageProvidersAvailable; status = if ($_.AdditionalStorageProvidersAvailable -eq $false) { "pass" } else { "fail" }; value = "AdditionalStorageProvidersAvailable=$($_.AdditionalStorageProvidersAvailable)"; evidence_source = "Get-OwaMailboxPolicy" } })
  $findingMap["external_storage_providers_in_owa"] = @{
    status = if ($anyProviders) { "fail" } else { "pass" }
    message = if ($anyProviders) { "External storage providers are enabled." } else { "External storage providers are disabled." }
    severity = "medium"
  }
} catch {
  $f = Get-CraExchangeFailure -Message $_.Exception.Message
  $owaEvidence = @([pscustomobject]@{ Policy = ""; AdditionalStorageProvidersAvailable = ""; status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-OwaMailboxPolicy" })
  $findingMap["external_storage_providers_in_owa"] = @{ status = $f.status; message = $f.message; severity = $f.severity; detail = $f.detail }
}
$path = Join-Path $out "external_storage_providers_in_owa.csv"; Export-CraCsv $owaEvidence $path; $files.Add($path)

# full_calendar_schedules_able_to_be_shared_externally: only ENABLED sharing policies are
# in effect. A policy that shares detailed calendar info externally
# (CalendarSharingFreeBusyDetail or CalendarSharingFreeBusyReviewer) fails; free/busy time
# only (CalendarSharingFreeBusySimple), disabled policies, and no policy pass. The invalid
# "CalendarSharingOwner" action is not a real Exchange sharing action and is not evaluated.
try {
  $sharingPolicies = @(Get-SharingPolicy)
  $detailPattern = 'CalendarSharingFreeBusyDetail|CalendarSharingFreeBusyReviewer'
  $enabledPolicies = @($sharingPolicies | Where-Object { $_.Enabled -eq $true })
  $externalCal = (@($enabledPolicies | Where-Object { ($_.Domains -join ';') -match $detailPattern }).Count -gt 0)
  $sharingEvidence = if ($sharingPolicies.Count -gt 0) {
    @($sharingPolicies | ForEach-Object {
      $domains = ($_.Domains -join ';')
      $isFail = ($_.Enabled -eq $true) -and ($domains -match $detailPattern)
      [pscustomobject]@{ Policy = $_.Identity; Enabled = $_.Enabled; Domains = $domains; status = if ($isFail) { "fail" } else { "pass" }; value = "Enabled=$($_.Enabled);Domains=$domains"; evidence_source = "Get-SharingPolicy" }
    })
  } else {
    @([pscustomobject]@{ Policy = ""; Enabled = ""; Domains = ""; status = "pass"; value = "No sharing policy present"; evidence_source = "Get-SharingPolicy" })
  }
  $findingMap["full_calendar_schedules_able_to_be_shared_externally"] = @{
    status = if ($externalCal) { "fail" } else { "pass" }
    message = if ($externalCal) { "Detailed calendar information can be shared externally." } else { "Only Free/Busy calendar sharing is configured." }
    severity = "medium"
  }
} catch {
  $f = Get-CraExchangeFailure -Message $_.Exception.Message
  $sharingEvidence = @([pscustomobject]@{ Policy = ""; Enabled = ""; Domains = ""; status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-SharingPolicy" })
  $findingMap["full_calendar_schedules_able_to_be_shared_externally"] = @{ status = $f.status; message = $f.message; severity = $f.severity; detail = $f.detail }
}
$path = Join-Path $out "full_calendar_schedules_able_to_be_shared_externally.csv"; Export-CraCsv $sharingEvidence $path; $files.Add($path)

# Parse an Exchange ByteQuantifiedSize value (e.g. "1.23 GB (1,320,000,000 bytes)",
# "Unlimited", or a raw byte count from the REST cmdlets) into a numeric byte value.
function ConvertTo-CraBytes {
  param($Value)
  if ($null -eq $Value) { return 0.0 }
  $text = [string]$Value
  if ($text -match '\(([\d,]+)\s*bytes\)') { return [double]($matches[1] -replace ',', '') }
  try { return [double]$Value.Value.ToBytes() } catch {}
  if ($text -match '^\s*([\d,]+)\s*$') { return [double]($matches[1] -replace ',', '') }
  return 0.0
}

# mailbox_storage_usage: evaluated via Exchange PowerShell (Get-EXOMailboxStatistics + the
# per-mailbox quota) so it returns the ACTUAL tenant configuration instead of depending on the
# Microsoft Graph usage-report download that fails DNS in restricted networks. PASS when every
# user mailbox is below 75% of its storage quota; FAIL if any is at/above 75%. Only computed
# when this is the requested parameter (per-mailbox statistics are expensive to enumerate).
if ($ParameterKey -eq "mailbox_storage_usage") {
  try {
    $usageRows = New-Object System.Collections.Generic.List[object]
    $overThreshold = 0
    $maxRatio = 0.0
    $userMailboxes = @(Get-EXOMailbox -ResultSize Unlimited -RecipientTypeDetails UserMailbox -Properties ProhibitSendReceiveQuota)
    foreach ($mb in $userMailboxes) {
      $stat = Get-EXOMailboxStatistics -Identity $mb.ExternalDirectoryObjectId -ErrorAction SilentlyContinue
      $usedBytes = ConvertTo-CraBytes $stat.TotalItemSize
      $quotaText = [string]$mb.ProhibitSendReceiveQuota
      $quotaBytes = if ($quotaText -match 'Unlimited') { 0.0 } else { ConvertTo-CraBytes $mb.ProhibitSendReceiveQuota }
      $ratio = if ($quotaBytes -gt 0) { [math]::Round($usedBytes / $quotaBytes * 100, 2) } else { 0.0 }
      if ($ratio -ge 75) { $overThreshold++ }
      if ($ratio -gt $maxRatio) { $maxRatio = $ratio }
      $usageRows.Add([pscustomobject]@{
        UserPrincipalName = $mb.UserPrincipalName
        UsedBytes         = $usedBytes
        QuotaBytes        = $quotaBytes
        UsagePercent      = $ratio
        status            = if ($ratio -ge 75) { "fail" } else { "pass" }
        value             = "UsagePercent=$ratio;Used=$usedBytes;Quota=$quotaBytes"
        evidence_source   = "Get-EXOMailboxStatistics"
      })
    }
    $mailboxStorageEvidence = if ($usageRows.Count -gt 0) { $usageRows.ToArray() } else {
      @([pscustomobject]@{ UserPrincipalName = ""; UsedBytes = 0; QuotaBytes = 0; UsagePercent = 0; status = "pass"; value = "No user mailboxes found"; evidence_source = "Get-EXOMailboxStatistics" })
    }
    $findingMap["mailbox_storage_usage"] = @{
      status  = if ($overThreshold -gt 0) { "fail" } else { "pass" }
      message = if ($overThreshold -gt 0) { "$overThreshold user mailbox(es) are at or above 75% of their storage quota (highest $maxRatio%)." } else { "All user mailboxes are below 75% of their storage quota (highest $maxRatio%)." }
      severity = "medium"
    }
  } catch {
    $f = Get-CraExchangeFailure -Message $_.Exception.Message
    $mailboxStorageEvidence = @([pscustomobject]@{ UserPrincipalName = ""; UsedBytes = 0; QuotaBytes = 0; UsagePercent = 0; status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-EXOMailboxStatistics" })
    $findingMap["mailbox_storage_usage"] = @{ status = $f.status; message = $f.message; severity = $f.severity; detail = $f.detail }
  }
  $path = Join-Path $out "mailbox_storage_usage.csv"; Export-CraCsv $mailboxStorageEvidence $path; $files.Add($path)
}

# Fast path: the parameters answered above are emitted directly. Emit the real finding and
# stop before the (unneeded, slow) generic mailbox enumeration below.
if ($findingMap.ContainsKey($ParameterKey)) {
  $f = $findingMap[$ParameterKey]
  $fWarnings = @()
  if ($f.detail) { $fWarnings = @("EXCHANGE_COLLECTION_DETAIL: $($f.detail)") }
  Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray() -FindingStatus $f.status -FindingMessage $f.message -FindingSeverity $f.severity -Warnings $fWarnings
  return
}

$mailboxes = Get-EXOMailbox -ResultSize Unlimited -Properties AuditEnabled,ForwardingSmtpAddress,DeliverToMailboxAndForward,RecipientTypeDetails |
  Select-Object ExternalDirectoryObjectId,DisplayName,UserPrincipalName,RecipientTypeDetails,AuditEnabled
$path = Join-Path $out "mailbox_audit.csv"; Export-CraCsv $mailboxes $path; $files.Add($path)

$rules = Get-TransportRule | Select-Object Name,State,Mode,Priority,Comments
$path = Join-Path $out "transport_rules.csv"; Export-CraCsv $rules $path; $files.Add($path)

$forwarding = Get-EXOMailbox -ResultSize Unlimited -Properties ForwardingSmtpAddress,DeliverToMailboxAndForward |
  Where-Object { $_.ForwardingSmtpAddress -or $_.DeliverToMailboxAndForward } |
  Select-Object DisplayName,UserPrincipalName,ForwardingSmtpAddress,DeliverToMailboxAndForward
$path = Join-Path $out "mail_forwarding.csv"; Export-CraCsv $forwarding $path; $files.Add($path)

$safeLinks = Get-SafeLinksPolicy | Select-Object Name,IsEnabled,EnableSafeLinksForEmail,EnableSafeLinksForTeams
$path = Join-Path $out "safe_links.csv"; Export-CraCsv $safeLinks $path; $files.Add($path)

$owaPolicies = Get-OwaMailboxPolicy | ForEach-Object {
  [pscustomobject]@{
    Policy = $_.Identity
    AdditionalStorageProvidersAvailable = $_.AdditionalStorageProvidersAvailable
    status = if ($_.AdditionalStorageProvidersAvailable -eq $false) { "pass" } else { "fail" }
    value = "AdditionalStorageProvidersAvailable=$($_.AdditionalStorageProvidersAvailable)"
    evidence_source = "Get-OwaMailboxPolicy"
  }
}
$path = Join-Path $out "external_storage_providers_in_owa.csv"; Export-CraCsv $owaPolicies $path; $files.Add($path)

$sharingPolicies = @(Get-SharingPolicy | ForEach-Object {
  $domains = ($_.Domains -join ";")
  [pscustomobject]@{
    Policy = $_.Identity
    Enabled = $_.Enabled
    Domains = $domains
    status = if (($_.Enabled -eq $true) -and ($domains -match "CalendarSharingFreeBusyDetail|CalendarSharingFreeBusyReviewer")) { "fail" } else { "pass" }
    value = "Enabled=$($_.Enabled);Domains=$domains"
    evidence_source = "Get-SharingPolicy"
  }
})
if ($sharingPolicies.Count -eq 0) {
  $sharingPolicies = @([pscustomobject]@{
    Policy = ""
    Enabled = ""
    Domains = ""
    status = "fail"
    value = "No sharing policy set"
    evidence_source = "Get-SharingPolicy"
  })
}
$orgCalendar = Get-OrganizationConfig | Select-Object Identity,CalendarVersionStoreEnabled
$calendarRows = @($sharingPolicies) + @(
  $orgCalendar | ForEach-Object {
    [pscustomobject]@{
      Policy = $_.Identity
      Enabled = $_.CalendarVersionStoreEnabled
      Domains = ""
      status = "pass"
      value = "CalendarVersionStoreEnabled=$($_.CalendarVersionStoreEnabled)"
      evidence_source = "Get-OrganizationConfig"
    }
  }
)
$path = Join-Path $out "full_calendar_schedules_able_to_be_shared_externally.csv"; Export-CraCsv $calendarRows $path; $files.Add($path)

try {
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
  $lockboxEvidence = @([pscustomobject]@{ Identity = ""; CustomerLockBoxEnabled = ""; status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-OrganizationConfig" })
}
Export-CraExpectedCsv $lockboxEvidence $out "customer_lockbox.csv" $files "Get-OrganizationConfig"

$mailboxStatusEvidence = $mailboxes | Select-Object ExternalDirectoryObjectId,DisplayName,UserPrincipalName,RecipientTypeDetails,@{Name="status";Expression={ if ($_.RecipientTypeDetails) { "pass" } else { "fail" } }},@{Name="value";Expression={ "RecipientTypeDetails=$($_.RecipientTypeDetails)" }},@{Name="evidence_source";Expression={ "Get-EXOMailbox" }}
Export-CraExpectedCsv $mailboxStatusEvidence $out "mailboxes_status_active_inactive.csv" $files "Get-EXOMailbox"

try {
  $mailboxStats = Get-EXOMailbox -ResultSize Unlimited | Get-EXOMailboxStatistics | Select-Object DisplayName,TotalItemSize,ItemCount
  $mailboxStorageEvidence = $mailboxStats | Select-Object DisplayName,TotalItemSize,ItemCount,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "TotalItemSize=$($_.TotalItemSize);ItemCount=$($_.ItemCount)" }},@{Name="evidence_source";Expression={ "Get-EXOMailboxStatistics" }}
} catch {
  $mailboxStorageEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-EXOMailboxStatistics" })
}
Export-CraExpectedCsv $mailboxStorageEvidence $out "mailbox_storage_usage.csv" $files "Get-EXOMailboxStatistics"

$emailActivityReadEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "Email read/received activity requires Microsoft Graph reports endpoint getEmailActivityUserDetail or admin usage report export."
  evidence_source = "GET /reports/getEmailActivityUserDetail"
})
Export-CraExpectedCsv $emailActivityReadEvidence $out "number_of_emails_read_received.csv" $files "GET /reports/getEmailActivityUserDetail"

$emailActivitySentEvidence = @([pscustomobject]@{
  status = "not_collected"
  value = "Email sent activity requires Microsoft Graph reports endpoint getEmailActivityUserDetail or admin usage report export."
  evidence_source = "GET /reports/getEmailActivityUserDetail"
})
Export-CraExpectedCsv $emailActivitySentEvidence $out "number_of_emails_sent.csv" $files "GET /reports/getEmailActivityUserDetail"

try {
  $transportConfig = Get-TransportConfig | Select-Object Identity,SmtpClientAuthenticationDisabled
  $channelEmailEvidence = $transportConfig | Select-Object Identity,SmtpClientAuthenticationDisabled,@{Name="status";Expression={ "pass" }},@{Name="value";Expression={ "SmtpClientAuthenticationDisabled=$($_.SmtpClientAuthenticationDisabled)" }},@{Name="evidence_source";Expression={ "Get-TransportConfig" }}
} catch {
  $channelEmailEvidence = @([pscustomobject]@{ status = "not_collected"; value = $_.Exception.Message; evidence_source = "Get-TransportConfig" })
}
Export-CraExpectedCsv $channelEmailEvidence $out "teams_channel_email_addresses.csv" $files "Get-TransportConfig"

Write-CraContract -CollectorName $CollectorName -TenantId $TenantId -ParameterKey $ParameterKey -GeneratedFiles $files.ToArray()
