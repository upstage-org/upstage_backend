# UpStage Backend

UpStage is an open-source platform for live online performance: performers
("players") manipulate avatars, props, backdrops and streams on a shared
stage, watched live by an audience in the browser.

This repository is the backend. It provides:

- **HTTP API** — FastAPI + Ariadne GraphQL, served at **`/api/studio_graphql`**
  (see [API.md](API.md) for request/response examples).
- **Realtime** — MQTT (Mosquitto). Live-stage traffic goes over MQTT topics
  `<namespace>/<stage>/<topic>`; the browser connects via WebSocket.
- **Persistence** — PostgreSQL, migrated with Alembic.
- **Workers** — `event_archive` (persists MQTT events to Postgres so
  performances can be replayed) and `upstage_stats` (live audience/player
  counts).

The frontend (Vue SPA) lives in the sibling
[`upstage_frontend`](../upstage_frontend) repository and has its own README.
For architecture depth (module map, data model, GraphQL + MQTT flows, the
DB-session model) see [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

---

## Architecture & ports

Deployment is two docker-compose tiers on one shared external network
(`upstage-network-<site>`, where `<site>` is `dev` or `prod`):

| Tier | Directory | Services |
|---|---|---|
| Service tier | `service_containers/` | `postgres_container_<site>` (Postgres), `mosquitto_container_<site>` (MQTT broker) |
| App tier | `app_containers/` | `upstage_db_migrate` (one-shot: `alembic upgrade heads`), `upstage_backend` (API), `upstage_event_archive`, `upstage_stats` |

Application code and the Python venv are **baked into the image at build
time** (no source bind mounts). The three long-running app services wait for
the one-shot migration container to finish (`service_completed_successfully`)
before starting.

**Ports:**

| What | Where |
|---|---|
| Backend API (uvicorn) | container `:3000` → host `:9090` (dev) / `:9091` (prod) |
| Postgres | `:5432` inside the docker network only (not host-published) |
| Mosquitto MQTT (tcp) | `:1883` inside the docker network only |
| Mosquitto WebSocket | `127.0.0.1:9001` (dev) / `127.0.0.1:9002` (prod) |
| Uploaded media | bind mount `/app_code_<site>/uploads` ↔ `/usr/app/uploads` |

### TLS: all SSL is stripped at nginx

Every service behind the reverse proxy speaks **plain HTTP / plain
WebSocket**. nginx (or your proxy of choice) terminates all TLS and forwards:

- `https://<host>/api/` → `http://127.0.0.1:9090` (dev) or `:9091` (prod)
- `https://<host>/resources/` → served directly from `/app_code_<site>/uploads`
- `wss://mqtt-<host>:443` → `http://127.0.0.1:9001` (dev) / `:9002` (prod)
  (WebSocket upgrade; this is the browser's MQTT connection)
- everything else → the frontend's built `dist/` (see the frontend README;
  the SPA needs an HTML5-history fallback: `try_files $uri /index.html`)

No ready-made nginx config ships for this flow; the templates under
`initial_scripts/nginx_templates/` are reference material from the old
installer and need adapting. HTTPS is required in production — browsers only
grant camera/microphone access to secure origins.

---

## Setting up an instance

Prerequisites: Docker with the compose plugin. (Python 3.12 is only needed
for host-side development, not to run the stack.)

### 1. Configuration files

**a) `src/upstage_backend/global_config/load_env.py`** — the real runtime
configuration. It is gitignored and overrides everything in
`global_config/env.py` (imported last via `from .load_env import *`).
Sample, copied from a working dev instance with secrets X'd out:

