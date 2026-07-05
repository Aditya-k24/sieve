#!/usr/bin/env bash
# Clone-and-run installer. No browser, no manual config — everything happens here.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3.11+ first." >&2
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo "Python 3.11+ required, found $PY_VERSION." >&2
    exit 1
fi

echo "Creating virtualenv (.venv)..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing Sieve..."
pip install --quiet --upgrade pip
# Regular (non-editable) install: some Python builds skip .pth processing for
# editable installs, which breaks `import sieve` intermittently. A normal
# install copies the package into site-packages, sidestepping that entirely.
pip install --quiet .

mkdir -p "$HOME/.sieve/bin"
python3 -c "from sieve.ledger import ensure_db; ensure_db()"

echo
echo "Running sieve doctor..."
sieve doctor || true

cat <<'EOF'

Next steps:
  source .venv/bin/activate   # each new shell, until sieve's venv is on your PATH
  sieve on
  claude "what test framework does this repo use?"
  sieve ledger
  sieve off
EOF
