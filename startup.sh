#!/bin/sh

alembic upgrade head
uvicorn src.main:app --proxy-headers --forwarded-allow-ips='*' --host 0.0.0.0 --port 3000 --reload
