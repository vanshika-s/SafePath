#!/usr/bin/env bash
set -e
echo "==> Pre-downloading data before server start..."
python -c "from src.api.loader import download_data; download_data()"
echo "==> Data ready. Starting uvicorn..."
exec uvicorn app.api_server:app --host 0.0.0.0 --port "${PORT:-8000}"
