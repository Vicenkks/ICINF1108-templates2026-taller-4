from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base, TimestampMixin


# Usuarios que pueden iniciar sesión en la API (no confundir con Student,
# que es el recurso del CRUD).
class UserModel(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    passwordHash: Mapped[str] = mapped_column("password_hash", String(255))
