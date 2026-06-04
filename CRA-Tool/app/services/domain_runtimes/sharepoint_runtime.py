from app.services.domain_runtimes.base import DomainRuntime


class SharePointRuntime(DomainRuntime):
    service = "sharepoint"
    master_script = "app/powershell/sharepoint/sharepoint_master.ps1"
