#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_command=""

for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c \
        'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
    then
        python_command="$candidate"
        break
    fi
done

if [[ -z "$python_command" ]]; then
    echo "Python 3.11 or newer is required to build the documentation." >&2
    exit 1
fi

docs_venv="${REACT_LUAU_DOCS_VENV:-$repo_root/.venv/docs}"
venv_python="$docs_venv/bin/python"

if [[ "${OS:-}" == "Windows_NT" ]]; then
    venv_python="$docs_venv/Scripts/python.exe"
fi

if [[ ! -x "$venv_python" ]]; then
    "$python_command" -m venv "$docs_venv"
fi

"$venv_python" -m pip install --disable-pip-version-check -r "$repo_root/docs/requirements.txt"

(
    cd "$repo_root"
    "$venv_python" -m mkdocs build --strict
)
