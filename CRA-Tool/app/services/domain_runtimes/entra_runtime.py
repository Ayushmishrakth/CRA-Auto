from app.services.domain_runtimes.base import DomainRuntime


class EntraRuntime(DomainRuntime):
    service = "entra"
    master_script = "app/powershell/entra/entra_master.ps1"
