#!/usr/bin/env bash
# Coding models on the lab: Ollama in Docker on one GPU, serving an OpenAI-compatible API (and Anthropic's Messages
# API) on 127.0.0.1, published at https://coder.stbfarm.org behind API keys. Run by ../lab.sh coder ..., by the CD
# step (../deploy/cd.sh) and by CI (check).
#   coder.sh up [--wait]      start the server, pull the models, load the first one; --wait: in the foreground
#   coder.sh status           container, GPU, loaded and pulled models, health
#   coder.sh down             stop and remove the container (the models stay)
#   coder.sh purge            also delete the downloaded models
#   coder.sh key add NAME     make an API key for NAME (printed once); key list; key rm NAME
#   coder.sh check            validate the settings without starting anything
# Environment:
#   CODER_MODELS   space-separated Ollama models, the first loaded and kept loaded; NAME=SOURCE downloads SOURCE (e.g.
#                  a hf.co/... GGUF) and serves it as NAME (default: qwen3.8-abliterated:27b, from huihui-ai's
#                  abliterated GGUF, kept loaded; and the stock qwen3.8:27b). One model fits on the GPU at a time: asking for another swaps it in.
#   CODER_GPU      which GPU, by a word of its name (default 4090)
#   CODER_CONTEXT  context length in tokens (default 98304: 22 of the 4090's 24 GB with qwen3.8:27b; 131072 spills)
#   CODER_PORT     the lab port, on 127.0.0.1 (default 11435)
#   CODER_IMAGE    the Ollama image (default ollama/ollama:latest)
#   CODER_DIR      models and keys (default ~/coder)
set -euo pipefail

CMD=${1:-status}
C=${CODER_DIR:-$HOME/coder}
MODELS=${CODER_MODELS:-qwen3.8-abliterated:27b=hf.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF:Q4_K_M qwen3.8:27b}
GPU=${CODER_GPU:-4090}
CTX=${CODER_CONTEXT:-98304}
PORT=${CODER_PORT:-11435}
IMAGE=${CODER_IMAGE:-ollama/ollama:latest}
NAME=coder-ollama
KEYS=$C/api-keys
FIRST=${MODELS%% *}
FIRST=${FIRST%%=*}
NAMES=$(for m in $MODELS; do printf '%s ' "${m%%=*}"; done)
case $PORT in 8000 | 8088 | 8790 | 8890 | 11434) echo "port $PORT is used by another lab service" >&2; exit 2 ;; esac

api() { curl -fsS -m "${2:-10}" "http://127.0.0.1:$PORT$1"; }
gpu_uuid() {
  nvidia-smi --query-gpu=uuid,name --format=csv,noheader | awk -F', ' -v g="$GPU" 'index($2, g) {print $1; exit}'
}
# the settings that decide whether a running container can be kept
config() { printf '%s|%s|%s|%s|%s' "$IMAGE" "$(gpu_uuid)" "$CTX" "$PORT" "v1"; }

check_settings() {
  [ -n "$FIRST" ] || { echo "CODER_MODELS is empty" >&2; exit 1; }
  [ "$CTX" -ge 8192 ] || { echo "CODER_CONTEXT $CTX is too small for a coding agent" >&2; exit 1; }
  for m in $MODELS; do
    case $m in *[!A-Za-z0-9._:/=-]*) echo "bad model name: $m" >&2; exit 1 ;; esac
  done
  echo "models: $NAMES(loaded: $FIRST), GPU: $GPU, context: $CTX, port 127.0.0.1:$PORT, image: $IMAGE"
}

case $CMD in
check)
  check_settings
  echo "check passed" ;;

status)
  if ! docker inspect "$NAME" >/dev/null 2>&1; then echo "not running (no $NAME container)"; exit 0; fi
  docker ps -a --filter "name=^$NAME$" --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
  docker exec "$NAME" ollama ps 2>/dev/null || true
  echo "--- pulled"; docker exec "$NAME" ollama list 2>/dev/null | awk 'NR > 1 {print "  " $1 "  " $3 " " $4}'
  printf 'api /v1/models: %s\n' "$(api /v1/models >/dev/null 2>&1 && echo ok || echo FAILED)"
  [ -f "$C/up.log" ] && { echo "--- $C/up.log"; tail -3 "$C/up.log"; }
  [ -f "$KEYS" ] && echo "keys: $(awk '{print $1}' "$KEYS" | tr '\n' ' ')"
  exit 0 ;;

down)
  docker rm -f "$NAME" >/dev/null 2>&1 && echo "stopped" || echo "not running" ;;

purge)
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  if [ -d "$C/models" ]; then  # written by the container as root
    docker run --rm --entrypoint sh --mount "type=bind,source=$C,target=/x" "$IMAGE" -c 'rm -rf /x/models'
  fi
  echo "purged the server and its models (keys kept in $KEYS)" ;;

