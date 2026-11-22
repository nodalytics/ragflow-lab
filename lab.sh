#!/usr/bin/env bash
# Host RAGFlow (https://github.com/infiniflow/ragflow) on the lab, at https://ragflow.stbfarm.org.
# See README.md here, and integration.md for why and how it fits.
#
# Run from your machine, anywhere in the repo (reads LAB and LAB_KEY from .secrets/lab.env):
#   research/ragflow/lab.sh up       install or upgrade to the latest release and start it (in the background)
#   research/ragflow/lab.sh status   version, containers, health, and the end of the start-up log
#   research/ragflow/lab.sh down     stop the stack, keep its data
#   research/ragflow/lab.sh purge    stop it and delete its data, images and ~/ragflow (asks first)
#   research/ragflow/lab.sh tunnel   the web UI on this machine's http://127.0.0.1:8088 (ctrl-c to stop)
# Then, once, on the lab: sudo sh ~/ragflow/lab/install-nginx.sh   (the public name, through the lab's nginx)
#
# On the lab the stack is the docker compose project "ragflow" in ~/ragflow, the release's own compose files with
# one override (lab-override.yml): the only published port is the web UI on 127.0.0.1:8088 (RAGFlow's nginx inside
# routes /api/v1 to its API); every database and queue stays on the stack's own network. Generated once and kept in
# ~/ragflow/lab-passwords.env (mode 600): the database passwords and the admin password (admin@ragflow.io).
# Self sign-up is off: the admin adds users. Embeddings come from a CPU text-embeddings service (tei-cpu).
# Environment: RAGFLOW_VERSION (default: the latest release), RAGFLOW_WEB_PORT (8088),
# RAGFLOW_EMBED_MODEL (BAAI/bge-m3, 21 GB of RAM; BAAI/bge-small-en-v1.5 needs 1.2 GB).
set -euo pipefail

cmd=${1:-up}
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
cd "$root"  # LAB_KEY in .secrets/lab.env is relative to the repo root
if [ -z "${LAB:-}" ] && [ -f "$root/.secrets/lab.env" ]; then . "$root/.secrets/lab.env"; fi
: "${LAB:?set LAB (see .secrets/lab.env)}" "${LAB_KEY:?set LAB_KEY (see .secrets/lab.env)}"
WEB=${RAGFLOW_WEB_PORT:-8088}
case $WEB in 8000 | 8790 | 8890) echo "port $WEB belongs to another lab service" >&2; exit 2 ;; esac
ssh_opts=(-o IdentitiesOnly=yes -o ConnectTimeout=30 -o ServerAliveInterval=20 -i "$LAB_KEY")

if [ "$cmd" = tunnel ]; then
  echo "RAGFlow on http://127.0.0.1:$WEB (ctrl-c to stop)"
  exec ssh -N "${ssh_opts[@]}" -L "$WEB:127.0.0.1:$WEB" "$LAB"
fi
if [ "$cmd" = purge ]; then
  read -r -p "Delete RAGFlow's data, images and ~/ragflow on the lab? [y/N] " ok
  [ "$ok" = y ] || exit 1
fi
if [ "$cmd" = up ]; then  # the nginx files, for install-nginx.sh on the lab
  ssh "${ssh_opts[@]}" "$LAB" 'mkdir -p ~/ragflow-lab'
  scp -q "${ssh_opts[@]}" "$here/install-nginx.sh" "$here/nginx/ragflow.stbfarm.org.conf" "$LAB:ragflow-lab/"
fi

ssh "${ssh_opts[@]}" "$LAB" "CMD=$cmd WEB=$WEB VERSION=${RAGFLOW_VERSION:-} EMBED=${RAGFLOW_EMBED_MODEL:-BAAI/bge-m3} bash -s" <<'REMOTE'
set -euo pipefail
R=$HOME/ragflow
D=$R/docker
LOG=$R/lab/up.log
compose() { (cd "$D" && docker compose -p ragflow -f docker-compose.yml -f lab-override.yml "$@"); }
health() { curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$WEB$1" || true; }

case $CMD in
status)
  if [ ! -d "$D" ]; then echo "not installed (no ~/ragflow)"; exit 0; fi
  echo "version $(git -C "$R" describe --tags 2>/dev/null)"
  docker ps -a --filter label=com.docker.compose.project=ragflow --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
  echo "web http://127.0.0.1:$WEB/: HTTP $(health /)   api healthz: HTTP $(health /api/v1/system/healthz)"
  [ -f "$LOG" ] && { echo "--- ~/ragflow/lab/up.log"; tail -6 "$LOG"; }
  exit 0 ;;
down)
  [ -f "$D/lab-override.yml" ] && compose down
  exit 0 ;;
purge)
  if [ -f "$D/lab-override.yml" ]; then
    imgs=$(compose config --images 2>/dev/null || true)
    compose down -v --remove-orphans || true
    # shellcheck disable=SC2086
    [ -n "$imgs" ] && docker image rm $imgs 2>/dev/null || true
  fi
  if [ -d "$R" ]; then  # logs the containers wrote as root
    docker run --rm --user 0 --entrypoint sh --mount "type=bind,source=$R,target=/x" alpine:3.20 \
      -c 'rm -rf /x/docker/ragflow-logs /x/history_data_agent' || true
    rm -rf "${R:?}"
  fi
  echo "purged (the nginx site, if installed: sudo sh ~/ragflow-lab/install-nginx.sh --remove)"
  exit 0 ;;
