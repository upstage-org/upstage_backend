#!/usr/bin/env sh
# Local pre-push gate AND the CI `verify` job, byte-for-byte the same
# script. If a step is added here, mirror it in
# `.github/workflows/ci.yml` so server-side enforcement keeps catching
# `--no-verify` bypasses.
#
# Order is cheapest-first so failures fail fast:
#   1. ruff lint      (~seconds, autofixable findings already corrected
#                      by the pre-commit ruff hook on the way in; a
#                      finding here means somebody bypassed pre-commit).
#   2. pytest tests/unit/ (DB-free smoke; full pytest runs in CI's
#                          `tests` job which spins up Postgres + MQTT).
#   3. pip-audit       (HTTPS; usually <2s. Reads
#                       `[tool.pip-audit] ignore-vulns` from
#                       pyproject.toml so per-advisory accept-list
#                       entries are honoured automatically.)
#
# Note: we deliberately do NOT run `ruff format --check .` here. The
# legacy tree has 63 files that pre-date this formatter config; the
# `ruff-format` hook in `.pre-commit-config.yaml` formats anything that
# gets staged from now on, while old files stay untouched until they
# get edited. Once the backlog is drained, add `ruff format --check .`
# back here and to the CI verify job in lockstep.
#
# `set -e` aborts on the first failure.
set -e

ruff check .
pytest tests/unit/ -p no:cacheprovider
# `--skip-editable` excludes our own `upstage-backend` (0.0.0) editable
# install, which isn't on PyPI. We deliberately do NOT pass `--strict`
# alongside `--skip-editable` because `--strict` elevates the skipped-
# editable line to an error; without it, pip-audit still exits non-zero
# on any actual vulnerability finding (which is what we want), and the
# editable skip becomes purely informational.
pip-audit --skip-editable
