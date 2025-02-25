#!/bin/sh

cd /usr/app/
alembic -c ./scripts/alembic.ini upgrade head
uvicorn src.main:app --proxy-headers --forwarded-allow-ips='*' --host 0.0.0.0 --port 3000
#tail -f /dev/null
