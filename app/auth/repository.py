from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.models import PasswordResetTokenModel, UserSessionModel


class AuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Sesiones ---------------------------------------------------------

    def find_active_session(
        self, session_id: str, now: datetime
    ) -> UserSessionModel | None:
        query = select(UserSessionModel).where(
            UserSessionModel.id == session_id,
            UserSessionModel.expiresAt > now,
        )
        return self.db.scalar(query)

    def add_session(self, session: UserSessionModel) -> UserSessionModel:
        self.db.add(session)
        self.db.flush()
        return session

    def delete_session(self, session_id: str) -> None:
        self.db.execute(
            delete(UserSessionModel).where(UserSessionModel.id == session_id)
        )

    def delete_user_sessions(self, user_id: UUID) -> None:
        self.db.execute(
            delete(UserSessionModel).where(UserSessionModel.userId == user_id)
        )

    def delete_expired_sessions(self, now: datetime) -> None:
        self.db.execute(
            delete(UserSessionModel).where(UserSessionModel.expiresAt <= now)
        )

    # --- Recuperación de contraseña --------------------------------------

    def add_password_reset_token(
        self, token: PasswordResetTokenModel
    ) -> PasswordResetTokenModel:
        self.db.add(token)
        self.db.flush()
        return token

    def find_password_reset_token(self, jti: str) -> PasswordResetTokenModel | None:
        return self.db.get(PasswordResetTokenModel, jti)

    def delete_password_reset_tokens_for_user(self, user_id: UUID) -> None:
        self.db.execute(
            delete(PasswordResetTokenModel).where(
                PasswordResetTokenModel.userId == user_id
            )
        )
