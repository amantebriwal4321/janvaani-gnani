#!/bin/sh
# Production: built Next.js desk plus the FastAPI line.
set -eu
cd /app
. /opt/venv/bin/activate
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8766 &
cd /app/frontend
exec npx next start -H 0.0.0.0 -p 43123
