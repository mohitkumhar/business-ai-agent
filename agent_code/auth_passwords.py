from __future__ import annotations

import bcrypt

SOCIAL_LOGIN_PASSWORD_HASH = ""
BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def is_bcrypt_hash(password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return password_hash.startswith(BCRYPT_PREFIXES)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not is_bcrypt_hash(password_hash):
        return False

    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False
