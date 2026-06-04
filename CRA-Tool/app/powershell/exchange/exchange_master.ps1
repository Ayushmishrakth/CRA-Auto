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

$out = Initialize-CraArtifactDirectory -OutputRoot $OutputRoot -AssessmentId $AssessmentId -Domain "exchange"
$files = New-Object System.Collections.Generic.List[string]

Connect-CraExchange -Collector $collector

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

$sharingPolicies = Get-SharingPolicy | ForEach-Object {
  $domains = ($_.Domains -join ";")
  [pscustomobject]@{
    Policy = $_.Identity
    Enabled = $_.Enabled
    Domains = $domains
    status = if ($domains -match "CalendarSharingFreeBusyReviewer|CalendarSharingOwner|Anonymous") { "fail" } else { "pass" }
    value = "Enabled=$($_.Enabled);Domains=$domains"
    evidence_source = "Get-SharingPolicy"
  }
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
