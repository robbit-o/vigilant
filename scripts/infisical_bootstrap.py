#!/usr/bin/env python3
"""Fetch secrets from the local Infisical instance and exec the app.

Runs as the robot container entrypoint. Reads the Infisical bootstrap values
from the environment, pulls every secret in the configured project/environment
over the REST API, exports them, and replaces itself with the given command so
signals reach the application process directly.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    """Read an environment variable, optionally enforcing it is present."""
    value = os.getenv(name, default)
    if required and not value:
        sys.exit(f"[ERROR] Missing required env var: {name}")
    return value or ""


def fetch_secrets(
    base_url: str, token: str, project_id: str, env_slug: str, secret_path: str
) -> List[Dict[str, Any]]:
    """List all secrets for a project environment via the v3 Raw Secrets API."""
    url = f"{base_url.rstrip('/')}/api/v3/secrets/raw"
    query = urllib.parse.urlencode(
        {
            "workspaceId": project_id,
            "environment": env_slug,
            "secretPath": secret_path,
        }
    )
    request = urllib.request.Request(
        f"{url}?{query}", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("secrets") or payload.get("data") or []


def main() -> None:
    """Load Infisical secrets into the environment and exec the app command."""
    base_url = get_env("INFISICAL_BASE_URL", default="http://infisical:8080")
    project_id = get_env("INFISICAL_PROJECT_ID", required=True)
    env_slug = get_env("INFISICAL_ENV", default="dev")
    token = get_env("INFISICAL_TOKEN", required=True)
    secret_path = get_env("INFISICAL_SECRET_PATH", default="/")

    command = sys.argv[1:]
    if not command:
        sys.exit("[ERROR] No command given to run after the secrets bootstrap")

    try:
        secrets = fetch_secrets(base_url, token, project_id, env_slug, secret_path)
    except urllib.error.HTTPError as error:
        sys.exit(
            f"[ERROR] Infisical returned {error.code} fetching secrets: {error.reason}"
        )
    except Exception as error:  # noqa: BLE001 - surface any bootstrap failure
        sys.exit(f"[ERROR] Failed to fetch secrets from Infisical: {error}")

    loaded = 0
    for item in secrets:
        key = item.get("secretKey") or item.get("key")
        if not key:
            continue
        value = item.get("secretValue")
        if value is None:
            value = item.get("value", "")
        os.environ[str(key)] = "" if value is None else str(value)
        loaded += 1

    if loaded == 0:
        print("[WARN] No secrets fetched from Infisical", file=sys.stderr)
    else:
        print(f"[OK] Loaded {loaded} secrets from Infisical")

    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
