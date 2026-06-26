#!/bin/sh

set -e

echo "🚀 Running prestart..."
python backend/backend_prestart.py

echo "🗄️ Initializing database..."
python backend/init_database.py

echo "☁️ Initializing S3 bucket..."
python backend/init_s3.py

# -----------------------------
# 🧪 TEST MODE CONTROLADO
# -----------------------------
if [ "$RUN_TESTS" = "true" ]; then
  echo "🧪 Running tests (blocking mode - CI)..."

  pytest backend/tests -vv -s

else
  echo "🧪 Running tests (non-blocking mode - DEV)..."

  # NO rompe el flujo si fallan
  pytest backend/tests -vv -s || echo "⚠️ Tests failed, but continuing..."
fi

echo "🚀 Starting API..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000