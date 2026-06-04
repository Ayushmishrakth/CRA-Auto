from app.services.domain_runtimes.base import DomainRuntime


class OneDriveRuntime(DomainRuntime):
    service = "onedrive"
    master_script = "app/powershell/onedrive/onedrive_master.ps1"
