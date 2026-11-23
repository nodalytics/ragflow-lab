#!/usr/bin/env bash
# RAGFlow on this machine (the lab): install or upgrade, start, stop, check. Run by lab.sh over ssh, by the CD
# timer (deploy/cd.sh) on the lab, and by CI (check only).
#   ragflow.sh up [--wait]   install or upgrade to the release, start it; --wait: in the foreground until healthy
#   ragflow.sh status        version, containers, health
#   ragflow.sh down          stop, keep the data
#   ragflow.sh purge         delete the data, the images and the install
#   ragflow.sh check         dry run in a temporary folder: fetch the release, apply our settings and ports, validate
#   ragflow.sh latest        the latest release's tag
# Environment: RAGFLOW_VERSION (default: the latest release), RAGFLOW_WEB_PORT (8088), RAGFLOW_EMBED_MODEL
# (BAAI/bge-m3, 21 GB of RAM; BAAI/bge-small-en-v1.5 needs 1.2 GB), RAGFLOW_DIR (~/ragflow).
#
# The stack is the docker compose project "ragflow": the release's own compose files, our settings in docker/.env,
# and one override (docker/lab-override.yml) that publishes only the web UI, on 127.0.0.1. Secrets are made once and
# kept in $RAGFLOW_DIR/lab-passwords.env (mode 600).
set -euo pipefail

CMD=${1:-status}
WAIT=0
[ "${2:-}" = --wait ] && WAIT=1
R=${RAGFLOW_DIR:-$HOME/ragflow}
WEB=${RAGFLOW_WEB_PORT:-8088}
EMBED=${RAGFLOW_EMBED_MODEL:-BAAI/bge-m3}
VERSION=${RAGFLOW_VERSION:-}
case $WEB in 8000 | 8790 | 8890) echo "port $WEB belongs to another lab service" >&2; exit 2 ;; esac

latest() {
  curl -fsS -m 20 https://api.github.com/repos/infiniflow/ragflow/releases/latest \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])'
}
health() { curl -s -o /dev/null -w '%{http_code}' -m 5 "http://127.0.0.1:$WEB$1" || true; }
compose() { (cd "$R/docker" && docker compose -p ragflow -f docker-compose.yml -f lab-override.yml "$@"); }

# The release's source in $R, our settings, and the port override, validated. Starts nothing.
prepare() {
  local D=$R/docker
  if [ ! -d "$R/.git" ]; then
    git -c advice.detachedHead=false clone -q --depth 1 -b "$VERSION" https://github.com/infiniflow/ragflow "$R"
  fi
  git -C "$R" checkout -q -- docker/.env 2>/dev/null || true  # our settings are re-applied below
  if [ "$(git -C "$R" describe --tags --exact-match 2>/dev/null || true)" != "$VERSION" ]; then
    echo "upgrading from $(git -C "$R" describe --tags 2>/dev/null || echo '?') to $VERSION"
    git -C "$R" fetch -q --depth 1 origin tag "$VERSION"
    git -C "$R" -c advice.detachedHead=false checkout -q "$VERSION"
  fi
  mkdir -p "$R/lab"

  local PW=$R/lab-passwords.env
  if [ ! -f "$PW" ]; then
    (
      umask 077
      for k in ELASTIC_PASSWORD MYSQL_PASSWORD MINIO_PASSWORD REDIS_PASSWORD ADMIN_DEFAULT_PASSWORD; do
        echo "$k=$(head -c 32 /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 24)"
      done >"$PW"
    )
  fi
  set_env() {
    grep -q "^$1=" "$D/.env" || { echo "docker/.env of $VERSION has no $1: update ragflow.sh" >&2; return 1; }
    sed -i "s|^$1=.*|$1=$2|" "$D/.env"
  }
  set_env RAGFLOW_IMAGE "infiniflow/ragflow:$VERSION"
  for k in TZ TIMEZONE; do  # v1: TZ; older: TIMEZONE
    if grep -q "^$k=" "$D/.env"; then set_env "$k" UTC; fi
  done
  set_env REGISTER_ENABLED 0
  set_env TEI_MODEL "$EMBED"
  sed -i 's|^\(COMPOSE_PROFILES=.*\)$|\1,tei-cpu|' "$D/.env"
  grep -q '^COMPOSE_PROFILES=.*,tei-cpu$' "$D/.env" || { echo "could not add the embedding service" >&2; return 1; }
  while IFS='=' read -r k v; do set_env "$k" "$v"; done <"$PW"

  # Ports: none published except the web UI, on localhost; built from the services the release defines
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
}

