"""Token bertanda tangan untuk tautan dashboard pribadi (/progres).

Bot Telegram membuat token dari ID Telegram, lalu halaman web memeriksanya.
Tidak perlu login: tautan hanya berlaku sementara dan tidak bisa dipalsukan
tanpa SECRET_KEY.
"""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SALT = "currycoach-progres"
MASA_BERLAKU_DETIK = 24 * 60 * 60


def buat_token(secret_key: str, telegram_id: int) -> str:
    """Buat token yang memuat ID Telegram dan ditandatangani dengan secret_key."""
    return URLSafeTimedSerializer(secret_key, salt=SALT).dumps({"tid": int(telegram_id)})


def baca_token(secret_key: str, token: str, max_age: int = MASA_BERLAKU_DETIK) -> int | None:
    """Kembalikan ID Telegram jika token sah dan belum kedaluwarsa, selain itu None."""
    try:
        data = URLSafeTimedSerializer(secret_key, salt=SALT).loads(token, max_age=max_age)
        return int(data["tid"])
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None
