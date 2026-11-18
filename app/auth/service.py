import secrets
from datetime import timedelta
from typing import Annotated, Final
from urllib.parse import urlencode
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.auth.models import PasswordResetTokenModel, UserSessionModel
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    ForgotPasswordDto,
    LoginDto,
    RegisterDto,
    ResetPasswordDto,
    User,
)
from app.auth.security import (
    create_reset_token,
    decode_reset_token,
    hash_password,
    verify_password,
)
from app.shared.config import SESSION_MAX_AGE_SECONDS
from app.shared.database import DbSession
from app.shared.datetimes import utc_now
from app.shared.exceptions import conflict
from app.users.models import UserModel
from app.users.repository import UsersRepository

UNAUTHORIZED_MESSAGE: Final[str] = "Debes iniciar sesión para acceder a este recurso"
INVALID_RESET_TOKEN_MESSAGE: Final[str] = (
    "El enlace de recuperación no es válido o expiró"
)
RESET_PAGE_PATH: Final[str] = "/reset-password.html"


class AuthService:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.users = UsersRepository(db)
        self.auth = AuthRepository(db)

    # --- Cuenta -----------------------------------------------------------

    def register(self, data: RegisterDto) -> User:
        if self.users.find_by_email(data.email) is not None:
            raise conflict(
                {"email": {"message": "El correo electrónico ya está registrado"}}
            )

        user = self.users.add(
            UserModel(
                name=data.name,
                email=data.email,
                passwordHash=hash_password(data.password),
            )
        )
        self.db.commit()

        return User.model_validate(user)

    def login(self, data: LoginDto) -> User:
        user = self.users.find_by_email(data.email)

        # Mismo mensaje si el correo no existe o la contraseña es incorrecta,
        # para no revelar qué correos están registrados.
        if user is None or not verify_password(data.password, user.passwordHash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos",
            )

        return User.model_validate(user)

    def find_user(self, user_id: UUID) -> User | None:
        user = self.users.find_by_id(user_id)
        return User.model_validate(user) if user is not None else None

    # --- Sesiones ---------------------------------------------------------

    def start_session(self, user_id: UUID, previous_id: str | None) -> str:
        # Siempre se crea un id de sesión nuevo para evitar ataques de fijación
        # de sesión. La sesión anterior (si había) y las expiradas se eliminan.
        if previous_id:
            self.auth.delete_session(previous_id)

        now = utc_now()
        self.auth.delete_expired_sessions(now)

        session_id = secrets.token_urlsafe(32)
        self.auth.add_session(
            UserSessionModel(
                id=session_id,
                userId=user_id,
                expiresAt=now + timedelta(seconds=SESSION_MAX_AGE_SECONDS),
            )
        )
        self.db.commit()

        return session_id

    def destroy_session(self, session_id: str | None) -> None:
        if session_id:
            self.auth.delete_session(session_id)
            self.db.commit()

    def require_session(self, session_id: str | None) -> UserSessionModel:
        # Deja pasar la petición solo si la cookie apunta a una sesión vigente.
        session = (
            self.auth.find_active_session(session_id, utc_now()) if session_id else None
        )

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=UNAUTHORIZED_MESSAGE,
            )

        return session

    # --- Recuperación de contraseña --------------------------------------

    def forgot_password(self, data: ForgotPasswordDto, base_url: str) -> str | None:
        user = self.users.find_by_email(data.email)

        # Respuesta genérica: no se revela si el correo está registrado.
        if user is None:
            return None

        # Solo se mantiene un enlace pendiente por usuario: al pedir uno nuevo,
        # el anterior deja de servir.
        self.auth.delete_password_reset_tokens_for_user(user.id)

        token, jti = create_reset_token(user.id)
        self.auth.add_password_reset_token(
            PasswordResetTokenModel(jti=jti, userId=user.id)
        )
        self.db.commit()

        return self.build_reset_link(base_url, token)

    def build_reset_link(self, base_url: str, token: str) -> str:
        # En producción el enlace se enviaría por correo y no se devolvería.
        query = urlencode({"token": token})
        return f"{base_url.rstrip('/')}{RESET_PAGE_PATH}?{query}"

    def reset_password(self, data: ResetPasswordDto) -> None:
        decoded = decode_reset_token(data.reset_token)

        if decoded is None:
            raise _invalid_reset_token()

        user_id, jti = decoded
        reset_token = self.auth.find_password_reset_token(jti)

        if (
            reset_token is None
            or reset_token.usedAt is not None
            or reset_token.userId != user_id
        ):
            raise _invalid_reset_token()

        user = self.users.find_by_id(user_id)

        if user is None:
            raise _invalid_reset_token()

        # Todo se confirma junto: si algo falla, no queda ni la contraseña
        # nueva ni el token marcado como usado.
        user.passwordHash = hash_password(data.new_password)
        reset_token.usedAt = utc_now()
        self.auth.delete_user_sessions(user.id)
        self.db.commit()


def _invalid_reset_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_RESET_TOKEN_MESSAGE
    )


AuthServiceDep = Annotated[AuthService, Depends()]
