#!/usr/bin/env sh
# Light commit-message gate. Mirrors
# ../upstage_frontend/.husky/commit-msg.
#
# We deliberately do NOT enforce Conventional Commits — repo history
# is informal and the team has not opted in. The intent of this hook
# is to stop accidental empty / "wip" / "fix" / "fixup!" commits from
# landing on shared branches. `git commit --no-verify` remains as the
# emergency escape hatch and CI still runs the rest of the verify
# suite server-side.
#
# Only the SUBJECT line (the first non-comment, non-blank line) is
# inspected. Body paragraphs and machine-generated trailers like
# `Co-authored-by:` and `Signed-off-by:` are intentionally ignored —
# we already debugged a case on the frontend where a Cursor-injected
# trailer smuggled a bare "fix" past the length gate.

set -e
msg_file="$1"

# First non-comment, non-blank line. That's the conventional "subject".
subject=$(grep -v '^#' "$msg_file" | grep -v '^[[:space:]]*$' | head -n 1)

# Trim leading/trailing whitespace for substantive checks but keep an
# all-whitespace subject still detectable as "empty" via the compact
# version below.
subject_trimmed=$(printf '%s' "$subject" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
subject_compact=$(printf '%s' "$subject_trimmed" | tr -d '[:space:]')

case "$subject_compact" in
  '' | wip | WIP* | fixup* | squash*)
    echo "[commit-msg] subject looks empty / WIP / fixup. Use a real subject line, or pass --no-verify for an explicit emergency bypass."
    exit 1
    ;;
esac

if [ "${#subject_compact}" -lt 10 ]; then
  echo "[commit-msg] subject must be at least 10 non-whitespace characters (got ${#subject_compact}: \"$subject_trimmed\")."
  exit 1
fi
