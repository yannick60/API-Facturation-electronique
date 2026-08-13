from pydantic import BaseModel, EmailStr, Field, computed_field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


# ════════════════════════════════════════════════════════════════
# INVOICE LINE
# ════════════════════════════════════════════════════════════════

class InvoiceLineCreate(BaseModel):
    invoice_id:     int
    description:    str
    quantity:       float
    unit_price_ht:  float
    vat_rate:       float           # ex: 20.0
    total_ht:       float
    total_vat:      float           # ✅ ajouté — nécessaire pour l'UBL
    total_ttc:      float

class InvoiceLineModify(BaseModel):
    id:             int
    invoice_id:     int
    description:    str
    quantity:       float
    unit_price_ht:  float
    vat_rate:       float           # ex: 20.0
    total_ht:       float
    total_vat:      float           # ✅ ajouté — nécessaire pour l'UBL
    total_ttc:      float

class InvoiceLineResponse(BaseModel):   # ✅ typo corrigée (Reponse → Response)
    id:             int
    invoice_id:     int
    description:    Optional[str]   = None
    quantity:       Optional[float] = None   # ✅ float au lieu de int (quantités décimales)
    unit_price_ht:  Optional[Decimal] = None
    vat_rate:       Optional[Decimal] = None
    total_ht:       Optional[Decimal] = None
    total_vat:      Optional[Decimal] = None  # ✅ ajouté
    total_ttc:      Optional[Decimal] = None

    model_config = {"from_attributes": True}


class InvoiceLineUpdate(BaseModel):
    description:    Optional[str]   = None
    quantity:       Optional[float] = None
    unit_price_ht:  Optional[float] = None
    vat_rate:       Optional[float] = None
    total_ht:       Optional[float] = None
    total_vat:      Optional[float] = None   # ✅ ajouté
    total_ttc:      Optional[float] = None


# ════════════════════════════════════════════════════════════════
# INVOICE STATUS
# ════════════════════════════════════════════════════════════════

class InvoiceStatusResponse(BaseModel):
    id:    int
    code:  str      # ✅ ajouté — utile pour la logique frontend (ex: "envoyee")
    label: str

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════
# INVOICE
# ════════════════════════════════════════════════════════════════

class InvoiceCreate(BaseModel):
    customer_id:    int             # ✅ renommé client_id → customer_id (cohérent avec le modèle)
    company_id:     int
    issue_date:     date            # ✅ ajouté — obligatoire à la création
    due_date:       date            # ✅ ajouté — obligatoire à la création
    with_vat:       bool  = True    # ✅ ajouté — franchise en base ou TVA
    payment_terms:  Optional[str]  = None
    notes:          Optional[str]  = None
    lines:          list[InvoiceLineCreate] = []  # ✅ ajouté — créer facture + lignes en une fois


class InvoiceResponse(BaseModel):
    id:             int
    number:         str
    customer_id:    int
    company_id:     int
    issue_date:     date
    due_date:       date
    subtotal_ht:    float
    total_vat:      float
    total_ttc:      float
    with_vat:       bool            # ✅ ajouté
    payment_terms:  Optional[str]  = None
    notes:          Optional[str]  = None
    status_id:      int
    status:         Optional[InvoiceStatusResponse] = None  # ✅ relation imbriquée
    lines:          list[InvoiceLineResponse] = []          # ✅ lignes imbriquées
    created_at:     datetime
    # ── Champs PDP ──────────────────────────────────────────────
    pdp_invoice_id: Optional[int]      = None   # ✅ ajouté
    pdp_sent_at:    Optional[datetime] = None   # ✅ ajouté

    model_config = {"from_attributes": True}

class InvoiceCreateResponse(BaseModel):
    id: int
    number: str
    company_id: int
    customer_id: int
    status_id: int
    due_date:       date
    subtotal_ht:    float
    total_vat:      float
    total_ttc:      float
    with_vat:       bool  

    model_config = {"from_attributes": True}


class InvoiceUpdateTotal(BaseModel):
    # ✅ id retiré du body — il doit être dans l'URL (PATCH /invoices/{id})
    total_ht:    Optional[float] = None
    total_vat:      Optional[float] = None
    total_ttc:      Optional[float] = None  


class InvoiceListResponse(BaseModel):
    """Réponse paginée pour la liste des factures."""
    items:  list[InvoiceResponse]
    total:  int
    page:   int
    size:   int


# ════════════════════════════════════════════════════════════════
# PDP — Schémas spécifiques à l'envoi électronique
# ════════════════════════════════════════════════════════════════

class PDPSendResponse(BaseModel):
    """Réponse après envoi d'une facture à SUPER PDP."""
    message:    str
    pdp_id:     int
    pdp_status: str


class PDPValidationResponse(BaseModel):
    """Résultat de validation UBL avant envoi."""
    is_valid:   bool
    errors:     list[str] = []
    warnings:   list[str] = []


class PDPMarkPaidRequest(BaseModel):
    """Body pour marquer une facture comme encaissée."""
    net_amount: str   = Field(..., example="1800.00")
    vat_rate:   str   = Field(..., example="20.0")
    paid_date:  str   = Field(..., example="2026-03-31")