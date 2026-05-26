# Single-host installation (UpStage)

Scripts in this directory orchestrate a **clean Debian install** of UpStage when **app, service (DB/MQTT), and streaming (Jitsi)** all run on **one machine**. They **do not modify** existing files under `upstage_backend` or `upstage_frontend` in the repo beyond what the upstream generators already write (for example `service_containers/run_docker_compose.sh` from `generate_environments_script.sh`).

## Prerequisites

- Three DNS **A** records (and `auth.` for streaming) pointing at this host’s public IP, as described in the main `upstage_backend` README.
- A **Let’s Encrypt** contact email.
- Cloudflare Turnstile keys (prompted during backend env generation).
- Run as **root** on the target server (SSH keys recommended).

## Layout

- `install_single_host.sh` — run all phases or one phase.
- `phases/` — numbered steps (OS, domains, TLS, secrets, files, Jitsi, nginx, Docker, frontend).
- `lib/` — shared helpers (`common.sh`, `render_nginx.sh`, `run_service_compose.sh`).
- `state.env` — created by phase `20_collect_domains` (copy from `state.env.example`). Gitignored.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `UPSTAGE_BACKEND_DIR` | Path to `upstage_backend` (default: `../prod_copy/upstage_backend` relative to this `installation/` folder when that path exists). |
| `UPSTAGE_FRONTEND_DIR` | Path to `upstage_frontend` (default: `../prod_copy/upstage_frontend`). |
| `UPSTAGE_OVERWRITE_STATE=1` | Force phase 20 to re-prompt even if `state.env` exists. |
| `UPSTAGE_AUTO_UFW_LOOPBACK=1` | Attempt to inject loopback rules into `/etc/ufw/before.rules` (optional; manual edit is safer). |

## Password and run-script flow (same as multi-machine)

1. `initial_scripts/environments/generate_environments_script.sh` generates secrets and fills:
   - `src/global_config/load_env.py`
   - `container_scripts/mqtt_server/pw.txt`
   - `service_containers/run_docker_compose.sh` (exports for Postgres)
2. `scripts/generate_cipher_key.sh` updates the cipher entry in `load_env.py`.
3. Service Docker is started with **`installation/lib/run_service_compose.sh`**, which reads those `export` lines from the generated `run_docker_compose.sh` and runs `docker compose` with **`docker-compose-services-prod.yaml`** (or `-dev`) so prod-style compose filenames work without hand-editing passwords.

## Usage

From the machine where the repo lives (adjust paths if you clone only `upstage_backend`):

```sh
cd /path/to/debug_this/installation
chmod +x install_single_host.sh phases/*.sh lib/*.sh
./install_single_host.sh --all
```

List phases:

```sh
./install_single_host.sh --list
```

Run a single step (after preparing earlier steps), for example:

```sh
./install_single_host.sh --phase 60_compose_svc
```

### Phase order (`--all`)

1. `10_os` — `initial_scripts/setup-os.sh` (Docker, UFW base, logrotate).
2. `20_collect_domains` — writes `state.env` (app / svc / streaming hostnames, LE email, `prod` or `dev`).
3. `30_prepare_svc_app_layout` — creates `/postgresql_data`, `/mosquitto_files`, `/app_code` dirs.
4. `50_certificates` — nginx + certbot; obtains **separate** certificates per hostname (paths match the nginx templates).
5. `40_generate_secrets` — `generate_environments_script.sh` + `generate_cipher_key.sh` (interactive).
6. `45_sync_load_env` — mosquitto files, copy app tree to `/app_code`, `sed` on `load_env.py` for `{APP_HOST}` (no SCP).
7. `80_streaming_jitsi` — Jitsi repo, JDK 17, Prosody cert copies, **interactive** `apt-get install jitsi-meet` (own certificate paths from Let’s Encrypt).
8. `51_nginx_render_full` — builds **one** combined site from the three nginx templates (`lib/render_nginx.sh`), fixes `:80` catch-all conflicts by using explicit `server_name`s.
9. `60_compose_svc` — creates `upstage-network` if needed; starts service stack with generated passwords.
10. `75_docker_firewall` — documents or applies UFW loopback guidance; runs `initial_scripts/setup-docker-ports.sh`.
11. `70_compose_app` — `run_docker_compose_prod.sh` or `_dev.sh`.
12. `90_frontend` — frontend `generate_environments_script.sh` + `run_front_end_prod.sh` / `_dev.sh`.

If you omit streaming/Jitsi, skip phases `80_streaming_jitsi` and adjust DNS/README expectations; you will need a different nginx merge (not covered by the default `--all`).

## Other docs

- Same-host Docker ↔ DB firewall: `upstage_backend/docker-firewall-config.md`.
- Data migration (optional): `upstage_backend/migration_scripts/`.
- Default admin user and demo scaffold: main backend README and `initial_scripts/post_install/`.

## Troubleshooting

- **`upstage-network` missing** — phase 60 creates it before `docker compose up`.
- **Certbot fails** — wait for DNS propagation; confirm port 80 reaches this host.
- **Nginx `nginx -t` fails after phase 51** — ensure Jitsi is installed (phase 80) so `/usr/share/jitsi-meet` exists.
- **`run_docker_compose_prod.sh` still shows `HARDCODED_HOSTNAME=upstage.live`** — that comes from the existing script in the repo; change only if your deployment requires it (outside this directory).

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
