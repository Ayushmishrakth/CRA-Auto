from app.services.domain_runtimes.base import DomainRuntime


class TeamsRuntime(DomainRuntime):
    service = "teams"
    master_script = "app/powershell/teams/teams_master.ps1"
