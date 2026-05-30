# UpStage Backend

FastAPI GraphQL backend, Docker compose stacks, and the single-host installer for UpStage. **UpStage installs on a single Debian host via Docker — run the installer and it handles everything** (OS setup, TLS, secrets, Postgres, Mosquitto, backend workers, and the frontend build).

The frontend SPA lives in the sibling [`upstage_frontend`](../upstage_frontend/) repo.

## Quick start

Clone both repos as siblings on the target host, then run the installer:

```sh
git clone https://github.com/upstage-org/upstage_backend
git clone https://github.com/upstage-org/upstage_frontend

cd upstage_backend/installation
chmod +x install_single_host.sh phases/*.sh lib/*.sh
./install_single_host.sh --all
```

Set `UPSTAGE_BACKEND_DIR` and `UPSTAGE_FRONTEND_DIR` if your checkouts are not at the default sibling paths next to `installation/`.

Phase `20_collect_domains` writes `state.env` (see [`installation/state.env.example`](installation/state.env.example)) with:

| Variable | Purpose |
|----------|---------|
| `APP_DOMAIN` | Public app hostname (GraphQL + SPA) |
| `SVC_DOMAIN` | Service hostname (Postgres / MQTT) |
| `STREAMING_DOMAIN` | Jitsi / streaming hostname |
| `CERTBOT_EMAIL` | Let's Encrypt contact email |
| `UPSTAGE_COMPOSE_PROFILE` | `prod` or `dev` — selects which `run_docker_compose_*` scripts the installer uses |

For `--list`, `--phase`, and troubleshooting, see [`installation/README.md`](installation/README.md).

## Prerequisites

- Clean **Debian** host; run the installer as **root** (SSH keys recommended).
- DNS **A** records (and `auth.` for streaming) for app, service, and streaming hostnames pointing at this host's public IP.
- Cloudflare Turnstile keys (prompted interactively in phase `40_generate_secrets`).

## Pre-install configuration

Customize these **before** running `./install_single_host.sh --all`. The installer invokes the run scripts below; you do not run them as separate install steps.

### Service tier — `service_containers/`

Infrastructure stack: Postgres + Mosquitto. Edit the marked block at the top of [`service_containers/run_docker_compose_dev.sh`](service_containers/run_docker_compose_dev.sh) and [`run_docker_compose_prod.sh`](service_containers/run_docker_compose_prod.sh):

| Variable | Dev | Prod |
|----------|-----|------|
| `BASE_SITE` | your root domain | same |
| `SITE` | `dev` | `prod` |
| `SSL` | `mqtt-dev.<domain>` | empty (TLS via nginx) |
| `MOSQUITTO_EXPOSED_WS_PORT` | `9001` | `9002` |
| `HARDCODED_HOSTNAME` | `dev.<domain>` | `<domain>` |
| `PG_DATA_DIR` | `/postgres_data_dev` | `/postgres_data_prod` |
| `MQ_DATA_DIR` | `/mosquitto_files_dev` | `/mosquitto_files_prod` |

Starts `postgres_container_${SITE}` and `mosquitto_container_${SITE}` on Docker network `upstage-network-${SITE}`.

### App tier — `app_containers/`

Application stack: FastAPI, event archive, stats. Edit the top of [`app_containers/run_docker_compose_dev.sh`](app_containers/run_docker_compose_dev.sh) and [`run_docker_compose_prod.sh`](app_containers/run_docker_compose_prod.sh):

| Variable | Dev | Prod |
|----------|-----|------|
| `SITE` | `dev` | `prod` |
| `HARDCODED_HOSTNAME` | `dev.<domain>` | `<domain>` |
| `APP_PORT` | `9090` | `9091` |
| `APP_USER` / `APP_GROUP` | `1000` | `1000` |

Compose services ([`app_containers/docker-compose.yaml`](app_containers/docker-compose.yaml)):

| Service | Role |
|---------|------|
| `upstage_db_migrate` | One-shot Alembic `upgrade heads` |
| `upstage_backend` | FastAPI via [`scripts/start_upstage.sh`](scripts/start_upstage.sh) |
| `upstage_event_archive` | MQTT → Postgres event persistence |
| `upstage_stats` | Connection statistics |

Uploaded media is bind-mounted at `/app_code_<site>/uploads`.

### Backend secrets

Phase `40_generate_secrets` runs [`initial_scripts/environments/generate_environments_script.sh`](initial_scripts/environments/generate_environments_script.sh) and [`scripts/generate_cipher_key.sh`](scripts/generate_cipher_key.sh), producing:

- [`src/upstage_backend/global_config/load_env.py`](src/upstage_backend/global_config/load_env.py) (gitignored; from [`env_app_template.py`](initial_scripts/environments/env_app_template.py))
- [`container_scripts/mqtt_server/pw.txt`](container_scripts/mqtt_server/pw.txt)
- [`service_containers/run_docker_compose.sh`](service_containers/run_docker_compose.sh) (generated password exports)

Key variables in `load_env.py`: `HOSTNAME`, `DATABASE_*`, `MQTT_*`, `SECRET_KEY`, `CIPHER_KEY`, `CLOUDFLARE_CAPTCHA_SECRETKEY`, `STRIPE_*`, `ENV_TYPE`, JWT settings.

