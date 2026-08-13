from datetime import date, datetime, timezone

from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from decimal import Decimal

from app.core.database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "number",
            name="uq_invoice_company_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    number: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id")
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id")
    )

    issue_date: Mapped[date] = mapped_column(
        Date
    )

    due_date: Mapped[date] = mapped_column(
        Date
    )

    subtotal_ht: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
    )

    total_vat: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
    )

    total_ttc: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
    )

    status_id: Mapped[int] = mapped_column(
    ForeignKey("invoice_statuses.id")
    )  

    status: Mapped["InvoiceStatus"] = relationship(
    "InvoiceStatus",
    lazy="selectin"
    )

    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    # ID de la facture chez SUPER PDP après envoi
    pdp_invoice_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Date d'envoi électronique
    pdp_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # La facture est-elle assujettie à la TVA ?
    # False = franchise en base (mention légale automatique dans l'UBL)
    with_vat: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    # Conditions de paiement (texte libre, ex: "30 jours fin de mois")
    payment_terms: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="invoices"
    )

    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="invoices"
    )

    archive_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class InvoiceLine(Base):
    __tablename__ = "invoiceLines"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id")
    )

    description: Mapped[str] = mapped_column(
        String(255)
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    unit_price_ht: Mapped[Decimal] = mapped_column(
        Numeric(10, 2)
    )

    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2)
    )

    total_vat: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
    )

    total_ht: Mapped[Decimal] = mapped_column(
        Numeric(10, 2)
    )

    total_ttc: Mapped[Decimal] = mapped_column(
        Numeric(10, 2)
    )

    invoice = relationship(
        "Invoice",
        back_populates="lines"
    )


class InvoiceCounter(Base):
    __tablename__ = "invoice_counters"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id")
    )

    last_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    company: Mapped["Company"] = relationship(
        back_populates="invoice_counter"
    )

class InvoiceStatus(Base):
    __tablename__ = "invoice_statuses"

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True
    )

    label: Mapped[str] = mapped_column(
        String(100)
    )