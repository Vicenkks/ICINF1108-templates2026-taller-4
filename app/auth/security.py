import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Final
from uuid import UUID, uuid4

import jwt

from app.shared.config import PASSWORD_RESET_SECRET, PASSWORD_RESET_TTL_MINUTES
from app.shared.datetimes import utc_now

KEY_LENGTH = 64

# Mismos parámetros que `crypto.scrypt` de Node (rama NestJS).
SCRYPT_PARAMS = {"n": 16384, "r": 8, "p": 1}

ALGORITHM: Final[str] = "HS256"
PURPOSE: Final[str] = "password_reset"


# Formato guardado: "scrypt$<sal en hex>$<hash en hex>".
# La sal aleatoria hace que dos contraseñas iguales tengan hashes distintos.
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(
        password.encode(), salt=salt, dklen=KEY_LENGTH, **SCRYPT_PARAMS
    )

    return f"scrypt${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")

    if len(parts) != 3 or parts[0] != "scrypt":
        return False

    salt = bytes.fromhex(parts[1])
    expected = bytes.fromhex(parts[2])
    actual = hashlib.scrypt(
        password.encode(), salt=salt, dklen=len(expected), **SCRYPT_PARAMS
    )

    # Comparación en tiempo constante para no filtrar información por timing.
    return hmac.compare_digest(actual, expected)


def create_reset_token(user_id: UUID) -> tuple[str, str]:
    """Genera el JWT de recuperación y su identificador único (`jti`)."""
    jti = uuid4().hex
    now = utc_now()
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "purpose": PURPOSE,
        "iat": now,
        "exp": now + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
    }

    token = jwt.encode(payload, PASSWORD_RESET_SECRET, algorithm=ALGORITHM)
    return token, jti


def decode_reset_token(token: str) -> tuple[UUID, str] | None:
    """Valida firma, expiración y propósito. Devuelve `None` si no sirve."""
    try:
        payload = jwt.decode(
            token,
            PASSWORD_RESET_SECRET,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "jti"]},
        )

        subject = payload["sub"]
        jti = payload["jti"]

        if payload.get("purpose") != PURPOSE:
            return None
        if not isinstance(subject, str) or not isinstance(jti, str) or not jti:
            return None

        return UUID(subject), jti
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