case $CMD in
latest)
  latest ;;
status)
  if [ ! -d "$R/docker" ]; then echo "not installed (no $R)"; exit 0; fi
  echo "version $(git -C "$R" describe --tags 2>/dev/null)"
  docker ps -a --filter label=com.docker.compose.project=ragflow --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
  echo "web http://127.0.0.1:$WEB/: HTTP $(health /)   api healthz: HTTP $(health /api/v1/system/healthz)"
  [ -f "$R/lab/up.log" ] && { echo "--- $R/lab/up.log"; tail -4 "$R/lab/up.log"; }
  [ -f "$R/lab/cd.log" ] && { echo "--- $R/lab/cd.log (CD)"; tail -4 "$R/lab/cd.log"; }
  exit 0 ;;
down)
  if [ -f "$R/docker/lab-override.yml" ]; then compose down; fi ;;
purge)
  if [ -f "$R/docker/lab-override.yml" ]; then
    imgs=$(compose config --images 2>/dev/null || true)
    compose down -v --remove-orphans || true
    # shellcheck disable=SC2086
    if [ -n "$imgs" ]; then docker image rm $imgs 2>/dev/null || true; fi
  fi
  if [ -d "$R" ]; then  # logs the containers wrote as root
    docker run --rm --user 0 --entrypoint sh --mount "type=bind,source=$R,target=/x" alpine:3.20 \
      -c 'rm -rf /x/docker/ragflow-logs /x/history_data_agent' || true
    rm -rf "${R:?}"
  fi
  echo "purged (the nginx site, if installed: sudo sh ~/ragflow-lab/deploy/install.sh --remove)" ;;
check)
  [ -n "$VERSION" ] || VERSION=$(latest)
  echo "RAGFlow $VERSION (dry run)"
  R=$(mktemp -d)
  trap 'rm -rf "${R:?}"' EXIT
  R=$R/ragflow
  prepare
  echo "check passed" ;;
up)
  [ -n "$VERSION" ] || VERSION=$(latest)
  echo "RAGFlow $VERSION"
  docker compose version >/dev/null || { echo "needs docker with compose" >&2; exit 1; }
  mmc=$(sysctl -n vm.max_map_count)
  [ "$mmc" -ge 262144 ] || { echo "Elasticsearch needs vm.max_map_count >= 262144 (now $mmc)" >&2; exit 1; }
  free=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
  need=15  # the images (~8 GB with Elasticsearch and the embedding service), the model, and the index's headroom
  [ -d "$R/docker" ] && need=6
  [ "$free" -ge "$need" ] || { echo "only ${free} GB free, needs ${need} GB" >&2; exit 1; }
  if ss -ltnH "sport = :$WEB" | grep -q . \
    && ! docker ps --filter label=com.docker.compose.project=ragflow --format '{{.Ports}}' | grep -q ":$WEB->"; then
    echo "port $WEB is taken: set RAGFLOW_WEB_PORT" >&2; exit 1
  fi
  prepare
  start="date && docker compose -p ragflow -f docker-compose.yml -f lab-override.yml up -d --remove-orphans \
    && echo 'started; the server takes a few minutes to answer' || { echo 'up FAILED'; exit 1; }"
  if [ "$WAIT" = 1 ]; then
    (cd "$R/docker" && bash -c "$start") >"$R/lab/up.log" 2>&1 || { tail -20 "$R/lab/up.log" >&2; exit 1; }
    for _ in $(seq 1 60); do  # up to 10 minutes
      [ "$(health /api/v1/system/healthz)" = 200 ] && { echo "healthy"; exit 0; }
      sleep 10
    done
    echo "not healthy after 10 minutes" >&2; exit 1
  fi
  # in the background: the first pull is several GB, and an ssh drop must not stop it
  (setsid nohup bash -c "cd '$R/docker' && $start; date" >"$R/lab/up.log" 2>&1 </dev/null &)
  echo "starting in the background (log $R/lab/up.log)" ;;
*)
  echo "unknown command $CMD (up, status, down, purge, check, latest)" >&2; exit 2 ;;
esac
