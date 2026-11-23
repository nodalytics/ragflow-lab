#!/bin/sh
# Publish the lab's sites through its nginx. Called by deploy/install.sh (sudo); alone:
#   sudo sh ~/ragflow-lab/deploy/install-nginx.sh            (to remove both sites: --remove)
#   ragflow.stbfarm.org  RAGFlow (lab 127.0.0.1:8088)
#   coder.stbfarm.org    the coding models (lab 127.0.0.1:11435), with /etc/nginx/coder-keys.map written from the API
#                        keys in ~/coder/api-keys (coder/coder.sh key add NAME); re-run after adding or removing a key
# Installs only these files: /etc/nginx/sites-{available,enabled}/{ragflow,coder}.stbfarm.org and coder-keys.map.
# Re-running it is safe.
set -eu
cd "$(dirname "$0")"
if [ "$(id -u)" != 0 ]; then echo "run with sudo" >&2; exit 1; fi
U=${SUDO_USER:?run with sudo from your own login}
H=$(getent passwd "$U" | cut -d: -f6)

if [ "${1:-}" = "--remove" ]; then
  for SITE in ragflow.stbfarm.org coder.stbfarm.org; do
    rm -f /etc/nginx/sites-enabled/$SITE /etc/nginx/sites-available/$SITE
  done
  rm -f /etc/nginx/coder-keys.map
  nginx -t && systemctl reload nginx
  echo "removed"
  exit 0
fi

enabled=""
site() {  # site NAME CONF: install and enable one vhost
  install -m 644 "$2" "/etc/nginx/sites-available/$1"
  ln -sf "/etc/nginx/sites-available/$1" "/etc/nginx/sites-enabled/$1"
  enabled="$enabled $1"
}

code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:8088/ || true)
if [ "$code" = 200 ]; then site ragflow.stbfarm.org ../nginx/ragflow.stbfarm.org.conf
else echo "RAGFlow is not answering on 127.0.0.1:8088 (HTTP $code): ragflow.stbfarm.org skipped" >&2; fi

if curl -fs -o /dev/null -m 5 http://127.0.0.1:11435/api/version; then
  # the key map: readable by root only; a key that is not exactly letters and digits is refused
  umask 077
  : >/etc/nginx/coder-keys.map.new
  if [ -f "$H/coder/api-keys" ]; then
    while read -r who key; do
      case "$who$key" in *[!A-Za-z0-9._-]*) echo "skipped a malformed key line" >&2; continue ;; esac
      [ -n "$key" ] && printf '"Bearer %s" "%s";\n' "$key" "$who" >>/etc/nginx/coder-keys.map.new
    done <"$H/coder/api-keys"
  fi
  mv /etc/nginx/coder-keys.map.new /etc/nginx/coder-keys.map
  umask 022
  n=$(wc -l </etc/nginx/coder-keys.map)
  [ "$n" -gt 0 ] || echo "no API keys yet: coder.stbfarm.org refuses every request (coder/coder.sh key add NAME)" >&2
  site coder.stbfarm.org ../coder/nginx/coder.stbfarm.org.conf
else
  echo "the coding models are not answering on 127.0.0.1:11435: coder.stbfarm.org skipped" >&2
fi

if nginx -t; then
  systemctl reload nginx
else
  for SITE in $enabled; do rm -f "/etc/nginx/sites-enabled/$SITE"; done
  echo "nginx config test failed; the sites were not enabled" >&2
  exit 1
fi
# a reload is asynchronous: until the new workers run, a request can land on another vhost
for SITE in $enabled; do
  path=/
  [ "$SITE" = coder.stbfarm.org ] && path=/v1/models  # 401 without a key: the site is working
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    code=$(curl -sk -o /dev/null -w "%{http_code}" --resolve "$SITE:443:127.0.0.1" "https://$SITE$path")
    [ "$code" = 200 ] || [ "$code" = 401 ] && break
    sleep 1
  done
  echo "https://$SITE$path answers $code on the lab (200, or 401 without a key, expected)"
done
