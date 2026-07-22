#!/bin/bash

set -euo pipefail

python_command=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 \
    && "$candidate" -c \
      'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    python_command="$candidate"
    break
  fi
done

if [[ -z "$python_command" ]]; then
  echo "Python 3.11 or newer is required" >&2
  exit 1
fi

temporary_directory="$(mktemp -d)"
trap 'rm -rf -- "$temporary_directory"' EXIT

cp tests/wally-workspace/wally.lock "$temporary_directory/wally.lock.before"
wally install --project-path tests/wally-workspace
cmp tests/wally-workspace/wally.lock "$temporary_directory/wally.lock.before"

"$python_command" bin/generate-wally-workspace.py --check
rojo sourcemap tests.wally.project.json \
  --output "$temporary_directory/tests.wally.sourcemap.json"
rojo build tests.wally.project.json \
  --output "$temporary_directory/tests.wally.rbxm"
test -s "$temporary_directory/tests.wally.rbxm"

echo "Wally source workspace validation passed (layout only; Jest was not executed)"
