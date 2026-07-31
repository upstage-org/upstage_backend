"""Argon2 password hashing.

Replaces the old reversible Fernet encryption (fernet_crypto.py). An argon2
hash embeds its own salt and parameters, so verification re-derives the hash
from the entered password and compares — there is no decryption and no
CIPHER_KEY to manage. Installs upgrading from the Fernet scheme must convert
stored ciphertexts once with migration_scripts/fernet_to_argon2.py before
deploying this code (old hashes are unreadable to it and vice versa).
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(stored_hash: str, plain: str) -> bool:
    try:
        return _hasher.verify(stored_hash, plain)
    except (VerificationError, InvalidHashError):
        # Wrong password, or a stored value that isn't an argon2 hash
        # (e.g. an unmigrated legacy Fernet ciphertext).
        return False
