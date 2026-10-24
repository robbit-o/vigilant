# Session Handoff — Local Dev Secret Management (Infisical + SOPS)

> Status: work complete and verified; **uncommitted** (all changes staged).
> Written to let a new session resume without re-deriving decisions.

## Objective

Rework the local development secret handling for the `vigilant` stack:

- `robot` fetches its secrets from the self-hosted Infisical instance **at startup** through a bootstrap entrypoint (no more `robot.env` export file / `robot_env_data` volume).
- Merge `docker-compose.override.yml` into a single `docker-compose.yml`.
- Persist the Infisical Postgres data in a fixed, named external volume.
- Store the `INFISICAL_*` bootstrap secrets (DB password, encryption key, auth secret, project id, token) **encrypted at rest** with SOPS + age instead of in a plaintext `.env`.

## Decisions (and why)

| Decision | Choice |
| --- | --- |
| Secret backend | Keep self-hosted **Infisical** (already in the stack). |
| Bootstrap script in image | **Always `COPY`** into the final image (no build-arg gating). It is inert in prod because the prod entrypoint/CMD is unchanged. |
| Compose layout | **Merge** override into one `docker-compose.yml`; `docker-compose.override.yml` **deleted**. |
| Encryption tool | **SOPS + age**, host-side decrypt. Private age key never leaves the developer machine. |
| How compose gets secrets | Wrapper `scripts/dev.sh` runs `sops exec-env secrets.enc.env "docker compose $*"`. |
| Token transport | Passed as **`INFISICAL_TOKEN` env var** to `robot` and `secrets-sync` (not a mounted file). |
| Networks | Removed the custom `internal` network; use the default network. |
| `.env` role | Keep `.env` for **non-secret app settings** only (`STORAGE_LOCATION`, `BROWSER_*`, `GCLOUD_PROJECT`, `INFISICAL_ENV`, `INFISICAL_REDIS_URL`). `.env` is gitignored and **not** in `.dockerignore`. |
| Docker build context | Exclude `secrets/`, `client-id.json`, `.git`, `terraform`, `screenshots`, `.venv`, caches, etc. via `.dockerignore`. |

## How it works

1. `./scripts/init-sops.sh` (idempotent) creates the age identity (if missing), writes `.sops.yaml`, and creates/seeds `secrets.enc.env`.
2. `./scripts/dev.sh <compose args>` checks for `sops` + `secrets.enc.env`, then decrypts into the process environment and runs Docker Compose.
3. Compose interpolates `${INFISICAL_*}` from that environment.
4. `secrets-sync` (one-shot, `restart: "no"`) copies the app secrets from Google Secret Manager into Infisical; `robot` waits for it via `depends_on: service_completed_successfully`.
5. `robot` starts with `entrypoint: python3 /usr/local/bin/infisical_bootstrap.py`; the script fetches `/api/v3/secrets/raw`, exports them into `os.environ`, and `os.execvp`s the original `uvicorn` command.

## Files

Created:
- `scripts/init-sops.sh` — SOPS/age bootstrap.
- `scripts/dev.sh` — decrypt + compose wrapper.
- `scripts/infisical_bootstrap.py` — robot entrypoint (stdlib only).
- `.sops.yaml` — creation rule for `secrets.enc.env` (age recipient).
- `secrets.enc.env` — **encrypted**, safe to commit.
- `docs/OPERATIONS.md` — first-time setup, secret rotation, Postgres backup/restore, troubleshooting.
- `secrets-sync/Dockerfile`, `secrets-sync/requirements.txt` (pre-existing WIP, staged).

Modified:
- `docker-compose.yml` — merged single-file stack; bootstrap entrypoint; external volume.
  - `volumes.infisical_db_data.name: vigilant_infisical_db_data`, `external: true` (must already exist in Docker).
- `Dockerfile` — added `COPY scripts/infisical_bootstrap.py /usr/local/bin/infisical_bootstrap.py` before `CMD`.
- `secrets-sync/sync_gsm_to_infisical.py` — token via env; removed `robot.env` export logic.
- `.env` (gitignored) / `.env.template` — app settings only + empty `INFISICAL_*` placeholders.
- `.dockerignore` — added build-context exclusions.
- `README.md` — start-service instructions.
- `.gitignore` — minor WIP changes (staged).

Deleted:
- `docker-compose.override.yml`
- `secrets/` (plaintext token) — the token now lives in `secrets.enc.env`, encrypted.

## Environment / prerequisites

- `sops 3.13.3`, `age` / `age-keygen` installed under `/usr/bin`.
- Age identity: `~/.config/sops/age/keys.txt` (public recipient in `.sops.yaml`).
- Docker volume `vigilant_infisical_db_data` already exists on this machine.
- Host `~/.config/gcloud/application_default_credentials.json` is bind-mounted for `secrets-sync` / `robot`.

## Verification already done

- `./scripts/dev.sh config` — passes; services, entrypoint, `command`, env interpolation, and external volume all render correctly.
- `ruff check --no-cache scripts/infisical_bootstrap.py secrets-sync/sync_gsm_to_infisical.py` — passes.
- `ruff format` applied to both new/modified Python files.
- `python3 -m py_compile` on both scripts — OK.
- No lingering references to the `internal` network, `robot_env_data`, `infisical_keys`, or `override.yml`.
- `git check-ignore`: `client-id.json` and `secrets/` ignored; `secrets.enc.env`, `.sops.yaml`, `scripts/`, `docs/` are **not** ignored.
- `sops exec-env secrets.enc.env env` decrypts and exposes the expected variables.

## Important gotcha (already fixed)

`sops exec-env` **only accepts exactly two positional arguments**: the file and a **single-word command**. Passing a multi-word command (`sops exec-env secrets.enc.env docker compose config`) fails with the misleading `error: missing file to decrypt`.

Fix in `scripts/dev.sh`:

```bash
exec sops exec-env secrets.enc.env "docker compose $*"
```

The command is joined into one quoted word; sops runs it through a shell. Keep this pattern when editing the wrapper.

## Before using / committing

- **Rotate** the Infisical values that were exposed in plaintext during setup: `INFISICAL_ENCRYPTION_KEY`, `INFISICAL_AUTH_SECRET`, `INFISICAL_DB_PASSWORD`, and `INFISICAL_TOKEN` (project id `7a863e6b-…`). The root encryption key can be rotated in the Infisical Server Console **without** recreating the project (see `docs/OPERATIONS.md`).
- **Do not** paste secret values into this file or a commit. `secrets.enc.env` is encrypted.

## Resume here (new session)

```bash
cd /home/gus/projects/vigilant

# inspect state
git status
sops --version
ls -la scripts docs
sops exec-env secrets.enc.env env | grep INFISICAL   # decrypt smoke test

# validate compose again
./scripts/dev.sh config

# full smoke test (pulls images, starts containers)
./scripts/dev.sh up --watch
```

Then optionally commit (only if the user asks). Suggested message: `chore(dev): move local secrets to Infisical bootstrap + SOPS`.

## Remaining / optional

1. Run `./scripts/dev.sh up --watch` to smoke-test end to end (secrets-sync populates Infisical; robot boots via the bootstrap).
2. Rotate the leaked Infisical secrets.
3. Commit the staged changes.
