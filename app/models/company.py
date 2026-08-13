from sqlalchemy import String, Boolean, Float, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base

class Company(Base):

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    siret: Mapped[str] = mapped_column(
        String(14),
        unique=True,
        index=True,
        nullable=False
    )

    address: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    legal_form: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    invoice_pattern: Mapped[str] = mapped_column(
    String(255),
    default="FAC-{year}-{sequence:04d}"
    )

    invoice_reset_yearly: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    next_invoice_number: Mapped[int] = mapped_column(
        default=1
    )

    last_invoice_year: Mapped[int | None] = mapped_column(
        Integer,
    nullable=True,
    )

     # SIREN (9 chiffres) — obligatoire dans l'UBL, dérivable du SIRET
    # mais mieux de le stocker explicitement
    siren: Mapped[str | None] = mapped_column(
        String(9),
        nullable=True,
        index=True,
    )

    # Numéro de TVA intracommunautaire (ex: FR12345678901)
    # Obligatoire dans l'UBL si assujetti à la TVA
    vat_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Ville et code postal — nécessaires pour le bloc adresse UBL
    # Ton champ `address` est un String(500) mais l'UBL attend
    # des champs séparés (StreetName, CityName, PostalZone)
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    zip_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    country_code: Mapped[str] = mapped_column(
        String(2),
        default="FR",      # code ISO 3166-1 alpha-2
    )

    # IBAN pour le bloc PaymentMeans de l'UBL (virement bancaire)
    iban: Mapped[str | None] = mapped_column(
        String(34),
        nullable=True,
    )

    # Email de contact — requis dans le bloc Contact de l'UBL
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Assujetti à la TVA par défaut ?
    # Copié sur Invoice.with_vat à la création mais stocké ici
    # comme valeur par défaut du profil
    is_vat_subject: Mapped[bool] = mapped_column(
        Boolean,
        default=False,     # False = franchise en base par défaut
    )

    # Token SUPER PDP OAuth2 (si l'utilisateur connecte son compte PDP)
    pdp_access_token: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    pdp_refresh_token: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    pdp_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    pdp_adress_electronique: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )


    # FK vers User
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    clients:  Mapped[list["Client"]] = relationship(
    "Client",
    back_populates="company",
    cascade="all, delete-orphan"
    )

    invoices: Mapped[list["Invoice"]] = relationship(
    "Invoice",
    back_populates="company",
    cascade="all, delete-orphan"
    )

    invoice_counter: Mapped["InvoiceCounter"] = relationship(
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan"
    )
    # relation ORM
    user: Mapped["User"] = relationship(
        "User",
        back_populates="companies"
    )

    vat_setting_id: Mapped[int | None] = mapped_column(
        ForeignKey("vat_settings.id"),
        nullable=True
        )


class VatSetting(Base):

    __tablename__ = "vat_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    country: Mapped[str] = mapped_column(
        String(2),
        index=True,
        nullable=False
    )  

    label: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    ) 

    rate: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )  # ex: 20.0

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    ubl_category_id: Mapped[str] = mapped_column(
        String(1),
        default="S",       # S=Standard, E=Exempt, Z=Zero rated
    )