# Authentication Requirements Report

## Why the browser opens every time
The CRA Tool uses an asynchronous **PowerShell Subprocess Executor** (`PowerShellExecutor`) to run each assessment parameter.
To ensure strict variable isolation, memory cleanup, and process safety, **every parameter is executed in a brand-new, isolated PowerShell session (`powershell.exe` / `pwsh.exe`)**.
Because each subprocess is entirely clean, **Exchange Online PowerShell and PnP modules do not share or cache authentication contexts** across parameters.
As a result, they trigger a new local web server and open a browser window to request interactive login credentials for every single PowerShell-based parameter.

## How to fix it (Non-Interactive Authentication)
To run all 65 parameters fully automatically without opening any browser or prompting for logins, you must configure **Certificate-Based Authentication (App-Only Auth)** for Exchange Online and SharePoint Online modules:

1. **Generate a Self-Signed Certificate**:
   ```powershell
   $cert = New-SelfSignedCertificate -Subject 'CN=CRAAutomatedAuth' -CertStoreLocation 'Cert:\CurrentUser\My' -KeyExportPolicy Exportable -KeySpec Signature
   Export-Certificate -Cert $cert -FilePath 'CRAAutomatedAuth.cer'
   ```
2. **Upload the Certificate to the App Registration** in Microsoft Entra admin center.
3. **Configure Certificate-based connection** in your master scripts:
   ```powershell
   Connect-ExchangeOnline -AppID <ApplicationID> -CertificateThumbprint <Thumbprint> -Organization <TenantDomain>
   ```