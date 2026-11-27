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
| App tier | `app_containers/` | `upstage_db_migrate` (one-shot: `alembic upgrade head`, then `scripts/run_bootstrap.py`), `upstage_backend` (API), `upstage_event_archive`, `upstage_stats` |

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

Prerequisites: Docker with the compose plugin. The app image is built from
`python:3.14-slim-trixie` (`app_containers/docker-compose.yaml`); Python
≥ 3.12 on the host is only needed for host-side development, not to run the
stack. The service tier runs `postgres:latest`. The baseline schema
(`alembic/versions/baseline001_schema.sql`) was dumped from PostgreSQL 18 and
sets `transaction_timeout`, so it needs PostgreSQL 17 or newer.

### 1. Configuration files

**a) `src/upstage_backend/global_config/load_env.py`** — the real runtime
configuration on a deployed host. It is gitignored. Settings are resolved
once at import by the pydantic-settings `Settings` class in
`global_config/app_settings.py`; `global_config/env.py` re-exports every
field as a module-level constant, which is what the rest of the code
imports. Precedence, highest first:

1. names defined in `load_env.py`;
2. the process environment (a `.env` file is loaded into it with
   python-dotenv by `env.py`);
3. the defaults declared in `Settings`.

Values are validated: a malformed value (for example a non-numeric
`EMAIL_PORT`) fails at startup. `SUPPORT_EMAILS` is a comma-separated list
when given through the environment. Names in `load_env.py` that are not
`Settings` fields are still exported from `global_config.env` unchanged.

Sample, with secrets X'd out:

```python
# Used as an identifier. In load_env.py this name sets it; from the
# environment only HARDCODED_HOSTNAME does (the HOSTNAME environment variable
# is not read). Unset, it is the machine name with "." and "-" replaced by "_".
HOSTNAME="dev.example.org"

DATABASE_CONNECT = "postgresql"
DATABASE_HOST = "postgres_container_dev"   # container name on the shared network
DATABASE_PORT = 5432
DATABASE_USER = "postgres"
DATABASE_PASSWORD = "XXXXXXXXXXXX"
DATABASE_NAME = "upstage"

EMAIL_USE_TLS = False  # True: the backend issues STARTTLS itself on ports other than 465 (465 is always implicit TLS)
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
MQTT_PASSWORD = "XXXXXXXXXXXXX"            # must match pw.backup; served to browsers on GraphQL `Stage.mqtt`

CLOUDFLARE_CAPTCHA_SECRETKEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
SECRET_KEY = "XXXX"   # JWT signing key: openssl rand -hex 48

CLIENT_MAX_BODY_SIZE = 500 * 1024 * 1024

UPLOAD_USER_CONTENT_FOLDER = "/usr/app/uploads"   # mounted this way in docker-compose
DEMO_MEDIA_FOLDER = "/usr/app/dashboard/demo"

# Payment — only for instances that sell subscriptions; leave empty otherwise.
STRIPE_KEY = ""
STRIPE_PRODUCT_ID = ""

# Change to "Production" for official releases (CORS then allows only UPSTAGE_FRONTEND_URL and https sub-domains of DOMAIN; see main.py add_cors_middleware).
ENV_TYPE = "Dev"

JWT_ADMIN_TOKEN_DAYS = 30  # login lifetime for admins and super admins, in days (default 30)
JWT_USER_TOKEN_DAYS = 2    # login lifetime for every other role, in days (default 2)

# RTMP streaming (optional, needs an external MediaMTX server): shared secret
# for signing publish tokens. Generate with: openssl rand -hex 24
# One key serves ALL MediaMTX hosts (multi-server streaming): the token is
# server-agnostic and every MediaMTX validates publishes against this backend's
# POST /api/rtmp/auth (remote hosts via the public nginx alias on the backend
# host, see /root/streaming2/nginx-rtmp-auth-public.conf).
STREAM_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
```

Notes:
- `DATABASE_HOST`/`MQTT_BROKER` are the *container names*; the app tier
  reaches them over the shared docker network on their internal ports
  (5432/1883). Do not use the old proxied ports (5433/1884) from
  `initial_scripts/environments/env_app_template.py` — that template predates
  the compose flow.
