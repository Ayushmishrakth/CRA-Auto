from app.services.domain_runtimes.base import DomainRuntime


class PurviewRuntime(DomainRuntime):
    service = "purview"
    master_script = "app/powershell/purview/purview_master.ps1"