up) ;;
*) echo "unknown command $CMD (up, status, down, purge, tunnel)" >&2; exit 2 ;;
esac

# The release: the latest unless one is given
if [ -z "$VERSION" ]; then
  VERSION=$(curl -fsS -m 20 https://api.github.com/repos/infiniflow/ragflow/releases/latest \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])')
fi
echo "RAGFlow $VERSION"

# Checks before anything is pulled
docker compose version >/dev/null || { echo "needs docker with compose" >&2; exit 1; }
mmc=$(sysctl -n vm.max_map_count)
[ "$mmc" -ge 262144 ] || { echo "Elasticsearch needs vm.max_map_count >= 262144 (now $mmc)" >&2; exit 1; }
free=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
need=15  # the images (~8 GB with Elasticsearch and the embedding service), the model, and the index's headroom
[ -d "$D" ] && need=6
[ "$free" -ge "$need" ] || { echo "only ${free} GB free on the lab, needs ${need} GB" >&2; exit 1; }
if ss -ltnH "sport = :$WEB" | grep -q . \
  && ! docker ps --filter label=com.docker.compose.project=ragflow --format '{{.Ports}}' | grep -q ":$WEB->"; then
  echo "port $WEB is taken on the lab: set RAGFLOW_WEB_PORT" >&2; exit 1
fi

# The source at that release
if [ ! -d "$R/.git" ]; then
  git -c advice.detachedHead=false clone -q --depth 1 -b "$VERSION" https://github.com/infiniflow/ragflow "$R"
fi
git -C "$R" checkout -q -- docker/.env 2>/dev/null || true  # our settings are re-applied below
if [ "$(git -C "$R" describe --tags --exact-match 2>/dev/null || true)" != "$VERSION" ]; then
  echo "upgrading from $(git -C "$R" describe --tags 2>/dev/null || echo '?')"
  git -C "$R" fetch -q --depth 1 origin tag "$VERSION"
  git -C "$R" -c advice.detachedHead=false checkout -q "$VERSION"
fi
mkdir -p "$R/lab"
cp ~/ragflow-lab/* "$R/lab/" 2>/dev/null || true

# Settings: secrets made once and reused (the data volumes keep the first ones)
PW=$R/lab-passwords.env
if [ ! -f "$PW" ]; then
  ( umask 077
    for k in ELASTIC_PASSWORD MYSQL_PASSWORD MINIO_PASSWORD REDIS_PASSWORD ADMIN_DEFAULT_PASSWORD; do
      echo "$k=$(head -c 32 /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 24)"
    done > "$PW" )
fi
set_env() {
  grep -q "^$1=" "$D/.env" || { echo "docker/.env has no $1: check research/ragflow/lab.sh against $VERSION" >&2; exit 1; }
  sed -i "s|^$1=.*|$1=$2|" "$D/.env"
}
set_env RAGFLOW_IMAGE "infiniflow/ragflow:$VERSION"
for k in TZ TIMEZONE; do grep -q "^$k=" "$D/.env" && set_env "$k" UTC; done  # v1: TZ; older: TIMEZONE
set_env REGISTER_ENABLED 0
set_env TEI_MODEL "$EMBED"
sed -i 's|^\(COMPOSE_PROFILES=.*\)$|\1,tei-cpu|' "$D/.env"
grep -q '^COMPOSE_PROFILES=.*,tei-cpu$' "$D/.env" || { echo "could not add the embedding service" >&2; exit 1; }
while IFS='=' read -r k v; do set_env "$k" "$v"; done < "$PW"

# Ports: none published except the web UI, on localhost. Built from the resolved services, whatever the release has.
(cd "$D" && docker compose -p ragflow -f docker-compose.yml config --format json) | D=$D WEB=$WEB python3 -c '
import json, os
c = json.load(open(0))
app = [n for n in c["services"] if n.startswith("ragflow")]
assert len(app) == 1, f"expected one RAGFlow server service, got {app}"
out = ["services:"]
for n, s in c["services"].items():
    if n in app:
        out += [f"  {n}:", "    ports: !override", "      - \"127.0.0.1:" + os.environ["WEB"] + ":80\""]
    elif s.get("ports"):
        out += [f"  {n}:", "    ports: !reset []"]
open(os.path.join(os.environ["D"], "lab-override.yml"), "w").write("\n".join(out) + "\n")'
compose config --format json | python3 -c '
import json
c = json.load(open(0))
pub = [(n, p.get("host_ip"), p.get("published")) for n, s in c["services"].items() for p in s.get("ports", [])]
assert all(h == "127.0.0.1" for _, h, _ in pub) and len(pub) == 1, f"published: {pub}"
print("services:", ", ".join(sorted(c["services"])))
print("published:", ", ".join(f"{n} {h}:{p}" for n, h, p in pub))'

# Start in the background: the first pull is several GB, and an ssh drop must not stop it
( setsid nohup bash -c "cd '$D' && date && docker compose -p ragflow -f docker-compose.yml -f lab-override.yml up -d \
    && echo 'started; the server takes a few minutes to answer' || echo 'up FAILED'; date" > "$LOG" 2>&1 < /dev/null & )
echo "starting in the background (log ~/ragflow/lab/up.log); check: research/ragflow/lab.sh status"
REMOTE
