#!/bin/sh
# Once on the lab, with sudo, after ./lab.sh setup (from your machine) made the checkout ~/ragflow-lab:
#   sudo sh ~/ragflow-lab/deploy/install.sh            the CD timer and the nginx site for ragflow.stbfarm.org
#   sudo sh ~/ragflow-lab/deploy/install.sh --remove   take both away (RAGFlow itself keeps running)
# Re-run it after the nginx config changes (deploy/cd.sh says so in its log). Touches only its own files:
# /etc/systemd/system/ragflow-cd.{service,timer} and /etc/nginx/sites-{available,enabled}/ragflow.stbfarm.org.
set -eu
cd "$(dirname "$0")"
if [ "$(id -u)" != 0 ]; then echo "run with sudo" >&2; exit 1; fi
U=${SUDO_USER:?run with sudo from your own login}
H=$(getent passwd "$U" | cut -d: -f6)
if [ "${1:-}" = "--remove" ]; then
  systemctl disable --now ragflow-cd.timer 2>/dev/null || true
  rm -f /etc/systemd/system/ragflow-cd.service /etc/systemd/system/ragflow-cd.timer
  systemctl daemon-reload
  sh ./install-nginx.sh --remove
  exit 0
fi
[ -d "$H/ragflow-lab/.git" ] || { echo "no checkout at $H/ragflow-lab: ./lab.sh setup from your machine first" >&2; exit 1; }
sed -e "s|__USER__|$U|g" -e "s|__HOME__|$H|g" ragflow-cd.service > /etc/systemd/system/ragflow-cd.service
install -m 644 ragflow-cd.timer /etc/systemd/system/ragflow-cd.timer
systemctl daemon-reload
systemctl enable --now ragflow-cd.timer
echo "CD timer: $(systemctl is-active ragflow-cd.timer); next run: $(systemctl show ragflow-cd.timer -p NextElapseUSecRealtime --value)"
sh ./install-nginx.sh
