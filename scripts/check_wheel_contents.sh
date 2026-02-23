#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! compgen -G "dist/*.whl" > /dev/null; then
  echo "No wheel found in dist/. Build one first with: python -m build --sdist --wheel"
  exit 1
fi

wheel_file="$(ls dist/*.whl | head -n1)"
echo "Inspecting wheel: $wheel_file"

if unzip -l "$wheel_file" | awk '{print $4}' | grep -E '^mu/test_.*\.py$|^mu/tests\.py$' > /tmp/mu_wheel_test_files.txt; then
  echo "Unexpected test files found in wheel:"
  cat /tmp/mu_wheel_test_files.txt
  exit 1
fi

echo "Wheel content check passed: no package-internal test modules were included."
