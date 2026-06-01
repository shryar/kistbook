from __future__ import annotations

from cryptography.fernet import Fernet
from jose import jwt

from kistbook.core.config import settings

ALGORITHM = "HS256"

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.CREDENTIALS_ENC_KEY.encode())
    return _fernet


def create_access_token(data: dict) -> str:
    return jwt.encode(data.copy(), settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def encrypt_credentials(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_credentials(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
