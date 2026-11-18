from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base, TimestampMixin


# Sesiones iniciadas. Al navegador solo llega una cookie con el `id` de la
# sesión (un valor aleatorio); el resto de los datos queda en esta tabla.
class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Si se elimina el usuario, se eliminan sus sesiones.
    userId: Mapped[UUID] = mapped_column(
        "user_id", ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expiresAt: Mapped[datetime] = mapped_column(
        "expires_at", DateTime(timezone=True), index=True
    )


# Enlaces de recuperación pendientes. Solo se guarda el `jti` del JWT: la
# firma y la expiración se validan al decodificarlo.
class PasswordResetTokenModel(TimestampMixin, Base):
    __tablename__ = "password_reset_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Si se elimina el usuario, se eliminan sus enlaces pendientes.
    userId: Mapped[UUID] = mapped_column(
        "user_id", ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # `None` mientras el enlace está pendiente; se marca al usarlo.
    usedAt: Mapped[datetime | None] = mapped_column(
        "used_at", DateTime(timezone=True), nullable=True
    )
