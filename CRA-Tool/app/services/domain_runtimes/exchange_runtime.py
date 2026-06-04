from app.services.domain_runtimes.base import DomainRuntime


class ExchangeRuntime(DomainRuntime):
    service = "exchange"
    master_script = "app/powershell/exchange/exchange_master.ps1"
