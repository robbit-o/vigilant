import os
import sys
from typing import Dict, List, Optional, Tuple

import requests
from google.api_core.exceptions import GoogleAPICallError, NotFound, PermissionDenied
from google.cloud import secretmanager


def get_env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    """Fetch an environment variable, exiting with an error if required and missing.

    Args:
        name: Name of the environment variable.
        required: Whether the environment variable must be present and non-empty.
        default: Fallback value if the variable is not set.

    Returns:
        The string value of the environment variable.
    """
    val = os.getenv(name, default)
    if required and (val is None or val == ""):
        print(f"[ERROR] Missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return val or ""


def gsm_get_latest_value(project_id: str, secret_name: str) -> Tuple[str, str]:
    """Retrieve the latest version value and full resource name from Google Secret Manager.

    Args:
        project_id: GCP project ID containing the secret.
        secret_name: Name of the secret key in GSM.

    Returns:
        Tuple of (secret_payload_value, full_version_resource_name).
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    try:
        resp = client.access_secret_version(request={"name": name})
    except NotFound:
        raise
    except PermissionDenied as e:
        print(
            f"[WARN] GSM permission denied accessing {secret_name}: {e}",
            file=sys.stderr,
        )
        raise
    except GoogleAPICallError as e:
        print(f"[WARN] GSM API error accessing {secret_name}: {e}", file=sys.stderr)
        raise
    return resp.payload.data.decode("utf-8"), resp.name


def infisical_list_secrets(
    base_url: str, token: str, project_id: str, env_slug: str, secret_path: str = "/"
) -> Dict[str, Dict]:
    """Retrieve all secrets in a given Infisical workspace, environment, and path.

    Uses the Infisical v3 Raw Secrets API (`GET /api/v3/secrets/raw`).

    Args:
        base_url: Base HTTP URL for the Infisical instance.
        token: Service token or authentication bearer token.
        project_id: Infisical Workspace ID (Project ID).
        env_slug: Target environment slug (e.g., 'dev', 'prod').
        secret_path: Folder path within Infisical secrets (defaults to '/').

    Returns:
        A dictionary mapping secret keys to dicts containing 'value' and 'raw' payload details.
    """
    url = f"{base_url.rstrip('/')}/api/v3/secrets/raw"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "workspaceId": project_id,
        "environment": env_slug,
        "secretPath": secret_path,
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code == 404:
        return {}
    if r.status_code >= 400:
        print(
            f"[ERROR] Infisical list failed {r.status_code}: {r.text[:200]}",
            file=sys.stderr,
        )
        r.raise_for_status()
    data = r.json()
    result = {}
    items = data.get("secrets") or data.get("data") or []
    for it in items:
        key = it.get("secretKey") or it.get("key") or it.get("name")
        if not key:
            continue
        val = it.get("secretValue") or it.get("value") or ""
        result[key] = {"value": val, "raw": it}
    return result


def infisical_get_secret(
    base_url: str,
    token: str,
    project_id: str,
    env_slug: str,
    key: str,
    secret_path: str = "/",
) -> Optional[str]:
    """Fetch a single secret by name from Infisical using the v3 Raw Secrets API.

    Args:
        base_url: Base HTTP URL for the Infisical instance.
        token: Authentication token.
        project_id: Infisical Workspace ID.
        env_slug: Target environment slug.
        key: The key identifier of the secret.
        secret_path: Folder path within Infisical secrets.

    Returns:
        The secret value string if found, or None if it does not exist (404).
    """
    try:
        url = f"{base_url.rstrip('/')}/api/v3/secrets/raw/{key}"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "workspaceId": project_id,
            "environment": env_slug,
            "secretPath": secret_path,
        }
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            print(
                f"[ERROR] Infisical get {key} failed {r.status_code}: {r.text[:120]}",
                file=sys.stderr,
            )
            r.raise_for_status()
        j = r.json()
        return (j.get("secret") or {}).get("secretValue") or j.get("secretValue") or ""
    except Exception as e:
        print(f"[WARN] Infisical get {key} error: {e}", file=sys.stderr)
        raise


def infisical_create_secret(
    base_url: str,
    token: str,
    project_id: str,
    env_slug: str,
    key: str,
    value: str,
    secret_path: str = "/",
    type_: str = "shared",
) -> None:
    """Create a new secret in Infisical via POST request on the v3 Raw Secrets API.

    Args:
        base_url: Base HTTP URL for the Infisical instance.
        token: Authentication token.
        project_id: Infisical Workspace ID.
        env_slug: Target environment slug.
        key: The secret key name.
        value: The secret value to store.
        secret_path: Folder path within Infisical secrets.
        type_: Secret type ('shared' or 'personal').
    """
    url = f"{base_url.rstrip('/')}/api/v3/secrets/raw/{key}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "workspaceId": project_id,
        "environment": env_slug,
        "secretPath": secret_path,
        "secretValue": value,
        "type": type_,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code not in (200, 201):
        print(
            f"[ERROR] Infisical create {key} failed {r.status_code}: {r.text[:120]}",
            file=sys.stderr,
        )
        r.raise_for_status()


def infisical_update_secret(
    base_url: str,
    token: str,
    project_id: str,
    env_slug: str,
    key: str,
    value: str,
    secret_path: str = "/",
    type_: str = "shared",
) -> None:
    """Update an existing secret in Infisical via PATCH request on the v3 Raw Secrets API.

    Args:
        base_url: Base HTTP URL for the Infisical instance.
        token: Authentication token.
        project_id: Infisical Workspace ID.
        env_slug: Target environment slug.
        key: The secret key name.
        value: The new secret value to store.
        secret_path: Folder path within Infisical secrets.
        type_: Secret type ('shared' or 'personal').
    """
    url = f"{base_url.rstrip('/')}/api/v3/secrets/raw/{key}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "workspaceId": project_id,
        "environment": env_slug,
        "secretPath": secret_path,
        "secretValue": value,
        "type": type_,
    }
    r = requests.patch(url, headers=headers, json=payload, timeout=30)
    if r.status_code not in (200, 201):
        print(
            f"[ERROR] Infisical update {key} failed {r.status_code}: {r.text[:120]}",
            file=sys.stderr,
        )
        r.raise_for_status()


def main() -> None:
    """Sync the required secrets from Google Secret Manager into Infisical.

    Reads configuration from environment variables, fetches each required value
    from GSM, and creates or updates it in Infisical so the robot can resolve it
    from the local Infisical instance at startup.
    """
    try:
        gsm_project = get_env("GSM_PROJECT_ID")
        base_url = get_env("INFISICAL_BASE_URL", default="http://infisical:8080")
        inf_project = get_env("INFISICAL_PROJECT_ID")
        inf_env = get_env("INFISICAL_ENV", default="dev")
        token = get_env("INFISICAL_TOKEN")
        req_str = get_env("REQUIRED_SECRETS", required=False, default="")

        required: List[str] = (
            [x.strip() for x in req_str.split(",") if x.strip()] if req_str else []
        )

        try:
            inf_cache = infisical_list_secrets(base_url, token, inf_project, inf_env)
        except Exception as e:
            print(f"[ERROR] Failed to list Infisical secrets: {e}", file=sys.stderr)
            sys.exit(2)

        any_critical = False
        for key in required:
            try:
                gsm_val, _ = gsm_get_latest_value(gsm_project, key)
            except NotFound:
                print(
                    f"[WARN] GSM secret not found for required key: {key} (skipping)",
                    file=sys.stderr,
                )
                continue
            except (PermissionDenied, GoogleAPICallError) as e:
                print(f"[ERROR] GSM access error for {key}: {e}", file=sys.stderr)
                any_critical = True
                continue
            except Exception as e:
                print(f"[ERROR] GSM unexpected error for {key}: {e}", file=sys.stderr)
                any_critical = True
                continue

            inf_val = inf_cache.get(key, {}).get("value")
            if inf_val is None:
                try:
                    inf_val = infisical_get_secret(
                        base_url, token, inf_project, inf_env, key
                    )
                except Exception:
                    inf_val = None

            if inf_val is None:
                try:
                    infisical_create_secret(
                        base_url, token, inf_project, inf_env, key, gsm_val
                    )
                    print(f"[OK] created {key} in Infisical")
                except Exception as e:
                    print(
                        f"[ERROR] Failed to create {key} in Infisical: {e}",
                        file=sys.stderr,
                    )
                    any_critical = True
            elif inf_val != gsm_val:
                try:
                    infisical_update_secret(
                        base_url, token, inf_project, inf_env, key, gsm_val
                    )
                    print(f"[OK] updated {key} in Infisical")
                except Exception as e:
                    print(
                        f"[ERROR] Failed to update {key} in Infisical: {e}",
                        file=sys.stderr,
                    )
                    any_critical = True
            else:
                print(f"[OK] skipped {key} (in sync)")

        if any_critical:
            print("[ERROR] Critical errors occurred during sync", file=sys.stderr)
            sys.exit(2)

        print("[OK] secrets-sync completed successfully")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected exception: {e}", file=sys.stderr)
        sys.exit(99)


if __name__ == "__main__":
    main()
