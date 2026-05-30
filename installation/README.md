# Single-host installation (UpStage)

See the [main README](../README.md) for pre-install configuration (service/app run scripts, secrets, frontend env) and architecture overview.

Scripts in this directory orchestrate a **clean Debian install** of UpStage when **app, service (DB/MQTT), and streaming (Jitsi)** all run on **one machine**. They **do not modify** existing files under `upstage_backend` or `upstage_frontend` in the repo beyond what the upstream generators already write (for example `service_containers/run_docker_compose.sh` from `generate_environments_script.sh`).

## Prerequisites

- Three DNS **A** records (and `auth.` for streaming) pointing at this host's public IP, as described in the [main README](../README.md).
- A **Let's Encrypt** contact email.
- Cloudflare Turnstile keys (prompted during phase `40_generate_secrets`).
- Run as **root** on the target server (SSH keys recommended).

## Layout

- `install_single_host.sh` — run all phases or one phase.
- `phases/` — numbered steps (OS, domains, TLS, secrets, files, Jitsi, nginx, Docker, frontend).
- `lib/` — shared helpers (`common.sh`, `render_nginx.sh`, `run_service_compose.sh`).
- `state.env` — created by phase `20_collect_domains` (copy from `state.env.example`). Gitignored.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `UPSTAGE_BACKEND_DIR` | Path to `upstage_backend` checkout. |
| `UPSTAGE_FRONTEND_DIR` | Path to `upstage_frontend` checkout. |
| `UPSTAGE_OVERWRITE_STATE=1` | Force phase 20 to re-prompt even if `state.env` exists. |
| `UPSTAGE_AUTO_UFW_LOOPBACK=1` | Attempt to inject loopback rules into `/etc/ufw/before.rules` (optional; manual edit is safer). |

## Secrets flow

Phase `40_generate_secrets` runs `initial_scripts/environments/generate_environments_script.sh` and `scripts/generate_cipher_key.sh`, which produce:

- `src/upstage_backend/global_config/load_env.py`
- `container_scripts/mqtt_server/pw.txt`
- `service_containers/run_docker_compose.sh` (Postgres password exports)

Later phases consume these automatically — phase `60_compose_svc` starts the service stack and phase `70_compose_app` starts the app stack using the generated credentials. No separate password export step is required.

## Usage

From the machine where the repo lives:

```sh
cd /path/to/upstage_backend/installation
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
6. `45_sync_load_env` — mosquitto files, copy app tree to `/app_code`, `sed` on `load_env.py` for `{APP_HOST}`.
7. `80_streaming_jitsi` — Jitsi repo, JDK 17, Prosody cert copies, **interactive** `apt-get install jitsi-meet` (own certificate paths from Let's Encrypt).
8. `51_nginx_render_full` — builds **one** combined site from the three nginx templates (`lib/render_nginx.sh`), fixes `:80` catch-all conflicts by using explicit `server_name`s.
9. `60_compose_svc` — creates `upstage-network` if needed; starts service stack with generated passwords.
10. `75_docker_firewall` — UFW guidance; runs [`initial_scripts/setup-docker-ports.sh`](../initial_scripts/setup-docker-ports.sh).
11. `70_compose_app` — `run_docker_compose_prod.sh` or `_dev.sh`.
12. `90_frontend` — frontend env + `run_front_end_prod.sh` / `_dev.sh` (default `--build`).

If you omit streaming/Jitsi, skip phases `80_streaming_jitsi` and adjust DNS/README expectations; you will need a different nginx merge (not covered by the default `--all`).

## Other docs

- Data migration (optional): [`migration_scripts/`](../migration_scripts/).
- Default admin user and demo scaffold: [main README](../README.md) and [`initial_scripts/post_install/`](../initial_scripts/post_install/).

## Troubleshooting

- **`upstage-network` missing** — phase 60 creates it before `docker compose up`.
- **Certbot fails** — wait for DNS propagation; confirm port 80 reaches this host.
- **Nginx `nginx -t` fails after phase 51** — ensure Jitsi is installed (phase 80) so `/usr/share/jitsi-meet` exists.
- **`run_docker_compose_prod.sh` still shows `HARDCODED_HOSTNAME=upstage.live`** — edit the top of [`app_containers/run_docker_compose_prod.sh`](../app_containers/run_docker_compose_prod.sh) if your domain differs.