- `MONGO_*`, `CIPHER_KEY`, `MQTT_PORT`, `ACCEPT_EMAIL_HOST`,
  `ACCEPT_SERVER_SEND_EMAIL_EXTERNAL` and `SEND_EMAIL_SERVER`, found in older
  configs, are not read by any code in this repository.
- The browser's MQTT login is not a frontend build variable: the frontend
  reads it at runtime from the GraphQL field `Stage.mqtt`, which returns
  `MQTT_USER` / `MQTT_PASSWORD`.
- With `ENV_TYPE` set to `"Dev"` or `"Production"` the backend refuses to
  start without a `SECRET_KEY`. With any other `ENV_TYPE` a random
  per-process key is generated instead.

**b) Postgres password** — the service-tier script reads it from the
environment of the shell that runs it (it does not read a file):

```sh
export POSTGRES_PASSWORD_DEV=XXXXXXXXXXXX
```

(Use `POSTGRES_PASSWORD_PROD` for a prod site. Must match
`DATABASE_PASSWORD` in `load_env.py`.)

**c) Mosquitto passwords** — the service-tier script seeds
`/mosquitto_files_<site>/etc/mosquitto/` from
`service_containers/deployment_config/etc_mosquitto/` on first run (setting
the ACL namespace in `acl.txt` to `<site>`), runs `certbot` for the site
hostname and exits, asking you to edit `pw.backup`. Run it again afterwards;
it refuses to start while the defaults say `changeme`:

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
Postgres + Mosquitto. Site-specific settings (hostname, exposed WS port) are
variables at the top of the script. The prod script also enables the
`db_backup` container (`COMPOSE_PROFILES=backup`).

### 3. Bring up the app tier

```sh
cd app_containers
./run_docker_compose_dev.sh      # or run_docker_compose_prod.sh
```

This builds the image (sources baked in, dependencies from `uv.lock`),
creates `/app_code_<site>/uploads`, runs the one-shot migration container
(`alembic upgrade head` — creates the entire schema from empty — followed by
`scripts/run_bootstrap.py`), then starts the API and the two workers. The
container publishes the API on host port `9090` (dev) / `9091` (prod).

`run_bootstrap.py` makes sure the `admin` account and the deleted-media
placeholder asset exist on every run, and seeds the Demo Stage only when the
database has no stages at all (a new installation).

### 4. First login

Migrations seed a default super admin: **username `admin`, password
`Secret@123`** (`alembic/versions/baseline001_consolidated_schema_and_seeds.py`).
**Log in and change this password immediately.**

Passwords are stored as argon2 hashes. Installs upgrading from the old
Fernet scheme must convert existing rows once with
`migration_scripts/fernet_to_argon2.py` (pass the retired `CIPHER_KEY`
via `--key`) before deploying this version.

The demo scaffold (the "Demo Stage" plus demo media) can also be loaded by
hand into a running backend container:

```sh
./initial_scripts/post_install/scaffold_base_media.sh
```

### 5. Front it with nginx

See the TLS section above and the frontend README for the static-file side.

---

## Developing

Host setup (Python ≥ 3.12):

```sh
uv sync --frozen --extra dev   # exact versions from uv.lock, into .venv (what CI does)
# or, without uv (resolves the latest versions instead): pip install -e .[dev]
pre-commit install        # installs pre-commit, commit-msg and pre-push hooks
```

| Task | Command |
|---|---|
| Lint + format | `ruff check .` / `ruff format .` (the only linter/formatter). Rules selected in `pyproject.toml`: `E`, `F`, `B`, `DTZ`, `RUF006`, `ASYNC` (`E501` ignored). The pre-commit ruff hook is pinned to `v0.16.9`. |
| Fast tests (no DB) | `pytest tests/unit/` |
| Full local gate (pre-push) | `scripts/verify.sh` — ruff + unit tests + `pip-audit` |
| All host-runnable tests | `pytest tests/` (unit + sqlite-bound suites) |

A plain `pytest` collects `src/upstage_backend` and `tests` (`testpaths` in
`pytest.ini`). `ruff format --check` is not part of `scripts/verify.sh`.

