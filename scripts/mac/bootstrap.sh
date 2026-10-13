#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
python3 -m venv "$repo_root/.venv"
"$repo_root/.venv/bin/python" -m pip install --editable "$repo_root"
echo "Run: source '$repo_root/.venv/bin/activate'"
