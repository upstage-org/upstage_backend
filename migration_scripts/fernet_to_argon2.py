"""One-time migration: convert stored Fernet-encrypted passwords to argon2 hashes.

Run this ONCE per install, BEFORE deploying the code that removed Fernet
(global_config/helpers/password.py replaced fernet_crypto.py). The old code
cannot read argon2 hashes and the new code cannot read Fernet ciphertexts,
so migrate and deploy together.

The Fernet key is passed in explicitly (it no longer exists in load_env):

    uv run python migration_scripts/fernet_to_argon2.py --key 'T0Nk...='
    # or: CIPHER_KEY='T0Nk...=' uv run python migration_scripts/fernet_to_argon2.py

Idempotent: rows already holding an argon2 hash ($argon2 prefix) are skipped,
and rows the key cannot decrypt are left untouched and reported.
"""

import argparse
import os
import sys

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import create_engine, text

from upstage_backend.global_config.env import (
    DATABASE_HOST,
    DATABASE_NAME,
    DATABASE_PASSWORD,
    DATABASE_PORT,
    DATABASE_USER,
)
from upstage_backend.global_config.helpers.password import hash_password


def migrate(key: str, dry_run: bool = False, database_url: str | None = None) -> int:
    cipher = Fernet(key.encode() if isinstance(key, str) else key)
    engine = create_engine(
        database_url
        or f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}"
        f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    )

    converted, skipped, failed = 0, 0, []
    with engine.connect() as conn:
        with conn.begin():
            rows = conn.execute(text("SELECT id, username, password FROM upstage_user")).fetchall()
            for row in rows:
                stored = row.password or ""
                if stored.startswith("$argon2"):
                    skipped += 1
                    continue
                try:
                    plain = cipher.decrypt(stored.encode()).decode()
                except (InvalidToken, ValueError):
                    failed.append((row.id, row.username))
                    continue
                if not dry_run:
                    conn.execute(
                        text("UPDATE upstage_user SET password = :p WHERE id = :id"),
                        {"p": hash_password(plain), "id": row.id},
                    )
                converted += 1

    print(f"converted: {converted}, already argon2 (skipped): {skipped}, failed: {len(failed)}")
    for user_id, username in failed:
        print(f"  could not decrypt user id={user_id} username={username!r} — left untouched")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", default=os.getenv("CIPHER_KEY"), help="the old Fernet CIPHER_KEY")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument(
        "--database-url",
        help="override the postgresql:// URL (e.g. when the configured "
        "DATABASE_HOST is a container name that doesn't resolve here)",
    )
    args = parser.parse_args()
    if not args.key:
        sys.exit("Provide the old Fernet key via --key or the CIPHER_KEY env var.")
    sys.exit(migrate(args.key, dry_run=args.dry_run, database_url=args.database_url))
