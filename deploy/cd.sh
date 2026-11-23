#!/usr/bin/env bash
# Continuous deployment on the lab, run every 5 minutes by ragflow-cd.timer (deploy/install.sh), or by hand:
#   bash ~/ragflow-lab/deploy/cd.sh [--force]
# It deploys when either changes: this repo's main branch (public, fetched over https) or RAGFlow's latest
# release. Each deploy: update the checkout, lint the scripts, then ragflow.sh up --wait (which validates the settings
# and ports before starting anything, and waits until RAGFlow is healthy). A failed deploy is not retried until the
# commit or the release changes again (or --force). The log is ~/ragflow/lab/cd.log; the state ~/ragflow/lab/cd.state.
# nginx needs root, so a changed nginx config or API key is only reported: sudo sh ~/ragflow-lab/deploy/install.sh
set -uo pipefail

C=$HOME/ragflow-lab
L=$HOME/ragflow/lab
mkdir -p "$L"
LOG=$L/cd.log
STATE=$L/cd.state
FORCE=0
[ "${1:-}" = --force ] && FORCE=1
log() { echo "$(date -u '+%F %T') $*" | tee -a "$LOG"; }

exec 9>"$L/cd.lock"
flock -n 9 || { echo "another deploy is running"; exit 0; }

cd "$C" || { log "no checkout at $C: ./lab.sh setup"; exit 1; }
if ! git fetch -q origin main 2>>"$LOG"; then log "FAILED fetching main"; exit 1; fi
commit=$(git rev-parse --short origin/main)
release=$(bash "$C/ragflow.sh" latest 2>>"$LOG") || { log "FAILED reading RAGFlow's latest release"; exit 1; }
installed=$(git -C "$HOME/ragflow" describe --tags --exact-match 2>/dev/null || echo none)
key="$commit $release"
last=$(cat "$STATE" 2>/dev/null || true)  # "<commit> <release> ok|failed"

if [ "$FORCE" = 0 ] && [ "${last% *}" = "$key" ]; then
  [ "${last##* }" = failed ] && exit 0      # this exact combination already failed: wait for a change
  coder=$(docker inspect -f "{{.State.Running}}" coder-ollama 2>/dev/null || echo false)
  [ "$installed" = "$release" ] && [ "$coder" = true ] && exit 0   # deployed and still running: nothing new
fi

log "deploying $commit with RAGFlow $release (was: ${last:-never}, installed $installed)"
git reset -q --hard origin/main
ok=1
for f in "$C"/*.sh "$C"/deploy/*.sh "$C"/coder/*.sh; do bash -n "$f" 2>>"$LOG" || { log "syntax error in $f"; ok=0; }; done
if [ "$ok" = 1 ] && command -v shellcheck >/dev/null; then
  shellcheck -S error "$C"/*.sh "$C"/deploy/*.sh "$C"/coder/*.sh >>"$LOG" 2>&1 || { log "shellcheck errors"; ok=0; }
fi
if [ "$ok" = 1 ]; then
  RAGFLOW_VERSION=$release bash "$C/ragflow.sh" up --wait >>"$LOG" 2>&1 || { log "RAGFlow failed"; ok=0; }
  bash "$C/coder/coder.sh" up --wait >>"$LOG" 2>&1 || { log "the coding models failed"; ok=0; }
fi
if [ "$ok" = 1 ]; then
  echo "$key ok" >"$STATE"
  log "deployed $commit, RAGFlow $release and the coding models, healthy"
else
  echo "$key failed" >"$STATE"
  log "FAILED deploying $commit with RAGFlow $release (details above in this log)"
fi
redo="run once on the lab: sudo sh ~/ragflow-lab/deploy/install.sh"
for pair in "ragflow.stbfarm.org nginx" "coder.stbfarm.org coder/nginx"; do
  # shellcheck disable=SC2086  # two words: the site and its folder
  set -- $pair
  site=/etc/nginx/sites-available/$1
  if [ ! -f "$site" ]; then log "$1 is not published yet: $redo"
  elif ! cmp -s "$site" "$C/$2/$1.conf"; then log "the nginx config of $1 changed: $redo"; fi
done
if [ -f "$HOME/coder/api-keys" ] && [ "$HOME/coder/api-keys" -nt /etc/nginx/coder-keys.map ]; then
  log "the coder API keys changed: $redo"
fi
[ "$ok" = 1 ]
