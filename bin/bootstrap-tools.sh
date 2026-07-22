#!/usr/bin/env bash

set -euo pipefail

required_rokit_version="rokit 1.2.0"

if ! command -v rokit >/dev/null 2>&1; then
    echo "Rokit 1.2.0 is required. Install it before running this bootstrap." >&2
    exit 1
fi

installed_rokit_version="$(rokit --version)"
if [[ "$installed_rokit_version" != "$required_rokit_version" ]]; then
    echo "Expected $required_rokit_version, found $installed_rokit_version." >&2
    exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
isolated_manifest_dir="$(mktemp -d)"

cleanup() {
    rm -rf -- "$isolated_manifest_dir"
}
trap cleanup EXIT

# Rokit 1.2 combines repository-local Rokit, Aftman, and Foreman manifests during
# installation. Install from an isolated copy so this repository's legacy Foreman
# sources do not prevent the public pins from being provisioned. Rokit may still
# discover manifests in the user's home directory.
cp "$repo_root/rokit.toml" "$isolated_manifest_dir/rokit.toml"

(
    cd "$isolated_manifest_dir"
    rokit install "$@"
)