key)
  sub=${2:-list}
  who=${3:-}
  mkdir -p "$C"
  touch "$KEYS" && chmod 600 "$KEYS"
  case $sub in
  list) awk '{print $1}' "$KEYS" ;;
  add)
    case $who in '' | *[!A-Za-z0-9._-]*) echo "usage: coder.sh key add NAME (letters, digits, . _ -)" >&2; exit 2 ;; esac
    if awk -v w="$who" '$1 == w {f = 1} END {exit !f}' "$KEYS"; then echo "$who already has a key" >&2; exit 1; fi
    k="sk-lab-$(head -c 32 /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 40)"
    echo "$who $k" >>"$KEYS"
    echo "key for $who (shown once; it works after: sudo sh ~/ragflow-lab/deploy/install.sh):"
    echo "$k" ;;
  rm)
    awk -v w="$who" '$1 != w' "$KEYS" >"$KEYS.new" && mv "$KEYS.new" "$KEYS" && chmod 600 "$KEYS"
    echo "removed $who (takes effect after: sudo sh ~/ragflow-lab/deploy/install.sh)" ;;
  *) echo "key add NAME | key list | key rm NAME" >&2; exit 2 ;;
  esac ;;

up)
  check_settings >/dev/null
  docker info --format '{{json .Runtimes}}' | grep -q nvidia || { echo "docker has no nvidia runtime" >&2; exit 1; }
  uuid=$(gpu_uuid)
  [ -n "$uuid" ] || { echo "no GPU named like '$GPU'" >&2; exit 1; }
  mkdir -p "$C/models"
  want=$(config)
  have=$(docker inspect -f '{{index .Config.Labels "coder.config"}}' "$NAME" 2>/dev/null || true)
  running=$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null || echo false)
  if [ "$have" != "$want" ] || [ "$running" != true ]; then
    if ss -ltnH "sport = :$PORT" | grep -q . && [ "$running" != true ]; then
      echo "port $PORT is taken: set CODER_PORT" >&2; exit 1
    fi
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker run -d --name "$NAME" --restart unless-stopped --gpus "device=$uuid" \
      -p "127.0.0.1:$PORT:11434" --mount "type=bind,source=$C/models,target=/root/.ollama" \
      -e OLLAMA_CONTEXT_LENGTH="$CTX" -e OLLAMA_FLASH_ATTENTION=1 -e OLLAMA_KV_CACHE_TYPE=q8_0 \
      -e OLLAMA_KEEP_ALIVE=-1 -e OLLAMA_MAX_LOADED_MODELS=1 -e OLLAMA_NUM_PARALLEL=1 \
      --label "coder.config=$want" "$IMAGE" >/dev/null
    echo "started $NAME on the $GPU (127.0.0.1:$PORT)"
  fi
  for _ in $(seq 1 30); do api /api/version >/dev/null 2>&1 && break; sleep 2; done
  api /api/version >/dev/null || { echo "Ollama did not answer" >&2; docker logs --tail 20 "$NAME" >&2; exit 1; }

  # pulling: ~19 GB for the default model, so check the disk first and pull in the background unless --wait
  pull='set -e
for m in '"$MODELS"'; do
  name=${m%%=*}; src=${m#*=}
  if ! ollama show "$name" >/dev/null 2>&1; then
    echo "pulling $src"; ollama pull "$src" >/dev/null
    if [ "$src" != "$name" ]; then ollama cp "$src" "$name" && ollama rm "$src" >/dev/null; fi
  fi
done
echo "pulled: '"$NAMES"'"'
  missing=0
  for m in $NAMES; do docker exec "$NAME" ollama show "$m" >/dev/null 2>&1 || missing=1; done
  if [ "$missing" = 1 ]; then
    free=$(df -BG --output=avail "$C" | tail -1 | tr -dc 0-9)
    [ "$free" -ge 25 ] || { echo "only ${free} GB free; pulling models needs 25 GB" >&2; exit 1; }
  fi
  load="curl -fsS -m 600 http://127.0.0.1:$PORT/api/generate -d '{\"model\":\"$FIRST\",\"keep_alive\":-1}' >/dev/null && echo 'loaded $FIRST'"
  if [ "${2:-}" = --wait ]; then
    { date; docker exec "$NAME" sh -c "$pull" && eval "$load"; date; } >"$C/up.log" 2>&1 || { tail -5 "$C/up.log" >&2; exit 1; }
    tail -3 "$C/up.log"
    docker exec "$NAME" ollama ps | awk -v m="$FIRST" '$1 == m' | grep -q "100% GPU" \
      || { echo "$FIRST is not fully on the GPU: lower CODER_CONTEXT" >&2; docker exec "$NAME" ollama ps >&2; exit 1; }
    echo "healthy: $FIRST fully on the $GPU, context $CTX"
  else
    (setsid nohup bash -c "date; docker exec $NAME sh -c '$pull' && $load; date" >"$C/up.log" 2>&1 </dev/null &)
    echo "pulling and loading in the background (log $C/up.log)"
  fi ;;

*)
  echo "unknown command $CMD (up, status, down, purge, key, check)" >&2; exit 2 ;;
esac
