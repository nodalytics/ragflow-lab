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

# Run from a copy: the checkout is updated below, and bash reads a script while it runs it. After an update that
# changes this file, the new version takes over (--force, so it deploys).
RUN=$L/cd.run.sh
if [ "${0##*/}" != cd.run.sh ]; then cp "$0" "$RUN" && exec bash "$RUN" "$@"; fi

exec 9>"$L/cd.lock"
flock -n 9 || { echo "another deploy is running"; exit 0; }

cd "$C" || { log "no checkout at $C: ./lab.sh setup"; exit 1; }
if ! git fetch -q origin main 2>>"$LOG"; then log "FAILED fetching main"; exit 1; fi
commit=$(git rev-parse --short origin/main)
# which services are on: deploy/services in the checkout (one name per line)
enabled() { grep -qx "$1" "$C/deploy/services" 2>/dev/null; }
release=off
installed=off
if enabled ragflow; then
  release=$(bash "$C/ragflow.sh" latest 2>>"$LOG") || { log "FAILED reading RAGFlow's latest release"; exit 1; }
  installed=$(git -C "$HOME/ragflow" describe --tags --exact-match 2>/dev/null || echo none)
fi
key="$commit $release"
last=$(cat "$STATE" 2>/dev/null || true)  # "<commit> <release> ok|failed"

if [ "$FORCE" = 0 ] && [ "${last% *}" = "$key" ]; then
  [ "${last##* }" = failed ] && exit 0      # this exact combination already failed: wait for a change
  coder=$(docker inspect -f "{{.State.Running}}" coder-ollama 2>/dev/null || echo false)
  enabled coder || coder=true
  [ "$installed" = "$release" ] && [ "$coder" = true ] && exit 0   # deployed and still running: nothing new
fi

log "deploying $commit: $(grep -v '^#' "$C/deploy/services" | xargs) (RAGFlow release $release; was: ${last:-never})"
git reset -q --hard origin/main
if ! cmp -s "$C/deploy/cd.sh" "$RUN"; then
  log "deploy/cd.sh changed: running the new version"
  exec 9>&-
  exec bash "$C/deploy/cd.sh" --force
fi
ok=1
for f in "$C"/*.sh "$C"/deploy/*.sh "$C"/coder/*.sh; do bash -n "$f" 2>>"$LOG" || { log "syntax error in $f"; ok=0; }; done
if [ "$ok" = 1 ] && command -v shellcheck >/dev/null; then
  shellcheck -S error "$C"/*.sh "$C"/deploy/*.sh "$C"/coder/*.sh >>"$LOG" 2>&1 || { log "shellcheck errors"; ok=0; }
fi
if [ "$ok" = 1 ]; then
  if enabled ragflow; then
    RAGFLOW_VERSION=$release bash "$C/ragflow.sh" up --wait >>"$LOG" 2>&1 || { log "RAGFlow failed"; ok=0; }
  fi
  if enabled coder; then
    bash "$C/coder/coder.sh" up --wait >>"$LOG" 2>&1 || { log "the coding models failed"; ok=0; }
  fi
fi
if [ "$ok" = 1 ]; then
  echo "$key ok" >"$STATE"
  log "deployed $commit: $(grep -v '^#' "$C/deploy/services" | xargs), healthy"
else
  echo "$key failed" >"$STATE"
  log "FAILED deploying $commit (details above in this log)"
fi
redo="run once on the lab: sudo sh ~/ragflow-lab/deploy/install.sh"
for pair in "ragflow ragflow.stbfarm.org nginx" "coder coder.stbfarm.org coder/nginx"; do
  # shellcheck disable=SC2086  # three words: the service, its site and the site's folder
  set -- $pair
  svc=$1
  shift
  site=/etc/nginx/sites-available/$1
  if ! enabled "$svc"; then
    [ -e "/etc/nginx/sites-enabled/$1" ] && log "$svc is disabled but $1 is still published: $redo"
    continue
  fi
  if [ ! -f "$site" ]; then log "$1 is not published yet: $redo"
  elif ! cmp -s "$site" "$C/$2/$1.conf"; then log "the nginx config of $1 changed: $redo"; fi
done
if [ -f "$HOME/coder/api-keys" ] && [ "$HOME/coder/api-keys" -nt /etc/nginx/coder-keys.map ]; then
  log "the coder API keys changed: $redo"
fi
[ "$ok" = 1 ]
