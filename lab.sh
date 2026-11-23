#!/usr/bin/env bash
# RAGFlow on the lab, from your machine. Reads LAB and LAB_KEY from .secrets/lab.env (ignored by git).
#   ./lab.sh setup    once: a checkout of this repo on the lab (~/ragflow-lab), for CD
#   ./lab.sh status   version, containers, health, and the last start-up and CD lines
#   ./lab.sh up       install or upgrade to the latest release and start it, in the background (CD does this itself)
#   ./lab.sh down     stop the stack, keep its data
#   ./lab.sh purge    delete its data, images and ~/ragflow (asks first)
#   ./lab.sh deploy   run the CD step now (deploy/cd.sh on the lab), instead of waiting for its timer
#   ./lab.sh tunnel   the web UI on this machine's http://127.0.0.1:8088 (ctrl-c to stop)
# The commands run ragflow.sh (from this folder) on the lab; see it for the settings it takes.
set -euo pipefail

cmd=${1:-status}
here=$(cd "$(dirname "$0")" && pwd)
cd "$here"  # LAB_KEY in .secrets/lab.env is relative to this folder
if [ -z "${LAB:-}" ] && [ -f .secrets/lab.env ]; then . .secrets/lab.env; fi
: "${LAB:?set LAB (see .secrets/lab.env)}" "${LAB_KEY:?set LAB_KEY (see .secrets/lab.env)}"
WEB=${RAGFLOW_WEB_PORT:-8088}
REPO=nodalytics/ragflow-lab
ssh_opts=(-o IdentitiesOnly=yes -o ConnectTimeout=30 -o ServerAliveInterval=20 -i "$LAB_KEY")
lab() { ssh "${ssh_opts[@]}" "$LAB" "$@"; }

case $cmd in
tunnel)
  echo "RAGFlow on http://127.0.0.1:$WEB (ctrl-c to stop)"
  exec ssh -N "${ssh_opts[@]}" -L "$WEB:127.0.0.1:$WEB" "$LAB" ;;
setup)
  # the repo is public: the lab pulls it over https, with no key or token
  lab "REPO=$REPO bash -s" <<'REMOTE'
set -euo pipefail
C=$HOME/ragflow-lab
if [ ! -d "$C/.git" ]; then
  [ -d "$C" ] && mv "$C" "$C.before-cd-$(date +%Y%m%d%H%M%S)"  # the files earlier versions copied there
  git clone -q "https://github.com/$REPO.git" "$C"
fi
git -C "$C" fetch -q origin main && git -C "$C" reset -q --hard origin/main
echo "checkout ~/ragflow-lab at $(git -C "$C" log --oneline -1)"
echo "now, once, on the lab: sudo sh ~/ragflow-lab/deploy/install.sh   (the CD timer and the nginx site)"
REMOTE
  ;;
purge)
  read -r -p "Delete RAGFlow's data, images and ~/ragflow on the lab? [y/N] " ok
  [ "$ok" = y ] || exit 1
  lab "RAGFLOW_WEB_PORT=$WEB bash -s -- purge" <ragflow.sh ;;
deploy)
  lab 'bash ~/ragflow-lab/deploy/cd.sh --force' ;;
up | status | down | check | latest)
  lab "RAGFLOW_WEB_PORT=$WEB RAGFLOW_VERSION=${RAGFLOW_VERSION:-} RAGFLOW_EMBED_MODEL=${RAGFLOW_EMBED_MODEL:-BAAI/bge-m3} bash -s -- $cmd" <ragflow.sh ;;
*)
  echo "unknown command $cmd (setup, status, up, down, purge, deploy, tunnel)" >&2; exit 2 ;;
esac
