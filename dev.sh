#!/usr/bin/env bash
# One command for the local call: API on 8766, the desk on 43123.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r backend/requirements.txt

if [[ ! -d frontend/node_modules ]]; then
  npm install --prefix frontend
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
fi
set -a
# shellcheck disable=SC1091
source .env
set +a

uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8766 &
API_PID=$!
cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "JanVaani call   http://127.0.0.1:43123"
echo "API health      http://127.0.0.1:8766/api/health"
echo ""

cd frontend
exec npx next dev --turbopack -H 0.0.0.0 -p 43123
