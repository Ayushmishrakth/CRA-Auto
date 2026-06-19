# CRA Parameter Assessment Reference

This file is generated from the real assessment registry files in `CRA-Tool/app/config/assessment_registry/`.

Sources used:

- `parameters.json` for parameter name, service, description, risk, Copilot relevance, and pass/fail criteria.
- `collectors.json` for the configured collector, Graph endpoint, PowerShell mapping, and expected output.
- `rules.json` for scoring weight, severity, Copilot blocking flag, rule type, and rule criteria.

Important: this document describes how the tool assesses each parameter. It does not say that a specific tenant passed or failed unless runtime evidence exists for that tenant.

Total parameters: 65

## Entra ID (21)

### 1. Administrator Consent Workflows

- **Parameter key:** `admin_consent_workflow`
- **Service:** Entra ID
- **Pillar/domain:** Best Practice
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** boolean_gate
- **Real description:** User cannot request admin consent.
- **Risk:** Without an admin consent workflow, users may inadvertently grant permissions to malicious or risky applications, potentially exposing sensitive data and enabling unauthorised access to Copilot-integrated services.
- **Copilot relevance:** Ensures that only trusted applications can access Copilot data, maintaining security and compliance
- **Expected evidence/output:** Admin workflow for consent requests configurations(Users can request admin consent, Selected users will receive email notifications for requests , Selected users will receive request expiration reminders , Consent request expires after (days))
- **Pass criteria:** When it is configured
- **Fail criteria:** When it is not configured
- **Collection method:** powershell
- **Collector name:** powershell.admin_consent_workflow
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Admin Consent Workflow
- **Portal mapping:** On the Admin portal , Admin Centers --> Identity --> Entra ID --> Enterprise apps --> Consent and Permissions --> Admin Consent Settings
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-admin-consent-workflow

### 2. Authentication Methods Enabled

- **Parameter key:** `authentication_methods_enabled`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** count_threshold
- **Real description:** All authentication methods are enabled.
- **Risk:** Copilot depends on robust user identity verification to ensure secure data access. Weak or outdated authentication mechanisms increase the risk of account compromise, potentially allowing malicious actors to exploit Copilot and access sensitive organisational information.
- **Copilot relevance:** Enforcing strong authentication ensures only verified users can use Copilot, safeguarding against misuse or data leaks via compromised accounts.
- **Expected evidence/output:** List of Authentication methods and state.(Authentication method, State)
- **Pass criteria:** When authentication method has more than 2 authentication methods
- **Fail criteria:** When authentication method has less than 2 authentication methods
- **Collection method:** powershell
- **Collector name:** powershell.authentication_methods_enabled
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Authentication methods enabled
- **Portal mapping:** On the Admin portal , Admin Centers --> Identity --> Entra ID --> Authentication Methods --> Policies
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-methods

### 3. Auto-expiration policy for inactive m365 groups

- **Parameter key:** `auto_expiration_policy_for_inactive_m365_groups`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** percentage_threshold
- **Real description:** Auto-expiration policy for inactive groups is not configured.
- **Risk:** Inactive M365 Groups may retain sensitive data unnecessarily, increasing exposure risk. Copilot may surface outdated or irrelevant content from these teams.
- **Copilot relevance:** Inactive Microsoft 365 groups can retain data that Copilot may surface. Expiration policies reduce stale collaboration data exposure.
- **Expected evidence/output:** Auto-expiration policy for inactive Microsoft 365 groups is configured
- **Pass criteria:** Auto-expiration policy for inactive M365 groups is configured
- **Fail criteria:** Auto-expiration policy for inactive M365 groups is not configured
- **Collection method:** powershell
- **Collector name:** powershell.auto_expiration_policy_for_inactive_m365_groups
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Auto-expiration policy for M365 Groups
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/users/groups-lifecycle

### 4. CAP Policies for Risky Sign-Ins

- **Parameter key:** `cap_policies_for_risky_sign_ins`
- **Service:** Entra ID
- **Pillar/domain:** Governance
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** boolean_gate
- **Real description:** CAP policy for risky sign-ins is not enabled.
- **Risk:** Conditional Access Policies (CAP) are critical for mitigating risky sign-ins. In the absence of stringent CAP enforcement, Copilot may be accessed during compromised sessions, heightening the risk of data leakage via AI-assisted functionalities.
- **Copilot relevance:** These policies ensure Copilot isn't accessed under suspicious conditions, preventing unauthorized use and protecting sensitive data Copilot might surface during such sessions.
- **Expected evidence/output:** List of CAP with conditions for risky sign ins. (Name, State, SignInRiskLevels, UserRiskLevels, GrantControls)
- **Pass criteria:** When CAP policy for Risky Sign -Ins are configured
- **Fail criteria:** When CAP policy for Risky Sign -Ins are not configured
- **Collection method:** powershell
- **Collector name:** powershell.cap_policies_for_risky_sign_ins
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** CAP policies for risky sign-ins
- **Portal mapping:** On the Admin portal , Admin Centers --> Identity --> Entra ID --> Conditional Access --> Policies
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/conditional-access/howto-conditional-access-policy-risk

### 5. Conditional Access Policies (Exclusion)

- **Parameter key:** `conditional_access_policies_exclusion`
- **Service:** Entra ID
- **Pillar/domain:** Best Practice
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** policy_existence_check
- **Real description:** Conditional Access Policies have [X] excluded user(s).
- **Risk:** Excluding users or applications from Conditional Access policies compromises identity security. Granting Copilot access to these excluded users can permit access to sensitive data without the enforcement of essential security measures like multi-factor authentication (MFA), thereby elevating the risk of misuse.
- **Copilot relevance:** Loosely scoped exclusions can allow Copilot access from risky or unmanaged devices or users who have been excluded from various Conditional Access policies.
- **Expected evidence/output:** List of Condiotional access policies with details including all exclusions.
- **Pass criteria:** If no users are excluded from conditional access policies
- **Fail criteria:** If users are excluded from conditional access policies
- **Collection method:** powershell
- **Collector name:** powershell.conditional_access_policies_exclusion
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Conditional Access Policies (Exclusion)
- **Portal mapping:** On the Admin portal , Admin Centers --> Identity --> Entra ID --> Conditional Access --> Policies
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-migration-mfa

### 6. Custom Banned Password List

