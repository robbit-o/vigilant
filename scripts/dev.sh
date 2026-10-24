#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v sops >/dev/null 2>&1; then
    echo "error: 'sops' is required (install from getsops/sops releases)" >&2
    exit 1
fi
if [ ! -f secrets.enc.env ]; then
    echo "error: secrets.enc.env not found. Run ./scripts/init-sops.sh first." >&2
    exit 1
fi

# sops exec-env takes exactly two positional args: the file and the command.
# Join the compose invocation into a single word; sops runs it through a shell.
exec sops exec-env secrets.enc.env "docker compose $*"
