#!/bin/bash

set -euxo pipefail

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

"$python_command" bin/validate-wally-packages.py "$@"
