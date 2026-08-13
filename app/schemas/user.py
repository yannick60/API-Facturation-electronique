from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email:    EmailStr
    firstname:    str
    lastname:    str
    password: str

class UserLogin(BaseModel):
    email:    EmailStr
    password: str

class UserResponse(BaseModel):
    id:          int
    email:       str
    firstname:   str | None
    lastname:    str | None
    model_config = {"from_attributes": True}

# Tokens renvoyés après connexion
class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"

class GoogleAuthRequest(BaseModel): 
    token: str


    #-------------- Company -----------------

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


# ════════════════════════════════════════════════════════════════
# VAT SETTING (imbriqué dans CompanyResponse)
# ════════════════════════════════════════════════════════════════

class VatSettingResponse(BaseModel):
    id:              int
    country:         str
    label:           str
    rate:            float
    ubl_category_id: str        # ✅ ajouté — nécessaire pour l'UBL
    is_default:      bool
    is_active:       bool

    model_config = {"from_attributes": True}


# ════════════════════════════════════════════════════════════════
# COMPANY
# ════════════════════════════════════════════════════════════════

class CompanyCreate(BaseModel):
    name:                 str
    siret:                str = Field(..., min_length=14, max_length=14)  # ✅ validation longueur
    address:              str
    legal_form:           str
    vat_setting_id:       Optional[int]  = None
    invoice_pattern:      str            = "FAC-{year}-{sequence:04d}"
    invoice_reset_yearly: bool           = True

    # ── Champs ajoutés pour l'UBL / PDP ─────────────────────────
    city:           Optional[str]  = None   # ✅ ville séparée pour l'UBL
    zip_code:       Optional[str]  = None   # ✅ code postal séparé
    country_code:   str            = "FR"   # ✅ code pays ISO
    email:          Optional[str]  = None   # ✅ contact UBL
    iban:           Optional[str]  = None   # ✅ virement bancaire UBL
    vat_number:     Optional[str]  = None   # ✅ numéro TVA intracommunautaire
    is_vat_subject: bool           = False  # ✅ assujetti TVA ou franchise en base

    @field_validator("siret")
    @classmethod
    def siret_must_be_numeric(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Le SIRET doit contenir uniquement des chiffres")
        return v

    @field_validator("vat_number")
    @classmethod
    def vat_number_format(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("FR"):
            raise ValueError("Le numéro de TVA doit commencer par FR")
        return v


class CompanyUpdate(BaseModel):
    name:                 Optional[str]  = None
    siret:                Optional[str]  = Field(None, min_length=14, max_length=14)
    address:              Optional[str]  = None
    legal_form:           Optional[str]  = None
    invoice_reset_yearly: Optional[bool] = None
    invoice_pattern:      Optional[str]  = None  

    # ── Champs UBL / PDP ─────────────────────────────────────────
    city:           Optional[str]  = None   
    zip_code:       Optional[str]  = None   
    country_code:   Optional[str]  = None   
    email:          Optional[str]  = None   
    iban:           Optional[str]  = None   
    vat_number:     Optional[str]  = None   
    is_vat_subject: Optional[bool] = None   
    vat_setting_id: Optional[int]  = None   

class CompanyResponse(BaseModel):
    id:                   int
    name:                 str
    siret:                str
    address:              str
    legal_form:           str
    invoice_pattern:      str
    invoice_reset_yearly: bool           
    next_invoice_number:  int            
    is_active:            bool           
    created_at:           datetime       

    # ── Champs UBL / PDP ─────────────────────────────────────────
    city:           Optional[str]  = None
    zip_code:       Optional[str]  = None
    country_code:   str            = "FR"
    email:          Optional[str]  = None
    iban:           Optional[str]  = None
    vat_number:     Optional[str]  = None
    is_vat_subject: bool           = False
    vat_setting_id: Optional[int]  = None

    # ── Relation imbriquée ────────────────────────────────────────
    vat_setting:    Optional[VatSettingResponse] = None  # ✅ objet complet au lieu de l'ID seul

    # ── PDP — jamais exposés au client ───────────────────────────
    # pdp_access_token  ← volontairement absent (sécurité)
    # pdp_refresh_token ← volontairement absent (sécurité)
    pdp_connected:  bool = False   # ✅ indique juste si le compte PDP est connecté

    pdp_adress_electronique: Optional[str] = None  # ✅ ajouté — adresse électronique PDP

    model_config = {"from_attributes": True}

    @property
    def siren(self) -> str:
        """Dérive le SIREN depuis le SIRET — pas besoin de le stocker."""
        return self.siret[:9] if self.siret else ""


class CompanyShortResponse(BaseModel):
    """Version allégée pour les listes et les relations imbriquées."""
    id:    int
    name:  str
    siret: str

    model_config = {"from_attributes": True}

       

class UserWithCompanyResponse(UserResponse):
    company: CompaniesResponse | None 
    user: UserResponse

class CompaniesResponse(BaseModel):
    companies : list[CompanyResponse]