#!/usr/bin/env bash
# Copies the integration to a Home Assistant OS host and restarts Home Assistant.
# Writes the deployed commit to guest_access/BUILD, which the page shows next to
# the version; "-dirty" marks files that differ from that commit.
#
#   scripts/deploy.sh <ssh-host> [ssh options...]
set -euo pipefail
cd "$(dirname "$0")/.."

host=${1:?usage: scripts/deploy.sh <ssh-host> [ssh options...]}
shift
target=/mnt/data/supervisor/homeassistant/custom_components

commit=$(git rev-parse --short=12 HEAD)
if ! git diff --quiet HEAD -- custom_components || [ -n "$(git ls-files --others --exclude-standard custom_components)" ]; then
  commit="$commit-dirty"
fi

staging=$(mktemp -d)
trap 'rm -rf "$staging"' EXIT
# COPYFILE_DISABLE keeps macOS from adding ._* files
COPYFILE_DISABLE=1 tar -C custom_components --exclude __pycache__ --exclude BUILD -cf - guest_access | tar -C "$staging" -xf -
printf '%s\n' "$commit" > "$staging/guest_access/BUILD"

echo "Deploying $commit to $host"
# Unpacked beside the old folder and then swapped, so files removed or renamed
# since the last deployment do not stay behind
COPYFILE_DISABLE=1 tar -C "$staging" -cf - guest_access |
  ssh "$@" "$host" "set -e; rm -rf $target/.guest_access.new; mkdir $target/.guest_access.new
    tar -C $target/.guest_access.new -xf -
    find $target/.guest_access.new -name '._*' -delete
    rm -rf $target/guest_access
    mv $target/.guest_access.new/guest_access $target/guest_access
    rmdir $target/.guest_access.new
    docker exec hassio_cli ha core restart"
