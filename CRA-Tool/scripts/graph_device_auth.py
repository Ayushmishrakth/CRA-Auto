from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import jwt
import msal
from dotenv import load_dotenv


GRAPH_SCOPES = [
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Directory.Read.All",
    "https://graph.microsoft.com/Policy.Read.All",
    "https://graph.microsoft.com/Application.Read.All",
    "https://graph.microsoft.com/RoleManagement.Read.Directory",
    "https://graph.microsoft.com/AuditLog.Read.All",
    "https://graph.microsoft.com/UserAuthenticationMethod.Read.All",
    "https://graph.microsoft.com/Reports.Read.All",
    "https://graph.microsoft.com/Group.Read.All",
    "https://graph.microsoft.com/Team.ReadBasic.All",
    "https://graph.microsoft.com/Sites.Read.All",
    "https://graph.microsoft.com/Files.Read.All",
]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> int:
    load_dotenv()
    tenant_id = os.getenv("CRA_VALIDATION_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "common"
    if tenant_id in {"", "common", "organizations"}:
        tenant_id = "common"
    client_id = os.getenv("AZURE_CLIENT_ID")
    if not client_id:
        raise RuntimeError("AZURE_CLIENT_ID is required in .env for device-code validation")

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.PublicClientApplication(client_id=client_id, authority=authority)
    flow = app.initiate_device_flow(scopes=GRAPH_SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Microsoft device-code flow failed to start: {flow}")

    _write_json(
        Path("storage/validation/m365-device-flow.json"),
        {
            "message": flow.get("message"),
            "user_code": flow.get("user_code"),
            "verification_uri": flow.get("verification_uri"),
            "verification_uri_complete": flow.get("verification_uri_complete"),
            "expires_in": flow.get("expires_in"),
            "interval": flow.get("interval"),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(flow["message"], flush=True)
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(f"Microsoft device-code auth failed: {result}")

    access_token = result["access_token"]
    claims = jwt.decode(access_token, options={"verify_signature": False, "verify_aud": False})
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=60, headers=headers) as client:
        me = client.get("https://graph.microsoft.com/v1.0/me?$select=id,userPrincipalName,displayName")
        me.raise_for_status()
        org = client.get("https://graph.microsoft.com/v1.0/organization?$select=id,displayName,verifiedDomains")
        org.raise_for_status()

    org_value = (org.json().get("value") or [{}])[0]
    proof = {
        "status": "success",
        "tenant_id": claims.get("tid"),
        "account": me.json().get("userPrincipalName"),
        "auth_type": "msal_device_code",
        "scopes": sorted(str(claims.get("scp") or "").split()),
        "get_mg_user_equivalent_returned": True,
        "get_mg_organization_equivalent_returned": True,
        "sample_user_id": me.json().get("id"),
        "sample_user_principal_name": me.json().get("userPrincipalName"),
        "organization_id": org_value.get("id"),
        "organization_display_name": org_value.get("displayName"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(Path("storage/validation/m365-graph-proof.json"), proof)

    token_script = (
        "# Sensitive validation token. Do not commit.\n"
        f"$env:CRA_GRAPH_ACCESS_TOKEN = {json.dumps(access_token)}\n"
        "$env:CRA_GRAPH_AUTH_MODE = 'context'\n"
    )
    Path("storage/validation").mkdir(parents=True, exist_ok=True)
    Path("storage/validation/graph-session.ps1").write_text(token_script, encoding="utf-8")
    print(json.dumps(proof, indent=2), flush=True)
    print("Wrote storage/validation/graph-session.ps1 for this validation session.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
