#!/bin/sh
# Publish RAGFlow at https://ragflow.stbfarm.org through the lab's nginx. Run once on the lab, with sudo, after
# research/ragflow/lab.sh up has copied this file there:
#   sudo sh ~/ragflow-lab/install-nginx.sh            (to remove the site: --remove)
# Installs only the vhost: /etc/nginx/sites-{available,enabled}/ragflow.stbfarm.org. Re-running it is safe.
set -eu
cd "$(dirname "$0")"
SITE=ragflow.stbfarm.org
PORT=8088
if [ "$(id -u)" != 0 ]; then echo "run with sudo" >&2; exit 1; fi
if [ "${1:-}" = "--remove" ]; then
  rm -f /etc/nginx/sites-enabled/$SITE /etc/nginx/sites-available/$SITE
  nginx -t && systemctl reload nginx
  echo "removed"
  exit 0
fi
code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://127.0.0.1:$PORT/ || true)
[ "$code" = 200 ] || { echo "RAGFlow is not answering on 127.0.0.1:$PORT (HTTP $code): research/ragflow/lab.sh up, then status" >&2; exit 1; }
install -m 644 $SITE.conf /etc/nginx/sites-available/$SITE
ln -sf /etc/nginx/sites-available/$SITE /etc/nginx/sites-enabled/$SITE
if nginx -t; then
  systemctl reload nginx
else
  rm -f /etc/nginx/sites-enabled/$SITE
  echo "nginx config test failed; the site was not enabled" >&2
  exit 1
fi
# a reload is asynchronous: until the new workers run, the request can land on another vhost
for _ in 1 2 3 4 5 6 7 8 9 10; do
  code=$(curl -sk -o /dev/null -w "%{http_code}" --resolve $SITE:443:127.0.0.1 https://$SITE/)
  [ "$code" = 200 ] && break
  sleep 1
done
echo "https://$SITE answers $code on the lab (200 expected); it needs a Cloudflare-proxied DNS record for $SITE"