```python
HOSTNAME="dev.example.org"

DATABASE_CONNECT = "postgresql"
DATABASE_HOST = "postgres_container_dev"   # container name on the shared network
DATABASE_PORT = 5432
DATABASE_USER = "postgres"
DATABASE_PASSWORD = "XXXXXXXXXXXX"
DATABASE_NAME = "upstage"

EMAIL_USE_TLS = False  # seems counterintuitive, but TLS happens by default.
EMAIL_HOST = "mail.smtp2go.com"
EMAIL_HOST_FROM = "support@example.org"
EMAIL_HOST_LOGIN = "example_login"
EMAIL_HOST_PASSWORD = "XXXXXXXXXXXXXXXX"
EMAIL_PORT = 587
EMAIL_HOST_DISPLAY_NAME = "UpStage Support"

MQTT_BROKER = "mosquitto_container_dev"    # container name on the shared network
MQTT_TRANSPORT = "tcp"
MQTT_ADMIN_USER = "admin"
MQTT_ADMIN_PASSWORD = "XXXXXXXXXXXXX"      # must match pw.backup (see below)
MQTT_ADMIN_PORT = 1883
MQTT_USER = "performance"
MQTT_PASSWORD = "XXXXXXXXXXXXX"            # must match pw.backup AND the frontend's VITE_MQTT_PASSWORD
MQTT_PORT = 1883

CLOUDFLARE_CAPTCHA_SECRETKEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
SECRET_KEY = "XXXX"   # JWT signing key: openssl rand -hex 48
CIPHER_KEY = b"XXXX"  # Fernet key (bytes!): python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"

CLIENT_MAX_BODY_SIZE = 500 * 1024 * 1024

UPLOAD_USER_CONTENT_FOLDER = "/usr/app/uploads"   # mounted this way in docker-compose
DEMO_MEDIA_FOLDER = "/usr/app/dashboard/demo"

# Payment — only for instances that sell subscriptions; leave empty otherwise.
STRIPE_KEY = ""
STRIPE_PRODUCT_ID = ""

# Email proxying — upstage.live-specific; leave as-is/empty for other instances.
ACCEPT_EMAIL_HOST = ["dev.example.org"]
ACCEPT_SERVER_SEND_EMAIL_EXTERNAL = []
SEND_EMAIL_SERVER = "https://dev.example.org"

# Change to "Production" for official releases (locks down CORS to HOSTNAME).
ENV_TYPE = "Dev"

JWT_ACCESS_TOKEN_MINUTES = "86400"  # 1 day
JWT_REFRESH_TOKEN_DAYS = "30"

# RTMP streaming (optional, needs an external MediaMTX server): shared secret
# for signing publish tokens. Generate with: openssl rand -hex 24
STREAM_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
```

Notes:
- `DATABASE_HOST`/`MQTT_BROKER` are the *container names*; the app tier
  reaches them over the shared docker network on their internal ports
  (5432/1883). Do not use the old proxied ports (5433/1884) from
  `initial_scripts/environments/env_app_template.py` — that template predates
  the compose flow.
- `MONGO_*` variables found in older configs are legacy and unused.

**b) `.env`** (repo root) — one line, consumed by the service-tier script:

```sh
export POSTGRES_PASSWORD_DEV=XXXXXXXXXXXX
```

(Use `POSTGRES_PASSWORD_PROD` for a prod site. Must match
`DATABASE_PASSWORD` in `load_env.py`.)

**c) Mosquitto passwords** — the service-tier script seeds
`/mosquitto_files_<site>/etc/mosquitto/` from
`service_containers/deployment_config/etc_mosquitto/` on first run, then asks
you to edit `pw.backup` (it refuses to start while the defaults say
`changeme`):

```
performance:XXXXXXXXXXXXX
admin:XXXXXXXXXXXXX
```

These must match `MQTT_PASSWORD` / `MQTT_ADMIN_PASSWORD` in `load_env.py`.
The broker hashes this file into its real password file at container start.

### 2. Bring up the service tier

```sh
cd service_containers
./run_docker_compose_dev.sh      # or run_docker_compose_prod.sh
```

This creates the external network `upstage-network-<site>`, the host data
dirs (`/postgres_data_<site>`, `/mosquitto_files_<site>`), and starts
Postgres + Mosquitto. Site-specific settings (hostname, exposed WS port,
optional certbot for the MQTT hostname) are variables at the top of the
script.

### 3. Bring up the app tier

```sh
cd app_containers
./run_docker_compose_dev.sh      # or run_docker_compose_prod.sh
```

