#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"
python3 scripts/mac/check_environment.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q cli agent benchmark