### Frontend env (sibling repo)

Before phase `90_frontend`, prepare `env_backup_dev` or `env_backup_prod` in [`upstage_frontend`](../upstage_frontend/) — see the [frontend README](../upstage_frontend/README.md).

## What the installer runs

| Phase | Does |
|-------|------|
| `10_os` | Docker, UFW base, logrotate |
| `20_collect_domains` | Writes `state.env` |
| `30_prepare_svc_app_layout` | Creates host data directories |
| `50_certificates` | nginx + certbot per hostname |
| `40_generate_secrets` | Backend secrets + cipher key |
| `45_sync_load_env` | Mosquitto files, app tree → `/app_code` |
| `80_streaming_jitsi` | Jitsi install (interactive) |
| `51_nginx_render_full` | Combined nginx site from templates |
| `60_compose_svc` | Service Docker stack (`service_containers/`) |
| `75_docker_firewall` | UFW + [`initial_scripts/setup-docker-ports.sh`](initial_scripts/setup-docker-ports.sh) |
| `70_compose_app` | App Docker stack (`app_containers/`) |
| `90_frontend` | Frontend env + `run_front_end_*.sh --build` |

If you omit streaming/Jitsi, skip phase `80_streaming_jitsi` and adjust DNS expectations accordingly.

## Further reading

- [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) — architecture, module map, event archive
- [`API.md`](API.md) — GraphQL examples
- [`installation/README.md`](installation/README.md) — installer phases, `--phase`, troubleshooting
- [`migration_scripts/`](migration_scripts/) — optional data migration
- [`initial_scripts/post_install/`](initial_scripts/post_install/) — demo scaffold, Jitsi cert cron

## Local protections (git hooks)

This repo uses [pre-commit](https://pre-commit.com/) to run a small
suite of local protections against the same checks that run in CI.
They exist so problems are caught at the developer's machine — before
they hit `main` — and so a `git push --no-verify` bypass is still
caught server-side by `.github/workflows/ci.yml`.

The frontend repo (`../upstage_frontend`) uses Husky for the same
purpose; the two configurations are deliberately symmetrical.

### One-time install

```sh
pip install -e .[dev]
pre-commit install --install-hooks
```

The `default_install_hook_types` line in `.pre-commit-config.yaml`
picks up `commit-msg` and `pre-push` automatically — no extra
`--hook-type` flags needed.

### What runs and when

| Hook         | What it does                                                                                                                                | Typical time |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| `pre-commit` | Standard hygiene (`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`/`-toml`, `detect-private-key`, `mixed-line-ending`) + `ruff --fix` + `ruff-format`, scoped to staged files. | < 5 s        |
| `commit-msg` | Light gate: rejects empty / `wip` / `fixup!` subjects shorter than 10 characters. Trailers like `Co-authored-by:` are intentionally ignored. | instant      |
| `pre-push`   | `scripts/verify.sh`: `ruff check .` + `ruff format --check .` + `pytest tests/unit/` + `pip-audit --strict`.                                 | ~10 s        |

The `pre-push` hook is byte-for-byte identical to `scripts/verify.sh`
and to the CI `verify` job, so a clean local push is a strong signal
that CI's verify build will pass.

The full pytest suite (which needs Postgres and Mosquitto) runs **only
in CI's `tests` job**, where the GitHub Actions `services:` block
brings up the dependencies. Locally, only `tests/unit/` is run on
push — that directory carries `tests/unit/conftest.py` no-op overrides
of the root conftest's autouse `client` and `db_engine` fixtures, so
it is actually runnable without the docker stack.

### Manual run

```sh
./scripts/verify.sh           # full pre-push gate (ruff + tests/unit + pip-audit)
ruff check . && ruff format --check .
pytest tests/unit/            # DB-free smoke
pip-audit --strict            # honours [tool.pip-audit] ignore-vulns
```

### Vulnerability allowlist

`pip-audit` exits non-zero on any finding — there is no severity
threshold. When upstream has no patched version available and the
team has explicitly accepted the risk, add the advisory ID to the
`[tool.pip-audit] ignore-vulns` list in `pyproject.toml` with a
trailing comment naming the reviewer and the date of acceptance:

```toml
[tool.pip-audit]
ignore-vulns = [
    "GHSA-xxxx-xxxx-xxxx",  # accepted 2026-05-27 by alice; no upstream fix
]
```

### Bypassing for emergencies

```sh
git commit --no-verify -m "hotfix: ..."
git push --no-verify
```

Use sparingly. CI still runs the full verify suite plus the full
pytest with services on the pushed branch and on the PR, so a bypass
only delays the failure — it does not hide it.

### Adding a new check

1. Add a one-liner to [scripts/verify.sh](scripts/verify.sh) so it can
   be run standalone.
2. Mirror it in [.github/workflows/ci.yml](.github/workflows/ci.yml)
   under the `verify` job so the local gate and the server-side gate
   stay in lockstep.
3. If the check is fast enough to run on every commit (not just every
   push), add it to [.pre-commit-config.yaml](.pre-commit-config.yaml)
   under the appropriate `repo:` block.
