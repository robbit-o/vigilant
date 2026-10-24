# Operating notes

Everything that requires a human step is collected here. Normal daily use is a
single command:

```shell
./scripts/dev.sh up --watch
```

`dev.sh` decrypts `secrets.enc.env` (SOPS + age) into the `docker compose`
process environment only, then runs compose. No plaintext secret is written to
disk. Run `./scripts/dev.sh down` the same way; never `down -v` (see
[Postgres data](#postgres-data)).

## First-time setup

1. **Install tooling** on the host (WSL2 Ubuntu):

   ```shell
   sudo apt install -y age
   # sops: install the .deb from https://github.com/getsops/sops/releases
   sops --version
   ```

2. **Initialize the SOPS store** (generates the age identity at
   `~/.config/sops/age/keys.txt`, writes `.sops.yaml`, and creates an empty
   encrypted `secrets.enc.env`):

   ```shell
   ./scripts/init-sops.sh
   ```

3. **Fill the bootstrap secrets**:

   ```shell
   sops secrets.enc.env
   ```

   Set `INFISICAL_DB_PASSWORD`, `INFISICAL_ENCRYPTION_KEY`,
   `INFISICAL_AUTH_SECRET`, `INFISICAL_PROJECT_ID`, and `INFISICAL_TOKEN`.
   The first three can be generated with `openssl rand -hex 16` (and a
   `openssl rand -base64 32` for `INFISICAL_AUTH_SECRET`); the project ID and
   token come from the Infisical setup in step 4.

4. **Bootstrap the Infisical instance** (one-time, manual, done in the UI):

   ```shell
   # Creates the DB volume if this is a fresh machine:
   docker volume create vigilant_infisical_db_data
   ./scripts/dev.sh up -d db redis infisical
   ```

   Open <http://localhost:8081> and create the admin account, an organization,
   a project, and the `dev` environment. Then create a **machine identity /
   service token** with read/write access to that project and environment.
   Copy the token and the project ID into `secrets.enc.env` (step 3) and
   re-run `sops secrets.enc.env`.

5. **Authenticate gcloud** so `secrets-sync` can read Secret Manager:

   ```shell
   gcloud auth application-default login \
       --impersonate-service-account="docker-compose-local@${GCLOUD_PROJECT}.iam.gserviceaccount.com" \
       --client-id-file client-id.json \
       --billing-project ${GCLOUD_PROJECT} \
       --scopes https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive
   ```

6. **Run the stack**, which triggers `secrets-sync` to copy the required GSM
   secrets into Infisical:

   ```shell
   ./scripts/dev.sh up --watch
   ```

## Postgres data

The Postgres data lives in the **external named volume**
`vigilant_infisical_db_data` (fixed name, survives project renames and
container removal).

- Create it on a fresh machine: `docker volume create vigilant_infisical_db_data`.
- Tear the stack down with `./scripts/dev.sh down` (never `down -v`, which
  deletes the volume along with the Infisical setup).
- Changing `INFISICAL_DB_PASSWORD` after the first init does **not** change the
  DB role password; follow the rotation steps below.

## Rotations

All four are independent. In particular, rotating the encryption key does **not**
invalidate the service token, and recreating the token does not force any other
rotation.

### `INFISICAL_AUTH_SECRET`

Signs sessions; swapping it logs everyone out. No data impact.

1. Generate a new value: `openssl rand -base64 32`.
2. Update `INFISICAL_AUTH_SECRET` in `secrets.enc.env` (`sops secrets.enc.env`).
3. Restart Infisical: `./scripts/dev.sh restart infisical`.
4. Log back into <http://localhost:8081>.

### Postgres/`INFISICAL_DB_PASSWORD`

Postgres only applies the password on first init of an empty data directory, so
the role must be altered first.

1. `docker exec -it infisical_db psql -U infisical -d infisical -c "ALTER USER infisical WITH PASSWORD '<new>';"`
2. Update `INFISICAL_DB_PASSWORD` in `secrets.enc.env`.
3. `./scripts/dev.sh up -d --force-recreate infisical secrets-sync robot`

### Infisical service token

1. In the project UI, create a new machine identity or service token.
2. Replace `INFISICAL_TOKEN` in `secrets.enc.env`.
3. `./scripts/dev.sh restart secrets-sync robot`

### `INFISICAL_ENCRYPTION_KEY` (root encryption key)

Infisical supports in-place rotation; no project recreation, no downtime,
service tokens remain valid.

1. Server Console → **Encryption** → **Root Encryption Keys** → **Generate New
   Key**. Copy the new key and its label (shown once; never recoverable) into
   `secrets.enc.env`.
2. Set `ENCRYPTION_KEY` to the new value and rolling-restart:
   `./scripts/dev.sh up -d --force-recreate infisical`.
3. Verify all instances restarted, then remove the old key in the Server
   Console (or let retention remove it after `KMS_ROOT_KEY_RETENTION_DAYS`,
   default 7).

Caveats: requires a recent version and server admin access; there is **no
rollback** after an instance applies it; DB backups taken before the rotation
still need the old key; only one old key is retained, so never fall two
rotations behind.

## Postgres backup & restore

The whole Infisical setup (org, project, machine identities, secrets) lives in
this database, so back it up if you care about it.

Backup (plain SQL dump, run while the stack is up):

```shell
docker exec infisical_db pg_dump -U infisical -d infisical --clean --if-exists \
    > infisical-backup.sql
```

Restore to a fresh volume:

```shell
./scripts/dev.sh down
# Wipe the old data dir (the volume itself is reused, so its name stays fixed)
docker run --rm -v vigilant_infisical_db_data:/var/lib/postgresql/data \
    alpine rm -rf /var/lib/postgresql/data/*
# Re-init the volume and replay the dump via the init scripts
docker run --rm -v vigilant_infisical_db_data:/var/lib/postgresql/data \
    -v "$(pwd)/infisical-backup.sql:/docker-entrypoint-initdb.d/00-restore.sql:ro" \
    -e POSTGRES_DB=infisical -e POSTGRES_USER=infisical \
    -e POSTGRES_PASSWORD="$INFISICAL_DB_PASSWORD" \
    postgres:16-alpine
./scripts/dev.sh up
```

Restores always need the encryption key that was active when the dump was taken.

## Troubleshooting

- `dev.sh` fails "Missing required env var INFISICAL_TOKEN": run
  `sops secrets.enc.env` and fill the token (step 4 of first-time setup).
- `robot` starts but reports no secrets loaded: confirm `secrets-sync` exited 0
  (`docker compose ps -a`) and that the token's machine identity has access to
  the project and environment configured in `secrets.enc.env`.
- Infisical won't start against an existing volume after a password change:
  you altered the env before the DB role (see rotation steps above).
