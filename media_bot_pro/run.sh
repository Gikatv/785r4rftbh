#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
set -a
[ -f .env ] && source .env
set +a
python3 main.py
