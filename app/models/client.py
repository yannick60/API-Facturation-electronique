from sqlalchemy import String, Boolean, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func, ForeignKey
from datetime import datetime
from app.core.database import Base

class Client(Base):

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True
    )

    name_contact: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    siret: Mapped[str] = mapped_column(
        String(14),
        unique=True,
        nullable=True
    )

    vat_number: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )

    is_professional: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=True
    )

    pdp_routing_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    address: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    legal_form: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )
    city: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    zip_code: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    country_code: Mapped[str] = mapped_column(
        String(2), default="FR"     # code ISO 3166-1 alpha-2
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        onupdate=lambda: datetime.now(__import__("datetime").timezone.utc)
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    """endpoint_id: Mapped[str | None] = mapped_column(
    String(100),
    nullable=True
    )

    endpoint_scheme_id: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    peppol_registered: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    peppol_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )"""

    # FK vers User
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    # relation ORM
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="clients"
    )

    user : Mapped["User"] = relationship(
        "User",
        back_populates="clients"
    )

    invoices: Mapped[list["Invoice"]] = relationship(
    "Invoice",
    back_populates="client",
    cascade="all, delete-orphan"

)