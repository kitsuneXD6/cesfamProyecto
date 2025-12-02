#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python cesfamProyecto/manage.py collectstatic --no-input
python cesfamProyecto/manage.py migrate