This builds the image (sources baked in, dependencies from `uv.lock`),
creates `/app_code_<site>/uploads`, runs the one-shot migration container
(`alembic upgrade heads` — creates the entire schema from empty), then starts
the API and the two workers. The API is now on `http://127.0.0.1:9090`
(dev) / `:9091` (prod).

### 4. First login

Migrations seed a default super admin: **username `admin`, password
`Secret@123`** (`users/db_migrations/eb504467a5d7_create_default_super_admin.py`).
**Log in and change this password immediately.**

Optional demo data (a "Demo Stage" plus demo media):

```sh
./initial_scripts/post_install/scaffold_base_media.sh
```

### 5. Front it with nginx

See the TLS section above and the frontend README for the static-file side.

---

## Developing

Host setup (Python ≥ 3.12):

```sh
pip install -e .[dev]
pre-commit install        # installs pre-commit, commit-msg and pre-push hooks
```

| Task | Command |
|---|---|
| Lint + format | `ruff check .` / `ruff format .` (the only linter/formatter) |
| Fast tests (no DB) | `pytest tests/unit/` |
| Full local gate (pre-push) | `scripts/verify.sh` — ruff + unit tests + `pip-audit` |
| All host-runnable tests | `pytest tests/` (unit + sqlite-bound suites) |

The `src/upstage_backend/**/tests/` integration suites write through the live
app into the configured Postgres. They require `UPSTAGE_TESTS_ALLOW_REAL_DB=1`
(leftover fixtures are swept at teardown) and a reachable database — run them
inside a container on the compose network. Off-network they skip with an
explanatory message; without the opt-in they refuse to run at all. Note that
some of them depend on data created by earlier suites, so run the whole
`src/upstage_backend` tree, not single files. CI runs the full suite with
throwaway Postgres/Mosquitto services.

### Migrations

- Hand-written Alembic revisions; **no autogenerate**.
- Each module keeps its own chain under
  `src/upstage_backend/<module>/db_migrations/` (9 locations wired in
  `scripts/alembic.ini`), so the project intentionally has **multiple heads**
  — always upgrade with `alembic -c ./scripts/alembic.ini upgrade heads`
  (plural), which is exactly what the `upstage_db_migrate` container does.
- New revision:
  `alembic -c ./scripts/alembic.ini revision -m "..." --version-path=src/upstage_backend/<module>/db_migrations`
  (`create-migration.sh` is a commented-out cheatsheet of these commands, not
  a runnable tool).

### GraphQL

Single combined schema mounted at `/api/studio_graphql` (HTTP + WebSocket).
[API.md](API.md) documents the envelope and common operations. CORS is open
outside production; with `ENV_TYPE="Production"` it is locked to `HOSTNAME`.

---

## Repository map (selected)

| Path | Purpose |
|---|---|
| `src/upstage_backend/<module>/` | Feature modules (assets, stages, users, authentication, studio_management, performance_config, upstage_options, licenses, payments, mails) — each with `db_models/`, `db_migrations/`, `http/`, `services/`, `tests/` |
| `src/upstage_backend/event_archive/` | MQTT→Postgres archiver (replay source); tunables via `EVENT_ARCHIVE_*` env vars |
| `src/upstage_backend/upstage_stats/` | Live player/audience counters |
| `scripts/` | Service entrypoints, `verify.sh`, backup + poster-backfill utilities, dev tools |
| `migration_scripts/` | One-off data importers for legacy databases |
| `service_containers/`, `app_containers/` | The two compose tiers (see above) |
| `initial_scripts/` | Env templates, nginx template references, post-install scaffold |
| `installation/` | Legacy single-host installer — superseded by the compose flow above |

## Behaviour note

Admin/Super-admin roles gate the Studio admin panels only. **Player controls
on a live stage are granted per stage** — to the stage owner and to users on
the stage's player/editor access lists (Stage Management → General). An admin
who is neither joins as audience. This is intentional; see the frontend
README for details.

## License

GPL-3.0 (see [LICENSE](LICENSE)).
