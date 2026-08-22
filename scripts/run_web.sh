#!/usr/bin/env bash
# One origin for judges: http://localhost:3000
# Next.js proxies /api/* → FastAPI :8000
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-/home/sudheesh02/miniforge3/envs/amp-data/bin}"
export PATH="$PY:$PATH"

if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "starting FastAPI on :8000"
  (cd "$ROOT" && uvicorn main:app --app-dir services/predict_api --host 127.0.0.1 --port 8000) &
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
    sleep 0.5
  done
else
  echo "FastAPI already on :8000"
fi

cd "$ROOT/frontend"
echo "open http://localhost:3000  (API is /api on the same origin)"
exec npm run dev
