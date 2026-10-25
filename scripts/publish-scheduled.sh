#!/usr/bin/env bash
# deploy from a FRESH CLONE of origin/main, never from the working tree, so an unattended run can't publish
# half-finished local edits. posts scheduled for a future date go live on the first run on/after that date.
# usage: scripts/publish-scheduled.sh        (needs CLOUDFLARE_* in the environment; the daily systemd timer uses fish's universals)
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
git clone --quiet --depth 1 "${REPO_URL:-https://github.com/TogiFerretFerret/Profile-Website.git}" "$tmp/site"
cd "$tmp/site"
git log -1 --format='publishing %h %s' 
make all