The `src/upstage_backend/**/tests/` integration suites write through the live
app into the configured Postgres. They require `UPSTAGE_TESTS_ALLOW_REAL_DB=1`
(leftover fixtures are swept at teardown) and a reachable database — run them
inside a container on the compose network. Off-network they skip with an
explanatory message; without the opt-in they refuse to run at all. Note that
some of them depend on data created by earlier suites, so run the whole
`src/upstage_backend` tree, not single files. CI
(`.github/workflows/ci.yml`) runs on Python 3.14: a `verify` job
(`scripts/verify.sh`) and a `tests` job that applies the migrations and runs
the full suite against throwaway `postgres:latest` and
`eclipse-mosquitto:latest` services.

The suite needs no Stripe, SMTP or stream secrets: the payment tests stub the
Stripe calls, the system-email test stubs SMTP, and the `rtmp_auth` tests set
their own `STREAM_KEY` when none is configured.

### Migrations

- Hand-written Alembic revisions; **no autogenerate**.
- One consolidated chain with a **single head**: all revisions live in
  `alembic/versions/`, wired by the repo-root `alembic.ini`. Upgrade with
  `alembic -c ./alembic.ini upgrade head`, which is exactly what the
  `upstage_db_migrate` container does.
- New revision: `alembic -c ./alembic.ini revision -m "..."`.
- Current chain, oldest first:

  | Revision | File | What it does |
  |---|---|---|
  | `baseline001` | `baseline001_consolidated_schema_and_seeds.py` (+ `baseline001_schema.sql`) | Full schema and install seeds |
  | `c3d5e7f9a1b2` | `c3d5e7f9a1b2_upload_limit_null_to_default.py` | Backfills NULL `upstage_user.upload_limit` to the 1 MiB default and adds a server default |
  | `a7c1e2d4f6b8` | `a7c1e2d4f6b8_foreign_key_indexes.py` | Indexes on foreign keys and lookup columns |
  | `b9d2f4a6c8e0` | `b9d2f4a6c8e0_timestamps_with_time_zone.py` | Converts the 21 remaining `timestamp without time zone` columns to `timestamp with time zone` |

- `b9d2f4a6c8e0` operational notes (from its docstring): existing values are
  converted as UTC. Each `ALTER` holds an `ACCESS EXCLUSIVE` lock while the
  indexes on the converted column are rebuilt, so run it while no performance
  is live (`events`, `connection_stats` and `receive_stats` are the tables
  that grow). It sets a 10 s `lock_timeout`, so it fails rather than queueing
  behind a long transaction, and can simply be re-run.
- History note (2026-07): the previous 41 revisions (9 per-module
  `db_migrations/` dirs, two heads) were squashed into
  `baseline001_consolidated_schema_and_seeds.py`, which creates the full
  schema and the install seeds (default admin, asset types, system config).
  Databases created before the consolidation cannot upgrade through the
  removed revisions — restore from a dump taken at/after the consolidation
  instead (existing dev/prod DBs were stamped/replaced accordingly).

### GraphQL

Single combined schema mounted at `/api/studio_graphql`, HTTP only: the
schema has no `Subscription` type and there is no GraphQL WebSocket route.
[API.md](API.md) lists the operations. CORS allows any origin unless
`ENV_TYPE="Production"`, where it allows `UPSTAGE_FRONTEND_URL` and https
sub-domains of `DOMAIN` (`add_cors_middleware` in `main.py`).

The only other HTTP route is `POST /api/rtmp/auth`
(`src/upstage_backend/assets/http/rtmp_auth.py`), the publish-authentication
hook called by MediaMTX.

---

## Repository map (selected)

| Path | Purpose |
|---|---|
| `src/upstage_backend/<module>/` | Feature modules (assets, stages, users, authentication, studio_management, performance_config, upstage_options, licenses, payments, mails, files) — most with `db_models/`, `http/`, `services/`, `tests/` (migrations live centrally in `alembic/versions/`) |
| `src/upstage_backend/global_config/` | Settings (`app_settings.py`, `env.py`), DB engine and sessions, shared base model, helpers, `@authenticated` decorator |
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
