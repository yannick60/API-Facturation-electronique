from sqlalchemy import String, Boolean, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id:           Mapped[int]      = mapped_column(primary_key=True)
    email:        Mapped[str]      = mapped_column(String(255), unique=True, index=True)
    firstname:         Mapped[str | None] = mapped_column(String(255), nullable=True)
    lastname:         Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(600), nullable=True)
    # nullable car Google OAuth n'a pas de mot de passe
    google_id:    Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_verified:  Mapped[bool]     = mapped_column(Boolean, default=False)
    is_active:    Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at:   Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    companies: Mapped[list["Company"]] = relationship(
            "Company",
            back_populates="user"
            )
    clients: Mapped[list["Client"]] = relationship(
            "Client",
            back_populates="user"
            )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} is_verified={self.is_verified} is_active={self.is_active} firstname={self.firstname} lastname={self.lastname}>"
    
