#!/bin/sh

export RUFF_CACHE_DIR=./ruff_cache

alembic upgrade head
ruff format src
uvicorn src.main:app --proxy-headers --forwarded-allow-ips='*' --host 0.0.0.0 --port 3000 --reload
