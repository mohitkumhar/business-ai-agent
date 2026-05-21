from __future__ import annotations

import sys
from pathlib import Path

import bcrypt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth_passwords import SOCIAL_LOGIN_PASSWORD_HASH, is_bcrypt_hash, verify_password


def test_social_login_password_sentinel_is_not_bcrypt_hash():
    assert SOCIAL_LOGIN_PASSWORD_HASH == ""
    assert not is_bcrypt_hash(SOCIAL_LOGIN_PASSWORD_HASH)
    assert not verify_password("anything", SOCIAL_LOGIN_PASSWORD_HASH)


def test_malformed_password_hashes_fail_closed_without_bcrypt_error():
    assert not verify_password("secret", None)
    assert not verify_password("secret", "")
    assert not verify_password("secret", "no_pass")
    assert not verify_password("secret", "$2b$not-a-complete-hash")


def test_valid_bcrypt_hash_still_verifies_password():
    password_hash = bcrypt.hashpw(b"correct-password", bcrypt.gensalt()).decode("utf-8")

    assert is_bcrypt_hash(password_hash)
    assert verify_password("correct-password", password_hash)
    assert not verify_password("wrong-password", password_hash)