- **Parameter key:** `custom_banned_password_list`
- **Service:** Entra ID
- **Pillar/domain:** Best Practice
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** Custom-banned password list is currently not enforced.
- **Risk:** Weak or commonly used passwords increase the risk of account compromise. In the absence of a robust, customized banned password list, attackers may hijack accounts and exploit Copilot features to access sensitive data or impersonate users.
- **Copilot relevance:** Enforcing strong passwords (via a custom banned list) helps prevent unauthorized access to accounts that have access to Copilot.
- **Expected evidence/output:** Password Protection enabled state, enforcement mode, and custom banned password count.
- **Pass criteria:** If custom banned password is enabled then users cannot use banned password which is security best practise (example : welcome,Happy,Password etc
- **Fail criteria:** If custom banned password is not enabled then users can use banned password which is not security best practise (example : welcome,Happy,Password etc
- **Collection method:** graph
- **Collector name:** graph.custom_banned_password_list
- **Graph endpoint:** https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/password
- **PowerShell mapping:** Not found in registry.
- **Portal mapping:** Entra admin center > Protection > Authentication methods > Password protection
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-configure-custom-password-protection

### 7. Customer Lockbox

- **Parameter key:** `customer_lockbox`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** composite_rule
- **Real description:** Customer Lockbox is not enabled.
- **Risk:** Without Customer Lockbox, Microsoft support engineers may access tenant data during troubleshooting without explicit approval. In a Copilot-enabled environment, this increases the risk of unintentionally exposing AI-accessible content to external personnel.
- **Copilot relevance:** No relation
- **Expected evidence/output:** We can see if enabled or disabled
- **Pass criteria:** Microsoft support staff cannot access your content without your explicit approval. You get a Lockbox request, and only if you approve it can Microsoft proceed
- **Fail criteria:** Microsoft support staff can access your content without your explicit approval. You get a Lockbox request, and only if you approve it can Microsoft proceed
- **Collection method:** powershell
- **Collector name:** powershell.customer_lockbox
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Customer Lockbox
- **Portal mapping:** On the Azure portal search for customer lockbox --> Administration
- **Documentation URL:** https://learn.microsoft.com/en-us/purview/customer-lockbox-overview

### 8. Device without Compliance Policies

- **Parameter key:** `devices_without_compliance_policies`
- **Service:** Entra ID
- **Pillar/domain:** Best Practice
- **Severity:** info
- **Copilot blocker:** False
- **Scoring weight:** 1.0
- **Rule type:** boolean_gate
- **Real description:** Intune is not being utilized.
- **Risk:** Devices that are not governed by compliance policies pose a significant security risk when accessing Copilot features. In the absence of essential protections such as encryption and threat detection, data surfaced by Copilot may be exposed to theft, loss, or unauthorised disclosure.
- **Copilot relevance:** Unmanaged devices can be risky. Enforcing rules helps keep Copilot's data safe.
- **Expected evidence/output:** List of non complient devices in the tenant
- **Pass criteria:** When compliance policy is configured
- **Fail criteria:** When compliance policy is not configured
- **Collection method:** powershell
- **Collector name:** powershell.devices_without_compliance_policies
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Devices without compliance policies
- **Portal mapping:** Not found in registry.
- **Documentation URL:** https://learn.microsoft.com/en-us/mem/intune/protect/device-compliance-get-started

### 9. Emergency Access Account

- **Parameter key:** `emergency_access_accounts`
- **Service:** Entra ID
- **Pillar/domain:** Best Practice
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** No Break glass accounts are present.
- **Risk:** If emergency access accounts are not properly monitored or restricted, they can be exploited to bypass security controls and access Copilot-generated insights. This creates a potential backdoor to sensitive information, circumventing standard identity protection measures.
- **Copilot relevance:** These accounts are required to avoid tenant lock out
- **Expected evidence/output:** Not found in registry.
- **Pass criteria:** When it is Present
- **Fail criteria:** When not present
- **Collection method:** graph
- **Collector name:** graph.emergency_access_accounts
- **Graph endpoint:** /directoryRoles + /directoryRoles/{id}/members
- **PowerShell mapping:** Not found in registry.
- **Portal mapping:** Need to check
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access

### 10. Entra - Third-Party App Integrations

- **Parameter key:** `entra_third_party_app_integrations`
- **Service:** Entra ID
- **Pillar/domain:** Governance
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** boolean_gate
- **Real description:** Users are allowed to register third-party applications.
- **Risk:** Integrating with inadequately managed third-party applications can expose sensitive user data and permissions accessible to Copilot. These applications may interact with Microsoft 365 services—either contributing or extracting content—which Copilot could process without oversight. This increases the risk of data leakage, compromised data integrity, and diminished control over the information Copilot accesses and shares.
- **Copilot relevance:** Ensuring only trusted applications are integrated helps maintain data integrity, which is crucial for Copilot's accurate functioning.
- **Expected evidence/output:** Third party app integration should be enabled
- **Pass criteria:** When it is disabled for users
- **Fail criteria:** When it is enabled for users
- **Collection method:** powershell
- **Collector name:** powershell.entra_third_party_app_integrations
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Entra - Third Party App Integrations
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/manage-application-permissions

### 11. Entra – Tenant Creation by Non-Admins

- **Parameter key:** `entra_tenant_creation_by_non_admin`
- **Service:** Entra ID
- **Pillar/domain:** Best Practice
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** configuration_value_check
- **Real description:** Non-Admin Users are not allowed to create tenants.
- **Risk:** Allowing non-administrators to create tenants can lead to unmanaged environments where Copilot may be enabled by default. This increases the risk of uncontrolled data exposure and inconsistent security configurations across shadow tenants.
- **Copilot relevance:** Restricting this prevents unauthorized or unmanaged tenants that could misuse Copilot services.
- **Expected evidence/output:** Whether tenant creation by non-admin is enabled or disabled.
- **Pass criteria:** When non-admins are not allowed to create tenants
- **Fail criteria:** When non-admins are allowed to create tenants
- **Collection method:** powershell
- **Collector name:** powershell.entra_tenant_creation_by_non_admin
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Entra - Tenant Creation By Non-Admin
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/fundamentals/users-default-permissions

### 12. Global Administrator Accounts

- **Parameter key:** `global_administrator_accounts`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** count_threshold
- **Real description:** There are a total of [X] Global Administrator accounts.
- **Risk:** An excessive number of unmonitored global admin accounts presents a significant security risk. If compromised, these accounts can exploit Copilot's capabilities to access extensive organizational data, circumventing standard user restrictions and controls.
- **Copilot relevance:** Global Admin is the account with the highest privilages. Limiting and securing these accounts prevents unauthorized configurations or access to Copilot settings.
- **Expected evidence/output:** List of Global admins with Type(User/Service Princpal), Display Name, UPN and object ID
- **Pass criteria:** When tenant has more than 2 or less then 5 global admins
- **Fail criteria:** When tenant has less than 2 or more then 5 global admins
- **Collection method:** powershell
- **Collector name:** powershell.global_administrator_accounts
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Global Administrator Accounts
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/best-practices

### 13. Guest Invite Settings

- **Parameter key:** `guest_invite_settings`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** configuration_value_check
- **Real description:** Anyone in the organisation can invite guest users, including guests and non-admins (most inclusive).
- **Risk:** Permissive invitation settings may permit unintended guests to join the tenant. Once inside, these guests could access content surfaced by Copilot features, thereby increasing the risk of internal data leakage or misuse.
- **Copilot relevance:** Guest invite settings control who can invite external users, impacting Copilot’s access and security in collaborative environments.
- **Expected evidence/output:** Not found in registry.
- **Pass criteria:** When it is set to No one in the organization can invite guest users including admins (most restrictive), Only users assigned to specific admin roles can invite guest users
- **Fail criteria:** Anyone in the organization can invite guest users including guests and non-admins] ,Member users and users assigned to specific admin roles can invite guest users including guests with member permissions
- **Collection method:** powershell
- **Collector name:** powershell.guest_invite_settings
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Guest Invite Settings
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/external-id/external-collaboration-settings-configure

### 14. Guest Users count

- **Parameter key:** `guest_users_count`
- **Service:** Entra ID
- **Pillar/domain:** Governance
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** percentage_threshold
- **Real description:** There are [X] guest users out of [Y] total users.
- **Risk:** Many guest users increase the risk that Copilot may inadvertently expose sensitive data to unintended recipients. In the absence of clear segmentation and strict data access controls, AI tools may treat guests as internal users, potentially revealing critical information.
- **Copilot relevance:** Monitoring guest users ensures that only authorized individuals have access, reducing potential data exposure through Copilot.
- **Expected evidence/output:** List and number of Guest users(Display name , Username, Mail ID , ID)
- **Pass criteria:** When the ratio of guest accounts to total accounts is less than 15%
- **Fail criteria:** When the ratio of guest accounts to total accounts is more than 15%
- **Collection method:** powershell
- **Collector name:** powershell.guest_users_count
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Guest users count
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/external-id/user-properties

### 15. Number of accounts enabled

- **Parameter key:** `account_enabled`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** low
- **Copilot blocker:** False
- **Scoring weight:** 2.0
- **Rule type:** percentage_threshold
- **Real description:** [X] accounts are enabled out of [Y] accounts.
- **Risk:** Copilot engages with all active accounts to deliver AI-driven insights. If inactive or unauthorised accounts remain enabled, there is a potential risk that Copilot may inadvertently expose sensitive organisational data to individuals who should no longer have access.
- **Copilot relevance:** Copilot relies on active user accounts to deliver personalized and contextual assistance. Only enabled accounts can interact with Copilot’s AI features and receive insights based on their usage and data.
- **Expected evidence/output:** List of users and their account status
- **Pass criteria:** When number of enabled account is more than 85 %
- **Fail criteria:** When number of enabled account is less than 85 %
- **Collection method:** powershell
- **Collector name:** powershell.account_enabled
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Account enabled
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 16. Restricted Access to Microsoft Entra Admin Centre

- **Parameter key:** `restricted_access_to_microsoft_entra_admin_centre`
- **Service:** Entra ID
- **Pillar/domain:** Best Practice
- **Severity:** info
- **Copilot blocker:** False
- **Scoring weight:** 1.0
- **Rule type:** configuration_value_check
- **Real description:** Access to the Microsoft Entra Admin Center is not restricted.
- **Risk:** Without strict access controls, unauthorised administrators may alter configurations that influence Copilot's data access across the tenant. This elevates the risk of misconfigurations or unintended over-permission of Copilot.
- **Copilot relevance:** No Direct Integration
- **Expected evidence/output:** To see its enabled or disabled
- **Pass criteria:** Non-Admin Users should not have access to Microsoft Entra Admin Centre
- **Fail criteria:** Non-Admin Users have access to Microsoft Entra Admin Centre
- **Collection method:** graph
- **Collector name:** graph.restricted_access_to_microsoft_entra_admin_centre
- **Graph endpoint:** /policies/authorizationPolicy
- **PowerShell mapping:** Not found in registry.
- **Portal mapping:** Not found in registry.
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/fundamentals/users-default-permissions

### 17. Self-Service Password Reset Authentication Method

- **Parameter key:** `self_service_password_reset_authentication_method`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** Self-Service Password Reset Authentication is enabled.
- **Risk:** Weak or poorly monitored self-service password reset (SSPR) methods increase the risk of account takeovers. If compromised accounts retain access to Copilot, sensitive data may be exposed or manipulated through AI-driven interactions.
- **Copilot relevance:** No Direct Integration
- **Expected evidence/output:** To see how many and what methods registered
- **Pass criteria:** Enabled to see how many methods registered
- **Fail criteria:** No methods enabled
- **Collection method:** graph
- **Collector name:** graph.self_service_password_reset_authentication_method
- **Graph endpoint:** https://graph.microsoft.com/beta/policies/authenticationMethodsPolicy
- **PowerShell mapping:** Not found in registry.
- **Portal mapping:** On the Admin portal , Admin Centers --> Identity --> Entra ID --> Password Reset --> Properties
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-enable-sspr

### 18. Tenant Collaboration Invitation

- **Parameter key:** `tenant_collaboration_invitations`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** configuration_value_check
- **Real description:** Set to 'Allow invitation to be sent to any domain' (Most inclusive).
- **Risk:** Uncontrolled collaboration invitations can cause tenant sprawl and broaden external access. Copilot may inadvertently access or generate responses using external content introduced through these collaborations, increasing the risk of data leakage and diminishing control over the information Copilot references or exposes.
- **Copilot relevance:** Proper management ensures that only authorized users can access data processed by Copilot
- **Expected evidence/output:** Setting configuration(AllowInvitesFrom)
- **Pass criteria:** When it is set to (Allow invitations only to the specified domain, Deny invitations to the specified domains)
- **Fail criteria:** When it is set to (Allow invitations to be sent to any domain )
- **Collection method:** powershell
- **Collector name:** powershell.tenant_collaboration_invitations
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Tenant Collaboration Invitations
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/external-id/external-collaboration-settings-configure

### 19. User Consent for Applications

- **Parameter key:** `user_consent_for_applications`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** configuration_value_check
- **Real description:** User consent for applications is not set.
- **Risk:** Permissive user consent settings can lead to widespread access to third-party applications, increasing the risk of data leakage and unauthorised use of Copilot features.
- **Copilot relevance:** Security by limiting access to only consent for approved application data ensures data protection.
- **Expected evidence/output:** Screenshot of User consent for application setting
- **Pass criteria:** When it is not set to Users can consent
- **Fail criteria:** When it is set to Users can consent
- **Collection method:** graph
- **Collector name:** graph.user_consent_for_applications
- **Graph endpoint:** /policies/authorizationPolicy
- **PowerShell mapping:** Not found in registry.
- **Portal mapping:** On the Admin portal , Admin Centers --> Identity --> Entra ID --> Enterprise apps --> Consent and Permissions --> User Consent Settings
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-user-consent

### 20. User Information

- **Parameter key:** `user_information`
- **Service:** Entra ID
- **Pillar/domain:** Best Practice
- **Severity:** low
- **Copilot blocker:** False
- **Scoring weight:** 2.0
- **Rule type:** boolean_gate
- **Real description:** User information details are not complete for all users.
- **Risk:** User profiles lacking accurate details such as department or role may compromise the relevance and precision of insights generated by Copilot. This misalignment can result in inappropriate content suggestions or accidental access to data outside a user's intended scope.
- **Copilot relevance:** If user dat is not correctly configured, copilot can provide irrevelent or wrong information.
- **Expected evidence/output:** List of all users and their detailed information
- **Pass criteria:** When the user information is complete for all users.
- **Fail criteria:** When the user information is not configured for all users
- **Collection method:** powershell
- **Collector name:** powershell.user_information
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** User Information
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 21. Users without MFA

- **Parameter key:** `users_without_mfa`
- **Service:** Entra ID
- **Pillar/domain:** Security
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** boolean_gate
- **Real description:** All MFA-capable users have MFA registered.
- **Risk:** The absence of MFA significantly weakens account security, increasing the risk of unauthorised access to user accounts. As Copilot can surface and interact with sensitive content across Microsoft 365 applications, accounts without MFA represent a heightened security vulnerability and may lead to unintentional data exposure.
- **Copilot relevance:** Enforcing MFA enhances security for Copilot access.
- **Expected evidence/output:** List of Users and MFA methods enrolled (UserPrincipalName, AuthMethodTypes)
- **Pass criteria:** When MFA is enabled for all the capable users
- **Fail criteria:** When MFA is not configured for some capable user
- **Collection method:** powershell
- **Collector name:** powershell.users_without_mfa
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Users without MFA
- **Portal mapping:** On the Admin portal, Admin Centers -> Identity --> Authentication Methods --> User Registration Details --> Download Export
- **Documentation URL:** https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-enable-azure-mfa

## Exchange Online (6)

### 1. External Storage providers in OWA

- **Parameter key:** `external_storage_providers_in_owa`
- **Service:** Exchange Online
- **Pillar/domain:** Security
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** boolean_gate
- **Real description:** Additional storage providers are allowed.
- **Risk:** Enabling third-party storage services in Outlook Web App may allow Copilot to access or recommend content stored outside the Microsoft 365 environment. This reduces control over data governance and increases the risk of exposing unsanctioned or non-compliant information through AI-generated insights.
- **Copilot relevance:** No Direct Integration
- **Expected evidence/output:** To see its enabled or disabled
- **Pass criteria:** When not enabled, users cannot connect third-party storage services to Outlook Web App and: Attach files from those services Share links to external files via email Access cloud-based documents directly from their emai
- **Fail criteria:** When enabled, users can connect third-party storage services to Outlook Web App and: Attach files from those services Share links to external files via email Access cloud-based documents directly from their emai
- **Collection method:** powershell
- **Collector name:** powershell.external_storage_providers_in_owa
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** External Storage Providers In OWA
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/outlook-on-the-web/owa-policies

### 2. Full Calendar Schedules able to be shared Externally

- **Parameter key:** `full_calendar_schedules_able_to_be_shared_externally`
- **Service:** Exchange Online
- **Pillar/domain:** Security
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** boolean_gate
- **Real description:** Policy for individual sharing is set to least information shared.
- **Risk:** Sharing full calendar access externally may enable Copilot to include sensitive scheduling information in its responses or meeting suggestions. This raises privacy concerns and increases the risk of organizational exposure through automated content summaries.
- **Copilot relevance:** No Direct Integration
- **Expected evidence/output:** To see its enabled or disabled
- **Pass criteria:** If False, calendar sharing is disabled across the organization, meaning users cannot share their calendars with anyone outside the organization.
- **Fail criteria:** If True, calendar sharing is enabled for the organization, allowing users to share their calendars with external users (or with internal users, depending on other settings).
- **Collection method:** powershell
- **Collector name:** powershell.full_calendar_schedules_able_to_be_shared_externally
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Full Calendar Schedules Able To Be Shared Externally
- **Portal mapping:** On the Exchange admin center, Organization --> Sharing --> Individual sharing.
- **Documentation URL:** Not found in registry.

### 3. Mailbox Storage usage

- **Parameter key:** `mailbox_storage_usage`
- **Service:** Exchange Online
- **Pillar/domain:** Best Practice
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** percentage_threshold
- **Real description:** All mailboxes are in good condition.
- **Risk:** Excessive mailbox storage in the absence of appropriate retention policies may lead Copilot to surface outdated or irrelevant content. Additionally, it increases processing overhead and the likelihood of sensitive legacy data being included in AI-generated responses.
- **Copilot relevance:** Monitoring storage ensures Copilot has smooth access to necessary data without delays.
- **Expected evidence/output:** Not found in registry.
- **Pass criteria:** When the active storage on mailbox is less than 75%
- **Fail criteria:** When the active storage on mailbox is more than 75%
- **Collection method:** powershell
- **Collector name:** powershell.mailbox_storage_usage
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Mailbox Storage usage
- **Portal mapping:** On the Microsoft 365 admin center, Reports --> Usage --> Exchange --> Mailbox usage. Review the mailbox usage report.
- **Documentation URL:** Not found in registry.

### 4. Mailbox status (Active/Inactive)

- **Parameter key:** `mailboxes_status_active_inactive`
- **Service:** Exchange Online
- **Pillar/domain:** Governance
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** percentage_threshold
- **Real description:** [X] users out of [Y]([Z]%) are active.
- **Risk:** Copilot retrieves data from active mailboxes to support features like email summarisation and task extraction; however, unused or poorly monitored mailboxes can increase the risk of exposing outdated, sensitive, or non-critical business data through its outputs.
- **Copilot relevance:** Active mailboxes are important because Copilot needs them to give helpful email-based support
- **Expected evidence/output:** List of active mailboxes in the tenant
- **Pass criteria:** When the number active mailboxes are more than 85%
- **Fail criteria:** When the number active mailboxes are less than 85%
- **Collection method:** powershell
- **Collector name:** powershell.mailboxes_status_active_inactive
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Mailboxes Status (Active/Inactive)
- **Portal mapping:** On the Microsoft 365 admin center, Reports --> Usage --> Exchange --> Email activity. Review the email activity report.
- **Documentation URL:** https://learn.microsoft.com/en-us/exchange/recipients/mailboxes

### 5. Number of Emails read/received

- **Parameter key:** `number_of_emails_read_received`
- **Service:** Exchange Online
- **Pillar/domain:** Best Practice
- **Severity:** info
- **Copilot blocker:** False
- **Scoring weight:** 1.0
- **Rule type:** percentage_threshold
- **Real description:** [X] out of [Y]([Z]%) have read [W]% of their mail.
- **Risk:** Copilot may analyse read emails to generate context-aware suggestions and insights. If these emails contain sensitive information, there is a risk of data exposure in the absence of adequate classification, retention, and monitoring controls.
- **Copilot relevance:** High engagement with emails suggests that Copilot's email summarization and drafting features will be beneficial.
- **Expected evidence/output:** Number of emails read by the users
- **Pass criteria:** More than 75% of users have read more than 70% of their emails.
- **Fail criteria:** Less than 75% of users have read more than 70% of their emails.
- **Collection method:** powershell
- **Collector name:** powershell.number_of_emails_read_received
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Number of emails read/received
- **Portal mapping:** On the Microsoft 365 admin center, Reports --> Usage --> Exchange --> Email activity. Review the email activity report.
- **Documentation URL:** Not found in registry.

### 6. Number of emails sent

- **Parameter key:** `number_of_emails_sent`
- **Service:** Exchange Online
- **Pillar/domain:** Best Practice
- **Severity:** info
- **Copilot blocker:** False
- **Scoring weight:** 1.0
- **Rule type:** count_threshold
- **Real description:** [X] out of [Y]([Z]%) have sent more than 30 mails.
- **Risk:** Sent emails are included in the dataset accessible to Copilot for analysing communication patterns. Without strong governance, Copilot may inadvertently reuse sensitive or private correspondence in its suggestions, summaries, or generated responses.
- **Copilot relevance:** High outgoing email activity shows Copilot’s drafting and reply suggestions can boost efficiency.
- **Expected evidence/output:** Number of emails sent by the users
- **Pass criteria:** When the number of emails sent by the users are more than 30
- **Fail criteria:** When the number of emails sent by the users are less than 30
- **Collection method:** powershell
- **Collector name:** powershell.number_of_emails_sent
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Number of emails sent
- **Portal mapping:** On the Microsoft 365 admin center, Reports --> Usage --> Exchange --> Email activity. Review the email activity report.
- **Documentation URL:** Not found in registry.

## Microsoft Purview (8)

### 1. Audit Log Retention Duration

- **Parameter key:** `audit_log_retention_duration`
- **Service:** Microsoft Purview
- **Pillar/domain:** Governance
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** policy_existence_check
- **Real description:** No Audit log retention duration.
- **Risk:** Copilot relies on extended retention of user activity logs to derive behavioural insights. Retaining audit logs for insufficient durations may result in the loss of critical risk signals and contextual history, whereas excessively long retention periods can increase the risk of data exposure if adequate safeguards are not in place.
- **Copilot relevance:** Sufficient retention ensures visibility into how Copilot is being used, helping detect misuse or data access anomalies.
- **Expected evidence/output:** List of Audit log retention policies
- **Pass criteria:** When policies are set up
- **Fail criteria:** When no policies are set up
- **Collection method:** graph
- **Collector name:** graph.audit_log_retention_duration
- **Graph endpoint:** /auditLogs/directoryAudits
- **PowerShell mapping:** Not found in registry.
- **Portal mapping:** On the Purview portal, Solutions --> Audit --> Policies
- **Documentation URL:** https://learn.microsoft.com/en-us/purview/audit-log-retention-policies

### 2. Audit Logs Enabled

- **Parameter key:** `audit_logs_enabled`
- **Service:** Microsoft Purview
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** Audit logs are not currently enabled.
- **Risk:** Audit logs play a crucial role in monitoring and tracing AI interactions. Disabling audit logging prevents the review and tracking of Copilot activities, thereby hindering incident response capabilities and increasing the likelihood of undetected data misuse or unauthorized behaviour.
- **Copilot relevance:** Audit logs help track who used Copilot, when, and where (e.g., in which repository or organization).
- **Expected evidence/output:** Audit logs enabled or not - True or False
- **Pass criteria:** If audit logs enabled this will hunt the results for query
- **Fail criteria:** If audit logs not enabled we cannot get the logs for the query
- **Collection method:** powershell
- **Collector name:** powershell.audit_logs_enabled
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Audit Logs enabled
- **Portal mapping:** On the Purview portal, Solutions --> Audit --> Search
- **Documentation URL:** https://learn.microsoft.com/en-us/purview/audit-log-enable-disable

### 3. Compliance Score Overview

- **Parameter key:** `compliance_score_overview`
- **Service:** Microsoft Purview
- **Pillar/domain:** Governance
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** percentage_threshold
- **Real description:** Compliance score is only [X]% which is less than the recommended industry standard (80%).
- **Risk:** A low compliance score may signal inadequate policy enforcement, indicating weak controls over the data accessible to Copilot. This can result in the inadvertent exposure of non-compliant or unprotected content through AI-driven recommendations.
- **Copilot relevance:** A higher compliance score means better data control, helping Copilot work safely and within rules.
- **Expected evidence/output:** Compliance Score percentage of the tenant
- **Pass criteria:** When it is more than or equal to 80%
- **Fail criteria:** When it is less than 80%
- **Collection method:** graph
- **Collector name:** graph.compliance_score_overview
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Not found in registry.
- **Portal mapping:** On the Purview portal, select Home on the left pane and scroll down to see the compliance score
- **Documentation URL:** Not found in registry.

### 4. DLP Rules configured

- **Parameter key:** `dlp_rules_configured`
- **Service:** Microsoft Purview
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** Data Loss Prevention (DLP) rules are not configured.
- **Risk:** Copilot has the capability to access and present sensitive content across Microsoft 365 applications. In the absence of well-defined Data Loss Prevention (DLP) policies, it may inadvertently expose or share sensitive information, potentially violating data protection and compliance requirements.
- **Copilot relevance:** DLP can detect if Copilot-suggested code includes secrets, PII, or confidential patterns (e.g., keys, passwords).
- **Expected evidence/output:** List of DLP rules applied and configured with settings
- **Pass criteria:** If DLP rules is configured and applied correctly to exchange,sharepoint,teams etc
- **Fail criteria:** If DLP rules is not configured and applied correctly to exchange,sharepoint,teams etc
- **Collection method:** powershell
- **Collector name:** powershell.dlp_rules_configured
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** DLP rules configured
- **Portal mapping:** On the Purview portal, Solutions --> Data Loss Prevention --> Policies
- **Documentation URL:** https://learn.microsoft.com/en-us/purview/dlp-create-deploy-policy

### 5. Information Protection Labels applied

- **Parameter key:** `information_protection_labels_applied`
- **Service:** Microsoft Purview
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** Information Protection labels have not been applied.
- **Risk:** Without the consistent application of sensitivity and protection labels, Copilot may inadvertently expose unclassified sensitive data through search, summarization, or recommendations. These labels establish critical boundaries for AI processing, and their absence undermines the organization's overall data protection posture.
- **Copilot relevance:** Example: If a document is labeled as Confidential, Copilot will ensure that it doesn’t share or use this document in a summary unless the user has the appropriate permissions, thus reducing the risk of data leakage
- **Expected evidence/output:** List of labels applied and configured with settings
- **Pass criteria:** If labels is configured and applied
- **Fail criteria:** If labels is not configured and applied
- **Collection method:** powershell
- **Collector name:** powershell.information_protection_labels_applied
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Information Protection Labels applied
- **Portal mapping:** On the Purview portal, Solutions --> Information Protection --> Policies
- **Documentation URL:** Not found in registry.

### 6. Secure Score Percentage

- **Parameter key:** `secure_score_percentage`
- **Service:** Microsoft Purview
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** percentage_threshold
- **Real description:** Secure score is only [X]% which is less than the recommended industry standard (80%).
- **Risk:** A low secure score reflects weak security practices, heightening the risk of data leakage or misuse when Copilot accesses tenant data. It indicates potential misconfigurations or policy gaps that may impact Copilot's security posture.
- **Copilot relevance:** A higher Secure Score means stronger security, creating a safer environment for Copilot.
- **Expected evidence/output:** Secure Score Percentage of the Tenant
- **Pass criteria:** When it is more than or equal to 80%
- **Fail criteria:** When it is less than 80%
- **Collection method:** graph
- **Collector name:** graph.secure_score_percentage
- **Graph endpoint:** /security/secureScores
- **PowerShell mapping:** Not found in registry.
- **Portal mapping:** From Defender Portal (security.microsoft.com)
- **Documentation URL:** https://learn.microsoft.com/en-us/microsoft-365/security/defender/microsoft-secure-score

### 7. Sensitivity Labels applied to Teams

- **Parameter key:** `sensitivity_labels_applied_to_teams`
- **Service:** Microsoft Purview
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** No sensitivity labels have been applied to Teams.
- **Risk:** Without proper labelling of Teams, Copilot may access or surface sensitive content without the necessary controls. This elevates the risk of data leakage, particularly in cross-team suggestions or summaries.
- **Copilot relevance:** Example: If a document is labeled as Confidential, Copilot will ensure that it doesn’t share or use this document in a summary unless the user has the appropriate permissions, thus reducing the risk of data leakage
- **Expected evidence/output:** List of labels applied and configured with Teams settings
- **Pass criteria:** If labels is configured and applied
- **Fail criteria:** If labels is not configured and applied
- **Collection method:** powershell
- **Collector name:** powershell.sensitivity_labels_applied_to_teams
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Sensitivity Labels applied to Teams
- **Portal mapping:** Failed if Sensitivity Labels configured and applied parameter is failed
- **Documentation URL:** https://learn.microsoft.com/en-us/purview/sensitivity-labels-teams-groups-sites

### 8. Sensitivity Labels configured and applied

- **Parameter key:** `sensitivity_labels_configured_and_applied`
- **Service:** Microsoft Purview
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** Sensitivity labels are not applied.
- **Risk:** Even when labels are configured, inconsistent application may prevent Copilot from respecting intended data boundaries. This can lead to partial or unintended access to confidential information during content generation.
- **Copilot relevance:** "Sites labeled with sensitive information (e.g., confidential or highly confidential) ensure that Copilot can only access and generate insights from data the user is permitted to view. Example: A Confidential – HR label ensures Copilot won't generate summaries or responses based on HR-related documents unless the user has the appropriate permissions to view that content. Adding appropriate labels gives clarity on copilot assessment to have this done."
- **Expected evidence/output:** List of labels applied and configured with settings
- **Pass criteria:** If labels is configured and applied
- **Fail criteria:** If labels is not configured and applied
- **Collection method:** powershell
- **Collector name:** powershell.sensitivity_labels_configured_and_applied
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Sensitivity Labels configured and applied
- **Portal mapping:** On the Purview portal, Solutions --> Information Protection --> Policies. If no policies are configured then the parameter is failed
- **Documentation URL:** https://learn.microsoft.com/en-us/purview/create-sensitivity-labels

## Microsoft Teams (16)

### 1. Active/Inactive Teams Users

- **Parameter key:** `activer_inactive_teams_users`
- **Service:** Microsoft Teams
- **Pillar/domain:** Best Practice
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** percentage_threshold
- **Real description:** 0 out of [X] team users are active ([Y]%).
- **Risk:** Inactive users who maintain access may have their content surfaced by Copilot within collaborative environments. This raises the risk of reintroducing outdated or irrelevant information and, more critically, the potential malicious exploitation of their accounts to misuse AI capabilities.
- **Copilot relevance:** Knowing who is active helps deploy Copilot to users who will benefit the most.
- **Expected evidence/output:** List of inactive teams user
- **Pass criteria:** When the number of inactive Teams users are less than 15% for the tenant
- **Fail criteria:** When the number of active Teams users are more than 15% for the tenant
- **Collection method:** powershell
- **Collector name:** powershell.activer_inactive_teams_users
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Activer/Inactive Teams users
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 2. Active/Inactive teams

- **Parameter key:** `active_inactive_teams`
- **Service:** Microsoft Teams
- **Pillar/domain:** Security
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** configuration_value_check
- **Real description:** No teams are inactive.
- **Risk:** Many active Teams expands the data pool that Copilot interacts with. Without effective classification and access controls, this broad surface area increases the likelihood of irrelevant or sensitive information being exposed to unintended users.
- **Copilot relevance:** Cleaning up inactive channels removes clutter, helping Copilot focus on useful conversations.
- **Expected evidence/output:** List of inactive teams channels
- **Pass criteria:** When a tenant does not have inactive teams
- **Fail criteria:** When a tenant has inactive teams
- **Collection method:** powershell
- **Collector name:** powershell.active_inactive_teams
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Active /Inactive teams
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 3. Copilot Integration Enabled

- **Parameter key:** `copilot_integration_enabled`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** Copilot integration is enabled.
- **Risk:** If Copilot is not fully enabled across core workloads like Teams, Word, or Outlook, it signals incomplete readiness and limits Copilot's utility. Gaps in licensing, onboarding, or workload configuration can reduce Copilot's effectiveness and may lead to inconsistent user experiences or missed productivity gains.
- **Copilot relevance:** To utilize Copilot features in teams app, It is rquired Copilot to have necessary configurations in place.
- **Expected evidence/output:** Configuration of Teams app (Copilot) integration with teams. (Identity, CopilotFromHomeTenant)
- **Pass criteria:** When it is enabled
- **Fail criteria:** When it is disabled
- **Collection method:** powershell
- **Collector name:** powershell.copilot_integration_enabled
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Copilot integration enabled
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 4. Guest access Enabled/Disabled

- **Parameter key:** `guest_access_enabled_disabled`
- **Service:** Microsoft Teams
- **Pillar/domain:** Security
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** boolean_gate
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** Disabling guest access prevents external users from interacting with Copilot and sensitive data.
- **Expected evidence/output:** Whether Guest access is enabled or disabled.
- **Pass criteria:** When it is disabled
- **Fail criteria:** When it is enabled
- **Collection method:** powershell
- **Collector name:** powershell.guest_access_enabled_disabled
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Guest access enabled / disabled
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 5. Meeting Policies Configuration

- **Parameter key:** `meeting_policies_configuration`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** configuration_value_check
- **Real description:** Recommended settings are configured.
- **Risk:** Inadequate or inconsistent meeting policies may allow Copilot to access recordings, chats, or transcriptions from meetings that were not intended for retention. This elevates the risk of private or confidential discussions being inadvertently surfaced in the future.
- **Copilot relevance:** Proper configurations ensure that Copilot can access necessary meeting data while maintaining compliance.
- **Expected evidence/output:** List of Teams meetings policies. (Identity, AllowCloudRecording, AutoAdmittedUsers, AllowMeetingReactions, MeetingChatEnabledType, AllowTranscription, AllowIPVideo, ExplicitRecordingConsent, AllowExternalNonTrustedMeetingChat, AllowBreakoutRooms)
- **Pass criteria:** When recommended settings are setup
- **Fail criteria:** When recommended settings aren't setup
- **Collection method:** powershell
- **Collector name:** powershell.meeting_policies_configuration
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Meeting Policies configuration
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 6. Meeting Recording Retention Policies

- **Parameter key:** `meeting_recording_retention_policies`
- **Service:** Microsoft Teams
- **Pillar/domain:** Best Practice
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** boolean_gate
- **Real description:** It is enabled and meeting recordings are set to automatically expire after [X] days.
- **Risk:** Without strict enforcement of retention policies, Copilot may continuously process and reference outdated recordings. This poses a risk of inappropriate reuse of sensitive historical meeting data, potentially resulting in violations of organisational compliance standards.
- **Copilot relevance:** Ensures that Copilot has access to relevant meeting data for generating summaries or insights by expiring recordings out of date.
- **Expected evidence/output:** From Teams meeting policies configuration of recording expiry duration.(Identity, RecordingStorageMode, NewMeetingRecordingExpirationDays)
- **Pass criteria:** When it is enabled
- **Fail criteria:** When it is disabled
- **Collection method:** powershell
- **Collector name:** powershell.meeting_recording_retention_policies
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Meeting recording retention policies
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 7. Meeting Transcription enabled

- **Parameter key:** `meeting_transcription_enabled`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** boolean_gate
- **Real description:** Meeting transcription is enabled.
- **Risk:** Enabled transcriptions create accessible content that Copilot can process. Without appropriate governance, this heightens the risk of confidential spoken information being incorporated into Copilot's suggestions, potentially violating privacy boundaries.
- **Copilot relevance:** Copilot requires transcripts to analyze and generate meeing summaries and action items
- **Expected evidence/output:** From Teams meeting policies configuration of transcription. (Identity, AllowTranscription)
- **Pass criteria:** When it is enabled
- **Fail criteria:** When it is disabled
- **Collection method:** powershell
- **Collector name:** powershell.meeting_transcription_enabled
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Meeting transcription enabled
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/microsoftteams/cloud-recording

### 8. Minimum number of Owners

- **Parameter key:** `minimum_number_of_owners`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** count_threshold
- **Real description:** There are no teams that have less than 2 owners.
- **Risk:** Teams or groups lacking a minimum number of designated owners risk becoming orphaned, complicating the management and oversight of data surfaced by Copilot. This absence of ownership can lead to unmanaged access to legacy or sensitive information.
- **Copilot relevance:** Prevents orphaned teams, ensuring that Copilot has access to managed and active resources.
- **Expected evidence/output:** List of Teams with the number of owners and also the number of teams with less than 2 owners(Team Name, Number of Owners, TotalTeamswithLessThan2Owners)
- **Pass criteria:** When all teams have more than 1 Owner
- **Fail criteria:** When teams have less than 2 Owner
- **Collection method:** powershell
- **Collector name:** powershell.minimum_number_of_owners
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Minimum number of owners
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 9. Orphan Teams

- **Parameter key:** `orphan_teams`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** boolean_gate
- **Real description:** There are no orphan teams.
- **Risk:** Orphaned Teams without owners may still hold sensitive content accessible by Copilot. Without proper oversight, these Teams become unmanaged data sources, raising the risk of outdated or confidential information being surfaced unintentionally.
- **Copilot relevance:** Orphaned teams may contain outdated or unmanaged data, which could affect Copilot's outputs.
- **Expected evidence/output:** List and Number of Orphan teams.(TeamName,TeamID,Total Orphan Teams)
- **Pass criteria:** When there are no orphan teams
- **Fail criteria:** When orphan teams are present
- **Collection method:** powershell
- **Collector name:** powershell.orphan_teams
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Orphan Teams
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 10. Teams - Channel Email Addresses

- **Parameter key:** `teams_channel_email_addresses`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** low
- **Copilot blocker:** False
- **Scoring weight:** 2.0
- **Rule type:** configuration_value_check
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** Copilot can help write the SMTP/email code that delivers messages to the Teams channel email address
- **Expected evidence/output:** AllowEmailIntoChannel - True means Users can send emails to a channel email address AllowEmailIntoChannel - False means Users cannot send emails to a channel email address
- **Pass criteria:** This will restrict Teams channels to allow accepting channel emails only from these Restricted Domains
- **Fail criteria:** This will not restrict Teams channels to allow accepting channel emails only from these Restricted Domains
- **Collection method:** powershell
- **Collector name:** powershell.teams_channel_email_addresses
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Teams - Channel Email Addresses
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 11. Teams - File Storage Option

- **Parameter key:** `teams_file_storage_option`
- **Service:** Microsoft Teams
- **Pillar/domain:** Security
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** configuration_value_check
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** Ensures that Copilot accesses files stored in approved and secure locations.
- **Expected evidence/output:** Third Party storge should be disabled
- **Pass criteria:** When the files are stored within the Microsoft suit
- **Fail criteria:** When the files are stored outside the Microsoft suit
- **Collection method:** powershell
- **Collector name:** powershell.teams_file_storage_option
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Teams - File Storage Option
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/microsoftteams/sharepoint-onedrive-interact

### 12. Teams - Lobby Bypass

- **Parameter key:** `teams_lobby_bypass`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** configuration_value_check
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** No Direct Integration
- **Expected evidence/output:** • AllowParticipantsToBypassLobby: Specifies whether participants can bypass the lobby when joining the meeting. The possible values are: o Always: Participants can always bypass the lobby. o Organizer: Only the organizer can bypass the lobby (default). o Never: No one can bypass the lobby.
- **Pass criteria:** Specifies whether participants can bypass the lobby when joining the meeting - Never
- **Fail criteria:** Specifies whether participants can bypass the lobby when joining the meeting - Anyone
- **Collection method:** powershell
- **Collector name:** powershell.teams_lobby_bypass
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Teams - Lobby Bypass
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/microsoftteams/meeting-policies-participants-and-guests

### 13. Teams - Meeting Chat

- **Parameter key:** `teams_meeting_chat`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** boolean_gate
- **Real description:** Meeting chats are enabled on global policy.
- **Risk:** Meeting chat messages frequently include important contextual information and follow-up actions. When retained and accessible, Copilot may utilize this data to generate summaries or recommendations. Without adequate governance controls, there is a risk that sensitive information casually shared in these chats could be inadvertently exposed by Copilot.
- **Copilot relevance:** No Direct Integration
- **Expected evidence/output:** • AllowMeetingChat: This setting controls whether chat is allowed during and after meetings. Possible values include: o Enabled: Participants are allowed to use chat during and after the meeting. o Disabled: Meeting chat is disabled. o In-meeting only: Chat is allowed only during the meeting but not after the meeting ends.
- **Pass criteria:** Enabled: Participants are allowed to use chat during and after the meeting.
- **Fail criteria:** Disabled: Meeting chat is disabled
- **Collection method:** powershell
- **Collector name:** powershell.teams_meeting_chat
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Teams - Meeting Chat
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 14. Teams with External Users

- **Parameter key:** `teams_with_external_users`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** percentage_threshold
- **Real description:** There are no teams with external users.
- **Risk:** External users in Teams have access to shared files, chats, and meeting content that Copilot can process. This increases the risk of sensitive or proprietary information being included in AI-generated outputs. Without strict controls, external collaboration can blur tenant boundaries and compromise organisational data privacy.
- **Copilot relevance:** Teams with external users involve sharing data outside the organization, requiring secure management for Copilot to work safely.
- **Expected evidence/output:** List of external users
- **Pass criteria:** When it is less than 20%
- **Fail criteria:** When it is more than to 20%
- **Collection method:** powershell
- **Collector name:** powershell.teams_with_external_users
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Teams with external users
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 15. Teams with guest as owner

- **Parameter key:** `teams_with_external_guest_as_owner`
- **Service:** Microsoft Teams
- **Pillar/domain:** Security
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** configuration_value_check
- **Real description:** No teams have external user assigned as owner.
- **Risk:** Proper ownership control reduces the risk of external manipulation of team settings or misuse of Copilot features within Microsoft Teams.
- **Copilot relevance:** External guest owners can influence Teams content and access boundaries that Copilot may use for summaries and responses.
- **Expected evidence/output:** No Teams have an external guest assigned as owner
- **Pass criteria:** No Teams have external guests as owners
- **Fail criteria:** One or more Teams have external guests as owners
- **Collection method:** powershell
- **Collector name:** powershell.teams_with_external_guest_as_owner
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Teams with external guest as owner
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 16. Third Party Apps allowed

- **Parameter key:** `third_party_apps_allowed`
- **Service:** Microsoft Teams
- **Pillar/domain:** Governance
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** boolean_gate
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** No Direct Integration
- **Expected evidence/output:** • Get the value of Custom Apps Setting. The value in the example is False, so custom apps are unavailable in the organization's app
- **Pass criteria:** Disabled- custom apps are unavailable in the organization's app
- **Fail criteria:** Enabled- custom apps are available in the organization's app
- **Collection method:** powershell
- **Collector name:** powershell.third_party_apps_allowed
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Third-party apps allowed
- **Portal mapping:** On the Teams admin center, Teams apps --> Manage apps --> Actions dropdown --> Org-wide app settings. Scroll down to find Third-party apps.
- **Documentation URL:** https://learn.microsoft.com/en-us/microsoftteams/manage-apps

## OneDrive for Business (3)

### 1. Days to retain a deleted user's OneDrive

- **Parameter key:** `days_to_retain_a_deleted_user_s_onedrive`
- **Service:** OneDrive for Business
- **Pillar/domain:** Governance
- **Severity:** low
- **Copilot blocker:** False
- **Scoring weight:** 2.0
- **Rule type:** configuration_value_check
- **Real description:** OneDrive retention for deleted users is set to [X] days.
- **Risk:** Not found in registry.
- **Copilot relevance:** Retention settings affect whether deleted-user content remains recoverable, auditable, and governed before Copilot rollout.
- **Expected evidence/output:** Deleted user's OneDrive retention is configured for an approved duration
- **Pass criteria:** Deleted user's OneDrive retention period is configured
- **Fail criteria:** Deleted user's OneDrive retention period is not configured or is below the expected baseline
- **Collection method:** powershell
- **Collector name:** powershell.days_to_retain_a_deleted_user_s_onedrive
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Days to retain a deleted user's OneDrive
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 2. External Sharing Settings

- **Parameter key:** `external_sharing_settings`
- **Service:** OneDrive for Business
- **Pillar/domain:** Security
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** configuration_value_check
- **Real description:** External sharing is set to only people in your organization.
- **Risk:** Not found in registry.
- **Copilot relevance:** Restricting external sharing reduces the risk of data leaks through Copilot-generated content.
- **Expected evidence/output:** Level of external sharing configured
- **Pass criteria:** When it is set to New and existing guests or more restrictive
- **Fail criteria:** When it is set to Anyone(Least restrictive)
- **Collection method:** powershell
- **Collector name:** powershell.external_sharing_settings
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** External sharing settings
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 3. Total Active users on OneDrive

- **Parameter key:** `total_active_users_on_onedrive`
- **Service:** OneDrive for Business
- **Pillar/domain:** Governance
- **Severity:** info
- **Copilot blocker:** False
- **Scoring weight:** 1.0
- **Rule type:** percentage_threshold
- **Real description:** [X] out of [Y] ([Z]%) users have shown activity in the last 2 months.
- **Risk:** Not found in registry.
- **Copilot relevance:** Total active users on OneDrive show how many people use it, indicating how much data Copilot can access to assist users.
- **Expected evidence/output:** List of Active users on OneDrive
- **Pass criteria:** When the total active user on OneDrive are more than than 80%
- **Fail criteria:** When the total active user on OneDrive are more than than 80%
- **Collection method:** powershell
- **Collector name:** powershell.total_active_users_on_onedrive
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Total active users on OneDrive
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

## SharePoint Online (11)

### 1. Active Sites count

- **Parameter key:** `active_sites_count`
- **Service:** SharePoint Online
- **Pillar/domain:** Governance
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** percentage_threshold
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** Active sites give Copilot more data to work with, making it more useful.
- **Expected evidence/output:** List of active SharePoint site in the tenant
- **Pass criteria:** When the number active sites on SharePoint are more than 85%
- **Fail criteria:** When the number active sites on SharePoint are less than 85%
- **Collection method:** graph
- **Collector name:** graph.active_sites_count
- **Graph endpoint:** /reports/getSharePointSiteUsageDetail(period='D30')
- **PowerShell mapping:** Active Sites count
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 2. Active Users on SharePoint

- **Parameter key:** `active_users_on_sharepoint`
- **Service:** SharePoint Online
- **Pillar/domain:** Governance
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** percentage_threshold
- **Real description:** [X] out of [Y]([Z]%) users are active.
- **Risk:** Not found in registry.
- **Copilot relevance:** Active SharePoint use means lots of data for Copilot to provide smart, helpful assistance and boost productivity.
- **Expected evidence/output:** List of active users on SharePoint in the tenant
- **Pass criteria:** When the number active users on SharePoint are more than 85%
- **Fail criteria:** When the number active users on SharePoint are less than 85%
- **Collection method:** powershell
- **Collector name:** powershell.active_users_on_sharepoint
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Active users on SharePoint
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 3. Expiration Policy for Anyone links

- **Parameter key:** `expiration_policy_for_anyone_links`
- **Service:** SharePoint Online
- **Pillar/domain:** Security
- **Severity:** high
- **Copilot blocker:** False
- **Scoring weight:** 4.0
- **Rule type:** configuration_value_check
- **Real description:** Expiration policy is set for [X] days.
- **Risk:** Not found in registry.
- **Copilot relevance:** Expiring anonymous links limits long-lived content exposure that Copilot could otherwise index or surface.
- **Expected evidence/output:** Anyone links have an expiration policy configured
- **Pass criteria:** Anyone links expire within the approved duration
- **Fail criteria:** Anyone links do not expire or exceed the approved duration
- **Collection method:** powershell
- **Collector name:** powershell.expiration_policy_for_anyone_links
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Expiration Policy for Anyone links
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 4. Inactive Site Policies

- **Parameter key:** `inactive_site_policies`
- **Service:** SharePoint Online
- **Pillar/domain:** Best Practice
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** percentage_threshold
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** Inactive sites can contain stale or ungoverned content. Inactive site policies reduce irrelevant data surfaced by Copilot.
- **Expected evidence/output:** Inactive site policy is configured
- **Pass criteria:** Inactive site policies are configured
- **Fail criteria:** Inactive site policies are not configured
- **Collection method:** powershell
- **Collector name:** powershell.inactive_site_policies
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Inactive site policies
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 5. Permission Settings for anyone links

- **Parameter key:** `permission_setting_for_anyone_links`
- **Service:** SharePoint Online
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** False
- **Scoring weight:** 5.0
- **Rule type:** configuration_value_check
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** Anyone links with broad permissions can expose SharePoint content that Copilot may index or surface to unintended users.
- **Expected evidence/output:** Anyone links are disabled or restricted to least privilege permissions
- **Pass criteria:** Anyone links are disabled or restricted to view-only least privilege access
- **Fail criteria:** Anyone links allow edit or overly permissive access
- **Collection method:** powershell
- **Collector name:** powershell.permission_setting_for_anyone_links
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Permission Settings for anyone links
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/sharepoint/turn-external-sharing-on-or-off

### 6. Sensitive SharePoint sites excluded from Copilot

- **Parameter key:** `getting_all_sites_with_sensitivity_keywords_on_a_tenant`
- **Service:** SharePoint Online
- **Pillar/domain:** Security
- **Severity:** info
- **Copilot blocker:** False
- **Scoring weight:** 1.0
- **Rule type:** configuration_value_check
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** Copilot can help to gather information related to sensitive files etc
- **Expected evidence/output:** Not found in registry.
- **Pass criteria:** This will give accurate result for sensitivity sites if anything exist
- **Fail criteria:** If there is no sites with sensitivity keywords then we can consider there are no sites with sensitive information.
- **Collection method:** powershell
- **Collector name:** powershell.getting_all_sites_with_sensitivity_keywords_on_a_tenant
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Getting all sites with Sensitivity keywords on a Tenant
- **Portal mapping:** Not found in registry.
- **Documentation URL:** Not found in registry.

### 7. SharePoint - Modern Authentication

- **Parameter key:** `sharepoint_modern_authentication`
- **Service:** SharePoint Online
- **Pillar/domain:** Best Practice
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** boolean_gate
- **Real description:** Apps using legacy authentication are disabled.
- **Risk:** Not found in registry.
- **Copilot relevance:** Modern authentication improves security, keeping Copilot’s access to SharePoint data safe.
- **Expected evidence/output:** Mordern Authentication method should be enabled
- **Pass criteria:** When it is enabled
- **Fail criteria:** When it is disabled
- **Collection method:** powershell
- **Collector name:** powershell.sharepoint_modern_authentication
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** SharePoint - Modern Authentication
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 8. SharePoint and OneDrive Guest Access Expiry

- **Parameter key:** `sharepoint_and_onedrive_guest_access_expiry`
- **Service:** SharePoint Online
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** Expiration Policy for SharePoint and OneDrive guest access links is enabled and set for [X] days.
- **Risk:** Not found in registry.
- **Copilot relevance:** No Direct Integration
- **Expected evidence/output:** SharingExpirationPeriod - how many days
- **Pass criteria:** SharingExpirationPeriod: The number of days the guest access link will be valid before it expires (if expiration is enabled).
- **Fail criteria:** SharingExpirationPeriod not enabled
- **Collection method:** powershell
- **Collector name:** powershell.sharepoint_and_onedrive_guest_access_expiry
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** SharePoint & OneDrive Guest Access Expiry
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 9. Sharing Settings (External/Internal)

- **Parameter key:** `sharing_settings_external_internal`
- **Service:** SharePoint Online
- **Pillar/domain:** Security
- **Severity:** critical
- **Copilot blocker:** True
- **Scoring weight:** 5.0
- **Rule type:** boolean_gate
- **Real description:** External sharing is disabled.
- **Risk:** Not found in registry.
- **Copilot relevance:** Restricting access to sharepoint and onedrive documents, prevents unauthorized access to data.
- **Expected evidence/output:** Configuration of External sharing setting preventing external user from resharing (Allow Guests to Share Items They Don't Own)
- **Pass criteria:** When settings enabled
- **Fail criteria:** When restrictive setting no set up
- **Collection method:** powershell
- **Collector name:** powershell.sharing_settings_external_internal
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Sharing Settings (External/Internal)
- **Portal mapping:** Using Script
- **Documentation URL:** https://learn.microsoft.com/en-us/sharepoint/external-sharing-overview

### 10. Site Ownership policies

- **Parameter key:** `site_ownership_policies`
- **Service:** SharePoint Online
- **Pillar/domain:** Governance
- **Severity:** medium
- **Copilot blocker:** False
- **Scoring weight:** 3.0
- **Rule type:** configuration_value_check
- **Real description:** Not found in registry.
- **Risk:** Not found in registry.
- **Copilot relevance:** Site ownership helps ensure content governance and accountability for information Copilot can access.
- **Expected evidence/output:** Site ownership policies are configured
- **Pass criteria:** Site ownership policies are configured and sites have accountable owners
- **Fail criteria:** Site ownership policies are not configured or sites lack accountable ownership
- **Collection method:** powershell
- **Collector name:** powershell.site_ownership_policies
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Site Ownership policies
- **Portal mapping:** Using Script
- **Documentation URL:** Not found in registry.

### 11. Storage Quota Consumption

- **Parameter key:** `storage_quota_consumption`
- **Service:** SharePoint Online
- **Pillar/domain:** Governance
- **Severity:** info
- **Copilot blocker:** False
- **Scoring weight:** 1.0
- **Rule type:** percentage_threshold
- **Real description:** Total storage consumption of the tenant is [X] GB out of [Y] TB.
- **Risk:** Not found in registry.
- **Copilot relevance:** Monitoring storage ensures Copilot can access data smoothly without performance problems.
- **Expected evidence/output:** Details of SharePoint storage which is utilized
- **Pass criteria:** When it is less than 90%
- **Fail criteria:** When it is more than or equal to 90%
- **Collection method:** powershell
- **Collector name:** powershell.storage_quota_consumption
- **Graph endpoint:** Not found in registry.
- **PowerShell mapping:** Storage Quota consumption
- **Portal mapping:** On the SharePoint admin center, Sites --> Active sites. Review the storage usage displayed at the top right of the page.
- **Documentation URL:** Not found in registry.
