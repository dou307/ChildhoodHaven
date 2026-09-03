#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ] && [ -n "${DB_HOST:-}" ]; then
  : "${DB_USER:?DB_USER is required when DB_HOST is set}"
  : "${DB_PASSWORD:?DB_PASSWORD is required when DB_HOST is set}"
  : "${DB_NAME:?DB_NAME is required when DB_HOST is set}"
  : "${DB_PORT:=5432}"
  export DATABASE_URL="$(.venv/bin/python - <<'PY'
import os
from urllib.parse import quote

user = quote(os.environ["DB_USER"], safe="")
password = quote(os.environ["DB_PASSWORD"], safe="")
host = os.environ["DB_HOST"]
port = os.environ["DB_PORT"]
database = quote(os.environ["DB_NAME"], safe="")
print(f"postgresql://{user}:{password}@{host}:{port}/{database}")
PY
)"
fi

if [ -n "${DATABASE_URL:-}" ]; then
  .venv/bin/alembic upgrade head
fi
exec "$@"
