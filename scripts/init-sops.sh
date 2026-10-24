#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

AGE_DIR="${AGE_DIR:-$HOME/.config/sops/age}"
AGE_KEY="$AGE_DIR/keys.txt"

if ! command -v sops >/dev/null 2>&1; then
    echo "error: 'sops' is required (install from getsops/sops releases)" >&2
    exit 1
fi
if ! command -v age-keygen >/dev/null 2>&1; then
    echo "error: 'age' is required (install with: sudo apt install age)" >&2
    exit 1
fi

if [ ! -f "$AGE_KEY" ]; then
    mkdir -p "$AGE_DIR"
    age-keygen -o "$AGE_KEY"
    chmod 600 "$AGE_KEY"
    echo "Generated age identity at $AGE_KEY"
fi

PUBKEY="$(grep -oP '^# public key: \K.*' "$AGE_KEY")"
if [ -z "$PUBKEY" ]; then
    echo "error: could not read public key from $AGE_KEY" >&2
    exit 1
fi

if [ ! -f .sops.yaml ]; then
    cat > .sops.yaml <<EOF
# Encrypted with the age identity at ~/.config/sops/age/keys.txt.
# The private key never leaves the host; without it secrets.enc.env is unreadable.
creation_rules:
  - path_regex: secrets\.enc\.env$
    age: $PUBKEY
EOF
    echo "Wrote .sops.yaml with recipient $PUBKEY"
fi

if [ ! -f secrets.enc.env ]; then
    cat > secrets.enc.env <<'EOF'
INFISICAL_DB_PASSWORD=
INFISICAL_ENCRYPTION_KEY=
INFISICAL_AUTH_SECRET=
INFISICAL_PROJECT_ID=
INFISICAL_TOKEN=
EOF
    sops encrypt --in-place secrets.enc.env
    echo "Created encrypted secrets.enc.env"
fi

echo "Edit values with:  sops secrets.enc.env"
echo "Run stack with:    ./scripts/dev.sh up --watch"
