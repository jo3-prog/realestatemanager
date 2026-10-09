#!/usr/bin/env bash
# Render runs this ONCE per deploy (the "Build Command").
set -o errexit   # stop immediately if any command fails

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input   # gather CSS/JS for admin + Swagger
python manage.py migrate --no-input         # create/update database tables
python manage.py ensure_superuser           # first admin from env vars (idempotent)

# Optional: load demo data by setting SEED_DEMO=true in Render (never for real data!)
if [ "$SEED_DEMO" = "true" ]; then
  python manage.py seed_demo
fi