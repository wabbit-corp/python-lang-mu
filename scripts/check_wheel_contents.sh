#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ "$#" -gt 1 ]; then
  echo "Usage: $0 [path/to/wheel.whl]"
  exit 1
fi

if [ "$#" -eq 1 ]; then
  wheel_file="$1"
else
  if ! compgen -G "dist/*.whl" > /dev/null; then
    echo "No wheel found in dist/. Build one first with: python -m build --sdist --wheel"
    exit 1
  fi
  wheel_file="$(ls -1t dist/*.whl | head -n1)"
fi

if [ ! -f "$wheel_file" ]; then
  echo "Wheel file not found: $wheel_file"
  exit 1
fi

echo "Inspecting wheel: $wheel_file"

tmp_matches_file="$(mktemp)"
trap 'rm -f "$tmp_matches_file"' EXIT

if unzip -l "$wheel_file" | awk '{print $4}' | grep -E '^mu/test_.*\.py$|^mu/tests\.py$' > "$tmp_matches_file"; then
  echo "Unexpected test files found in wheel:"
  cat "$tmp_matches_file"
  exit 1
fi

echo "Wheel content check passed: no package-internal test modules were included."
