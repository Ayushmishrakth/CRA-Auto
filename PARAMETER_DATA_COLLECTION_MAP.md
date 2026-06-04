# Parameter Data Collection Map

Source: attached CRA parameter sheet.  
Rule: pass/fail criteria must come from the sheet. This file maps each parameter to the real data source needed to evaluate that sheet-defined logic.

## Summary

Total parameters in attached sheet: 65

Recommended implementation order:

1. Microsoft Graph Identity and Security parameters.
2. Microsoft 365 Reports API usage parameters.
3. Exchange Online PowerShell parameters.
4. Teams PowerShell parameters.
5. SharePoint Graph and PnP PowerShell parameters.
6. Purview PowerShell parameters.
7. Manual-only parameters.

## Collection Matrix

| # | Parameter | Category | Technology | Collection Method | Exact API / Query / Command | Required Permissions | Required Evidence |
|---:|---|---|---|---|---|---|---|
| 1 | Global Administrator Accounts | Entra ID | Entra ID | Microsoft Graph | `GET /directoryRoles?$filter=displayName eq 'Global Administrator'&$select=id,displayName,roleTemplateId`; then `GET /directoryRoles/{role-id}/members?$select=id,displayName,userPrincipalName,mail` | `Directory.Read.All`, `RoleManagement.Read.Directory` | Type, DisplayName, UPN, ObjectId |
| 2 | Guest users count | Entra ID | Entra ID | Microsoft Graph | `GET /users?$select=id,displayName,userPrincipalName,mail,userType&$filter=userType eq 'Guest'`; total users from `GET /users/$count` with `ConsistencyLevel: eventual` | `User.Read.All`, `Directory.Read.All` | Guest display name, username, mail, id, total users, guest ratio |
| 3 | User Information | Entra ID | Entra ID | Microsoft Graph | `GET /users?$select=id,displayName,userPrincipalName,mail,jobTitle,department,accountEnabled,userType` | `User.Read.All`, `Directory.Read.All` | All users and required profile fields |
| 4 | Guest Invite Settings | Entra ID | Entra ID | Microsoft Graph | `GET /policies/authorizationPolicy?$select=id,allowInvitesFrom,defaultUserRolePermissions` | `Policy.Read.All` | `allowInvitesFrom`, default user role permissions |
| 5 | Entra - Third Party App Integrations | Entra ID | Entra ID | Microsoft Graph | `GET /policies/authorizationPolicy?$select=id,defaultUserRolePermissions` | `Policy.Read.All` | `defaultUserRolePermissions.allowedToCreateApps` |
| 6 | Tenant Collaboration Invitations | Entra ID | Entra ID | Microsoft Graph | `GET /policies/crossTenantAccessPolicy`; `GET /policies/crossTenantAccessPolicy/partners` | `Policy.Read.All` | Collaboration policy mode, allowed or denied domains |
| 7 | Authentication methods enabled | Entra ID | Entra ID | Microsoft Graph | `GET /policies/authenticationMethodsPolicy/authenticationMethodConfigurations` | `Policy.Read.All` | Authentication method id, method type, state |
| 8 | Admin Consent Workflow | Entra ID | Entra ID | Microsoft Graph | `GET /policies/adminConsentRequestPolicy` | `Policy.Read.All` | request enabled, reviewers, email notification, reminders, expiry days |
| 9 | CAP policies for risky sign-ins | Entra ID | Entra ID | Microsoft Graph | `GET /identity/conditionalAccess/policies?$select=id,displayName,state,conditions,grantControls` | `Policy.Read.All` | Name, state, sign-in risk levels, user risk levels, grant controls |
| 10 | Users without MFA | Entra ID | Entra ID | Microsoft 365 Reports API | `GET /reports/authenticationMethods/userRegistrationDetails` | `Reports.Read.All`, `UserAuthenticationMethod.Read.All` | UserPrincipalName, isMfaCapable, isMfaRegistered, auth method types |
| 11 | Unused licenses count | Entra ID | Licensing | Microsoft Graph | `GET /subscribedSkus` | `Organization.Read.All`, `Directory.Read.All` | SkuId, SkuPartNumber, prepaid units, consumed units, unused count |
| 12 | Emergency Access Accounts | Entra ID | Entra ID | Manual Validation | No reliable universal API because break-glass accounts are tenant naming/process dependent. Use `GET /directoryRoles/{global-admin-role-id}/members` to assist manual identification. | `Directory.Read.All`, `RoleManagement.Read.Directory` | Named emergency accounts, role assignment, exclusion from CA/MFA policy if required by tenant process |
| 13 | User Consent For Applications | Entra ID | Entra ID | Microsoft Graph | `GET /policies/authorizationPolicy?$select=id,defaultUserRolePermissions` | `Policy.Read.All` | user consent setting and app consent policy state |
| 14 | Custom Banned Password List | Entra ID | Entra ID | Manual Validation | No stable Microsoft Graph endpoint for reading the tenant custom banned password list values. Validate in Entra admin center Password Protection blade. | Manual admin access | enabled/disabled state and visible custom banned password terms where portal permits |
| 15 | Non-Admin Users can register Applications | Entra ID | Entra ID | Microsoft Graph | `GET /policies/authorizationPolicy?$select=id,defaultUserRolePermissions` | `Policy.Read.All` | `defaultUserRolePermissions.allowedToCreateApps` |
| 16 | Restricted Access To Microsoft Entra Admin Centre | Entra ID | Entra ID | Microsoft Graph | `GET /policies/authorizationPolicy?$select=id,defaultUserRolePermissions` | `Policy.Read.All` | `defaultUserRolePermissions.allowedToReadOtherUsers` and admin center restriction evidence if exposed |
| 17 | Self-Service Password Reset Authentication Method | Entra ID | Entra ID | Microsoft Graph | `GET /policies/authenticationMethodsPolicy/authenticationMethodConfigurations`; optionally `GET /reports/authenticationMethods/userRegistrationDetails` | `Policy.Read.All`, `Reports.Read.All` | enabled methods, registered methods per user |
| 18 | Account enabled | Entra ID | Entra ID | Microsoft Graph | `GET /users?$select=id,displayName,userPrincipalName,mail,accountEnabled,userType` | `User.Read.All`, `Directory.Read.All` | user list and account enabled status |
| 19 | Assigned License | Entra ID | Licensing | Microsoft Graph | `GET /users?$select=id,displayName,userPrincipalName,assignedLicenses,assignedPlans`; `GET /subscribedSkus` | `User.Read.All`, `Directory.Read.All`, `Organization.Read.All` | users missing prerequisite licenses, assigned SKU ids |
| 20 | Conditional Access Policies (Exclusion) | Entra ID | Entra ID | Microsoft Graph | `GET /identity/conditionalAccess/policies?$select=id,displayName,state,conditions,grantControls` | `Policy.Read.All` | policy name, state, include users/groups, exclude users/groups/roles |
| 21 | Entra - Tenant Creation By Non-Admin | Entra ID | Entra ID | Microsoft Graph | `GET /policies/authorizationPolicy?$select=id,defaultUserRolePermissions` | `Policy.Read.All` | `defaultUserRolePermissions.allowedToCreateTenants` |
| 22 | Devices without compliance policies | Entra ID | Intune | Microsoft Graph | `GET /deviceManagement/managedDevices?$select=id,deviceName,userPrincipalName,complianceState,managementAgent,operatingSystem` | `DeviceManagementManagedDevices.Read.All` | non-compliant or unknown compliance devices |
| 23 | Mailboxes Status (Active/Inactive) | Exchange Online | Exchange | Exchange Online PowerShell | `Get-EXOMailbox -ResultSize Unlimited -Properties WhenMailboxCreated`; activity from `Get-MailboxStatistics` or reports API `GET /reports/getEmailActivityUserDetail(period='D30')` | Exchange admin role; Graph `Reports.Read.All` if using reports | active mailbox count, inactive mailbox count, mailbox identities |
| 24 | Mailbox Storage usage | Exchange Online | Exchange | Exchange Online PowerShell | `Get-EXOMailbox -ResultSize Unlimited | Get-EXOMailboxStatistics` | Exchange admin role | display name, UPN, total item size, quota, usage percent |
| 25 | Number of emails read/received | Exchange Online | Exchange | Microsoft 365 Reports API | `GET /reports/getEmailActivityUserDetail(period='D30')` | `Reports.Read.All` | user principal name, read count, receive count |
| 26 | Number of emails sent | Exchange Online | Exchange | Microsoft 365 Reports API | `GET /reports/getEmailActivityUserDetail(period='D30')` | `Reports.Read.All` | user principal name, send count |
| 27 | External Storage Providers In OWA | Exchange Online | Exchange | Exchange Online PowerShell | `Get-OwaMailboxPolicy | Select-Object Identity,AdditionalStorageProvidersAvailable` | Exchange admin role | policy identity, external storage provider setting |
| 28 | Full Calendar Schedules Able To Be Shared Externally | Exchange Online | Exchange | Exchange Online PowerShell | `Get-SharingPolicy | Select-Object Identity,Enabled,Domains` and `Get-OrganizationConfig | Select-Object *Calendar*` | Exchange admin role | sharing policy identity, enabled state, allowed domains |
| 29 | Customer Lockbox | M365 | Microsoft 365 | Exchange Online PowerShell | `Get-OrganizationConfig | Select-Object CustomerLockBoxEnabled` | Exchange admin role / Global Reader | CustomerLockBoxEnabled |
| 30 | Compliance Score overview | Microsoft Purview | Purview | Manual Validation | Microsoft Purview compliance score is not consistently exposed through Microsoft Graph for tenant collection. Validate in Purview portal or supported compliance export. | Compliance admin / Purview access | compliance score percentage |
| 31 | Secure Score percentage | Microsoft Purview | Security | Microsoft Graph | `GET /security/secureScores?$top=1` | `SecurityEvents.Read.All` | current score, max score, percentage |
| 32 | Audit log retention duration | Microsoft Purview | Purview | Purview PowerShell | `Get-RetentionCompliancePolicy`; `Get-RetentionComplianceRule` | Purview compliance role | audit/retention policy names, enabled state, duration |
| 33 | Sensitivity Labels configured and applied | Microsoft Purview | Purview | Purview PowerShell | `Get-Label`; `Get-LabelPolicy`; for application evidence use content explorer/export where available | Purview compliance role | label names, scope, policy assignments, applied evidence |
| 34 | Audit Logs enabled | Microsoft Purview | Purview | Purview PowerShell | `Get-AdminAuditLogConfig | Select-Object UnifiedAuditLogIngestionEnabled` | Exchange/Purview audit role | audit enabled true/false |
| 35 | DLP rules configured | Microsoft Purview | Purview | Purview PowerShell | `Get-DlpCompliancePolicy`; `Get-DlpComplianceRule` | Purview compliance role | DLP policy/rule name, mode, workload, enabled state |
| 36 | Information Protection Labels applied | Microsoft Purview | Purview | Purview PowerShell | `Get-Label`; `Get-LabelPolicy`; applied evidence from Purview content explorer/export where available | Purview compliance role | label definitions, policy assignment, applied label evidence |
| 37 | Sensitivity Labels applied to Teams | Microsoft Purview | Teams/Purview | Purview PowerShell + Microsoft Graph | `Get-Label`; `Get-LabelPolicy`; `GET /groups?$select=id,displayName,assignedLabels,resourceProvisioningOptions` | `Group.Read.All`, Purview compliance role | Teams groups with assigned labels |
| 38 | Sensitivity labels are applied | Microsoft Purview | Purview | Purview PowerShell | `Get-Label`; `Get-LabelPolicy`; applied label export where available | Purview compliance role | configured labels and application evidence |
| 39 | Guest access enabled / disabled | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsClientConfiguration | Select-Object AllowGuestUser` and `Get-CsTeamsGuestMessagingConfiguration` | Teams admin role | guest access enabled/disabled |
| 40 | Minimum number of owners | Microsoft Teams | Teams | Microsoft Graph | `GET /groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')&$select=id,displayName`; then `GET /groups/{id}/owners?$select=id,displayName,userPrincipalName` | `Group.Read.All`, `Directory.Read.All` | team name, owner count, total teams with fewer than two owners |
| 41 | Orphan Teams | Microsoft Teams | Teams | Microsoft Graph | Same as owners collection; orphan team is team with zero owners | `Group.Read.All`, `Directory.Read.All` | team name, team id, owner count |
| 42 | Teams - Anonymous Users | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsMeetingPolicy | Select-Object Identity,AllowAnonymousUsersToJoinMeeting` | Teams admin role | policy identity, anonymous join setting |
| 43 | Teams - External Unmanaged User Communication | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsAcsFederationConfiguration`; `Get-CsTenantFederationConfiguration` | Teams admin role | external unmanaged/federation communication settings |
| 44 | Active /Inactive teams | Microsoft Teams | Teams | Microsoft 365 Reports API | `GET /reports/getTeamsTeamActivityDetail(period='D30')` | `Reports.Read.All` | team name/id, last activity date, active/inactive classification |
| 45 | Activer/Inactive Teams users | Microsoft Teams | Teams | Microsoft 365 Reports API | `GET /reports/getTeamsUserActivityUserDetail(period='D30')` | `Reports.Read.All` | user principal name, last activity, inactive user count |
| 46 | Teams - File Storage Option | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsFilesPolicy` | Teams admin role | identity, native file entry points, third-party storage state if exposed |
| 47 | Teams with external users | Microsoft Teams | Teams | Microsoft Graph | `GET /groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')`; then `GET /groups/{id}/members?$select=id,displayName,userPrincipalName,userType` | `Group.Read.All`, `Directory.Read.All` | teams with guest/external members, ratio |
| 48 | Copilot integration enabled | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsAppSetupPolicy`; `Get-TeamsApp -DisplayName *Copilot*` where available | Teams admin role | Teams app policy identity and Copilot app availability |
| 49 | Meeting transcription enabled | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsMeetingPolicy | Select-Object Identity,AllowTranscription` | Teams admin role | policy identity, AllowTranscription |
| 50 | Meeting recording retention policies | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsMeetingPolicy | Select-Object Identity,RecordingStorageMode,NewMeetingRecordingExpirationDays` | Teams admin role | recording storage mode, expiration days |
| 51 | Meeting Policies configuration | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsMeetingPolicy | Select-Object Identity,AllowCloudRecording,AutoAdmittedUsers,AllowMeetingReactions,MeetingChatEnabledType,AllowTranscription,AllowIPVideo,ExplicitRecordingConsent,AllowExternalNonTrustedMeetingChat,AllowBreakoutRooms` | Teams admin role | full meeting policy settings listed in sheet |
| 52 | Teams - Channel Email Addresses | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsClientConfiguration | Select-Object AllowEmailIntoChannel,RestrictedSenderList` | Teams admin role | allow email into channel, restricted domains |
| 53 | Teams - Lobby Bypass | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsMeetingPolicy | Select-Object Identity,AutoAdmittedUsers` | Teams admin role | lobby bypass / auto admitted users |
| 54 | Teams - Meeting Chat | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsMeetingPolicy | Select-Object Identity,MeetingChatEnabledType` | Teams admin role | meeting chat setting |
| 55 | Third-party apps allowed | Microsoft Teams | Teams | Teams PowerShell | `Get-CsTeamsAppPermissionPolicy`; `Get-CsTeamsAppSetupPolicy` | Teams admin role | custom/third-party app availability policy |
| 56 | External sharing settings | OneDrive for Business | OneDrive | SharePoint Graph / PnP PowerShell | `Get-SPOTenant | Select-Object SharingCapability,OneDriveSharingCapability` | SharePoint admin role | OneDrive external sharing level |
| 57 | Total active users on OneDrive | OneDrive for Business | OneDrive | Microsoft 365 Reports API | `GET /reports/getOneDriveActivityUserDetail(period='D30')` | `Reports.Read.All` | active users, last activity, active ratio |
| 58 | Active Sites count | SharePoint Online | SharePoint | Microsoft 365 Reports API | `GET /reports/getSharePointSiteUsageDetail(period='D30')` | `Reports.Read.All`, `Sites.Read.All` | active site count, site URL, activity date |
| 59 | Active users on SharePoint | SharePoint Online | SharePoint | Microsoft 365 Reports API | `GET /reports/getSharePointActivityUserDetail(period='D30')` | `Reports.Read.All` | active users, last activity, active ratio |
| 60 | SharePoint - Modern Authentication | SharePoint Online | SharePoint | PnP PowerShell | `Get-SPOTenant | Select-Object LegacyAuthProtocolsEnabled` | SharePoint admin role | legacy auth enabled/disabled |
| 61 | Storage Quota consumption | SharePoint Online | SharePoint | PnP PowerShell | `Get-SPOSite -Limit All | Select-Object Url,StorageUsageCurrent,StorageQuota` | SharePoint admin role | site URL, storage used, quota, usage percent |
| 62 | Sharing Settings (External/Internal) | SharePoint Online | SharePoint | PnP PowerShell | `Get-SPOTenant | Select-Object SharingCapability,PreventExternalUsersFromResharing,RequireAcceptingAccountMatchInvitedAccount` | SharePoint admin role | external sharing and resharing controls |
| 63 | SharePoint & OneDrive Guest Access Expiry | SharePoint Online | SharePoint/OneDrive | PnP PowerShell | `Get-SPOTenant | Select-Object SharingCapability,RequireAnonymousLinksExpireInDays,ExternalUserExpirationRequired,ExternalUserExpireInDays` | SharePoint admin role | sharing expiration days and external user expiry settings |
| 64 | Getting all sites with Sensitivity keywords on a Tenant | SharePoint Online | SharePoint | SharePoint Graph / PnP PowerShell | `Get-SPOSite -Limit All | Select-Object Url,Title,SensitivityLabel`; optionally search by title/url keywords from sheet process | SharePoint admin role, `Sites.Read.All` | sites with sensitivity labels or sensitivity keywords |
| 65 | Checking Sharing permissions for each sites on a Tenant | SharePoint Online | SharePoint | PnP PowerShell | `Get-SPOSite -Limit All`; then `Get-SPOExternalUser -SiteUrl {site-url}` and site sharing settings | SharePoint admin role | site URL, external sharing state, external users, guest expiration |

## Implementation Notes

### Automatable With Current Graph App Permissions

These can be implemented first with the permissions already targeted by the CRA app registration:

```text
Global Administrator Accounts
Guest users count
User Information
Guest Invite Settings
Entra - Third Party App Integrations
Tenant Collaboration Invitations
Authentication methods enabled
Admin Consent Workflow
CAP policies for risky sign-ins
Users without MFA
Unused licenses count
User Consent For Applications
Non-Admin Users can register Applications
Restricted Access To Microsoft Entra Admin Centre
Self-Service Password Reset Authentication Method
Account enabled
Assigned License
Conditional Access Policies (Exclusion)
Entra - Tenant Creation By Non-Admin
Devices without compliance policies
Secure Score percentage
Microsoft 365 usage report parameters
```

### Requires PowerShell Runtime Credentials / Modules

```text
Exchange Online PowerShell
Teams PowerShell
SharePoint Online / PnP PowerShell
Purview PowerShell
```

These should use real tenant admin delegated/session-based collection or app-only PowerShell where the module supports it.

### Manual Or Portal-Only Until Proven Otherwise

```text
Emergency Access Accounts
Custom Banned Password List
Compliance Score overview
```

These should not receive placeholder collectors. They need explicit manual evidence upload or a verified supported API/export path.

## Fastest Data Path

1. Implement remaining Entra ID Graph collectors.
2. Add Microsoft 365 Reports API collectors for email, Teams, SharePoint, and OneDrive activity.
3. Add Exchange Online PowerShell collectors.
4. Add Teams PowerShell collectors.
5. Add SharePoint/PnP collectors.
6. Add Purview collectors.
7. Add manual evidence workflow for manual-only controls.

