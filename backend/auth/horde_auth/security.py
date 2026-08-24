from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def normalize_nick(nick: str) -> str:
    nick = nick.strip()
    if not (3 <= len(nick) <= 32):
        raise ValueError("Ник должен быть от 3 до 32 символов.")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
    if any(ch not in allowed for ch in nick):
        raise ValueError("В нике можно использовать только латиницу, цифры и подчёркивание.")
    return nick


def hash_password(password: str) -> str:
    if len(password) < 6:
        raise ValueError("Пароль должен быть не короче 6 символов.")
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def new_public_token() -> str:
    return secrets.token_urlsafe(40)


def token_hash(token: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()

