from __future__ import annotations


class GraphAuthError(RuntimeError):
    pass


class GraphAuthService:
    async def get_delegated_token(self, *, tenant_id: str, user_id: str | None = None) -> str:
        raise GraphAuthError(
            "Microsoft Graph delegated auth is not configured for this tenant. "
            "Failing closed instead of collecting untrusted Graph data."
        )
