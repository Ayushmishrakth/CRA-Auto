# PowerShell Connectivity Report

Generated: 2026-06-02

This validation checks whether non-interactive delegated PowerShell context is already available on the runtime host. It does not start browser or device-code authentication.

| Service | Connection | Command execution |
| --- | --- | --- |
| Exchange Online | Success | Succeeded |
| Purview | Failed | Failed |
| SharePoint Online | Success | Succeeded |
| PnP PowerShell | Failed | Failed |

## Details

| Service | Return Code | Stdout | Stderr |
| --- | --- | --- | --- |
| Exchange Online | 0 |  |  |
| Purview | 1 |  | Get-Command : The term 'Get-DlpCompliancePolicy' is not recognized as the name of a cmdlet, function, script file, or 
operable program. Check the spelling of the name, or if a path was included, verify that the path is correct and try 
again.
At line:1 char:59
+ ... ction Stop; Get-Command Get-DlpCompliancePolicy -ErrorAction Stop / S ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (Get-DlpCompliancePolicy:String) [Get-Command], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException,Microsoft.PowerShell.Commands.GetCommandCommand |
| SharePoint Online | 0 | WARNING: The names of some imported commands from the module 'Microsoft.Online.SharePoint.PowerShell' include 
unapproved verbs that might make them less discoverable. To find the commands with unapproved verbs, run the 
Import-Module command again with the Verbose parameter. For a list of approved verbs, type Get-Verb.
Get-SPOTenant |  |
| PnP PowerShell | 1 |  | Import-Module : The version of Windows PowerShell on this computer is '5.1.26100.8457'. The module 'C:\Program 
Files\WindowsPowerShell\Modules\PnP.PowerShell\3.2.0\PnP.PowerShell.psd1' requires a minimum Windows PowerShell 
version of '7.4.0' to run. Verify that you have the minimum required version of Windows PowerShell installed, and then 
try again.
At line:1 char:1
+ Import-Module PnP.PowerShell -ErrorAction Stop; Get-PnPConnection -Er ...
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ResourceUnavailable: (C:\Program File...PowerShell.psd1:String) [Import-Module], Invalid 
   OperationException
    + FullyQualifiedErrorId : Modules_InsufficientPowerShellVersion,Microsoft.PowerShell.Commands.ImportModuleCommand |
