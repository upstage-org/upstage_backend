#!/bin/sh

cd /usr/app/
alembic -c ./scripts/alembic.ini upgrade head
uvicorn upstage_backend.main:app --proxy-headers --forwarded-allow-ips='*' --host 0.0.0.0 --port 3000
#tail -f /dev/null
