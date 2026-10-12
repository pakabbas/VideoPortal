#!/usr/bin/env bash
# Run on GCP3 as pakabbas52 (with sudo for nginx/systemd/mysql as needed).
set -euo pipefail

APP_DIR=/var/www/html/leadpilotai/videoportal
SERVICE=videoportal.service

echo "==> App dir: ${APP_DIR}"
cd "${APP_DIR}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

mkdir -p uploads secrets static/docs
sudo chown -R pakabbas52:www-data "${APP_DIR}"
sudo chmod g+rwxs "${APP_DIR}" uploads

if [[ -f schema.sql ]]; then
  echo "==> Apply schema (enter MySQL root/sudo password if prompted)"
  # Prefer app DB user if .env already set; otherwise document manual step
  echo "Run: sudo mysql < schema.sql   (or mysql -u root -p < schema.sql)"
fi

export FLASK_APP=wsgi:app
.venv/bin/flask init-db || true

echo "==> Install systemd unit"
sudo cp deploy/videoportal.service /etc/systemd/system/${SERVICE}
sudo systemctl daemon-reload
sudo systemctl enable --now ${SERVICE}
sudo systemctl status ${SERVICE} --no-pager || true

echo "==> Remember to add nginx snippet from deploy/nginx-videoportal.conf.snippet"
echo "    then: sudo nginx -t && sudo systemctl reload nginx"
echo "Done."
