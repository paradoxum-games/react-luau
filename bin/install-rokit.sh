#!/bin/bash

set -euo pipefail

readonly rokit_version="1.2.0"
readonly archive_sha256="951a7f3ec3d2a5e021fd1867d32f69f010ee4c2927f644b759578afc59c65fc0"
readonly archive_url="https://github.com/rojo-rbx/rokit/releases/download/v${rokit_version}/rokit-${rokit_version}-linux-x86_64.zip"

if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
  echo "bin/install-rokit.sh supports only Linux x86_64 CI runners" >&2
  exit 1
fi

for command_name in curl sha256sum unzip; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "$command_name is required to install Rokit" >&2
    exit 1
  fi
done

temporary_directory="$(mktemp -d)"
trap 'rm -rf -- "$temporary_directory"' EXIT
archive_path="$temporary_directory/rokit.zip"

curl \
  --proto '=https' \
  --tlsv1.2 \
  --retry 3 \
  --silent \
  --show-error \
  --fail \
  --location \
  --output "$archive_path" \
  "$archive_url"
printf '%s  %s\n' "$archive_sha256" "$archive_path" | sha256sum --check --status
unzip -q "$archive_path" -d "$temporary_directory"
chmod +x "$temporary_directory/rokit"
"$temporary_directory/rokit" self-install

echo "Installed checksum-verified Rokit ${rokit_version}"
