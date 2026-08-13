"""
app/routers/pdp.py

Endpoints FastAPI pour l'intégration SUPER PDP.
Traduit le flow du code Go en routes REST utilisables par le frontend Next.js.
"""

import secrets
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.invoice import Invoice
from app.services.pdp_service import SuperPDPService, get_pdp_service
from app.services.ubl import generate_ubl          # ton générateur UBL (voir ci-dessous)
from sqlalchemy import select

router = APIRouter(prefix="/pdp", tags=["PDP - Facturation électronique"])


# ── 1. Connexion OAuth2 (Authorization Code) ─────────────────────
# Équivalent du handler "GET /connect" du code Go

@router.get("/connect")
async def connect_pdp(
    current_user: User = Depends(get_current_user),
    pdp: SuperPDPService = Depends(get_pdp_service),
):
    """
    Redirige l'utilisateur vers le tunnel d'inscription SUPER PDP.
    Permet à un client de connecter son compte SUPER PDP à Facture-moi.
    """
    state = secrets.token_urlsafe(16)
    url   = pdp.get_authorization_url(state)
    return RedirectResponse(url)


# ── 2. Callback OAuth2 ───────────────────────────────────────────
# Équivalent du handler "GET /callback" du code Go

@router.get("/callback")
async def pdp_callback(
    code:         str = Query(...),
    state:        str = Query(...),
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
    pdp:          SuperPDPService = Depends(get_pdp_service),
):
    """
    Reçoit le code OAuth2 après inscription SUPER PDP,
    l'échange contre un token et le stocke pour l'utilisateur.
    """
    token_data = await pdp.exchange_code_for_token(code)

    # TODO: stocker token_data["access_token"] et token_data["refresh_token"]
    # dans la table users ou une table dédiée pdp_connections
    # await save_pdp_token(db, current_user.id, token_data)

    return {"message": "Compte SUPER PDP connecté avec succès", "token": token_data}


# ── 3. Info entreprise connectée ─────────────────────────────────
# Équivalent de GET /v1.beta/companies/me du code Go

@router.get("/company")
async def get_company(
    #current_user: User = Depends(get_current_user),
    pdp: SuperPDPService = Depends(get_pdp_service),
):
    """Retourne les infos de l'entreprise depuis SUPER PDP."""
    company = await pdp.get_company()
    return company

@router.get("/invoices")
async def get_invoices(
    #current_user: User = Depends(get_current_user),
    pdp: SuperPDPService = Depends(get_pdp_service),
):
    invoices = await pdp.list_invoices()
    print("Invoices from PDP:", invoices)
    return invoices

@router.get("/invoices/{direction}")
async def get_invoices(
    direction: str ,
    current_user: User = Depends(get_current_user),
    pdp: SuperPDPService = Depends(get_pdp_service),
):
    invoices = await pdp.list_invoices(direction=direction)
    
    return invoices


# ── 4. Envoi d'une facture ───────────────────────────────────────

@router.post("/invoices/{facture_id}/send")
async def send_invoice(
    facture_id:   int,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
    pdp:          SuperPDPService = Depends(get_pdp_service),
):
    """
    Envoie une facture électronique à SUPER PDP.
    Étapes : génération UBL → validation → envoi → mise à jour statut.
    """
    # Récupère la facture depuis la base
    result  = await db.execute(select(Invoice).where(Invoice.id == facture_id))
    facture = result.scalar_one_or_none()

    if not facture:
        raise HTTPException(status_code=404, detail="Facture introuvable")

    # Génère le XML UBL à partir de la facture
    ubl_xml = await generate_ubl(facture, db)
    print("UBL généré :", ubl_xml)

    # Envoie via SUPER PDP (validation + envoi + polling)
    pdp_invoice = await pdp.send_invoice(ubl_xml, facture_id, db)

    return {
        "message":     "Facture envoyée électroniquement",
        "pdp_id":      pdp_invoice.id,
        "pdp_status":  pdp_invoice.status,
    }


# ── 5. Marquer comme payée ───────────────────────────────────────

@router.put("/invoices/{facture_id}/paid")
async def mark_paid(
    facture_id:   int,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
    pdp:          SuperPDPService = Depends(get_pdp_service),
):
    """
    Envoie l'événement 'Encaissée' (fr:212) à SUPER PDP
    et met à jour le statut en base.
    """
    result  = await db.execute(select(Invoice).where(Invoice.id == facture_id))
    facture = result.scalar_one_or_none()

    if not facture or not facture.pdp_invoice_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Facture PDP introuvable")

    success = await pdp.mark_as_paid(
        facture_id=facture_id,
        pdp_id=facture.pdp_invoice_id,
        db=db,
    )
    return {"success": success}

@router.post("/invoices/{facture_id}/paidsend")
async def mark_paid_send(
    facture_id:   int,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
    pdp:          SuperPDPService = Depends(get_pdp_service),
):
    """
    Envoie l'événement 'Encaissée' (fr:212) à SUPER PDP
    et met à jour le statut en base.
    """
    """result  = await db.execute(select(Invoice).where(Invoice.id == facture_id))
    facture = result.scalar_one_or_none()

    if not facture or not facture.pdp_invoice_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Facture PDP introuvable")"""

    success = await pdp.mark_as_paid_send(
        facture_id=facture_id,
        pdp_id=facture_id,
        db=db,
    )
    return {"success": success}

@router.post("/invoices/{facture_id}/accepted")
async def mark_accepted(
    facture_id:   int,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
    pdp:          SuperPDPService = Depends(get_pdp_service),
):
    

    success = await pdp.mark_as_accept(
        pdp_id=facture_id,
    )
    return {"success": success}

@router.post("/invoices/{facture_id}/refused")
async def mark_refused(
    facture_id:   int,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
    pdp:          SuperPDPService = Depends(get_pdp_service),
):
    

    success = await pdp.mark_as_accept(
        pdp_id=facture_id,
    )
    return {"success": success}

# ── 6. Statut d'une facture ──────────────────────────────────────

@router.get("/invoices/{facture_id}/status")
async def get_invoice_status(
    facture_id:   int,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
    pdp:          SuperPDPService = Depends(get_pdp_service),
):
    """Récupère le statut actuel d'une facture chez SUPER PDP."""
    result  = await db.execute(select(Invoice).where(Invoice.id == facture_id))
    facture = result.scalar_one_or_none()

    if not facture or not facture.pdp_invoice_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Facture PDP introuvable")

    pdp_invoice = await pdp.get_invoice(facture.pdp_invoice_id)
    return {"pdp_id": pdp_invoice.id, "status": pdp_invoice.status}


# ── 7. Test sandbox ──────────────────────────────────────────────

@router.get("/test")
async def test_sandbox(
    current_user: User = Depends(get_current_user),
    pdp: SuperPDPService = Depends(get_pdp_service),
):
    """
    Génère et envoie une facture de test en sandbox.
    Reproduit le flow complet du script Go fourni.
    """
    # Facture de test SUPER PDP
    test_ubl = await pdp.generate_test_invoice(format="ubl")

    # Validation
    report = await pdp.validate_invoice(test_ubl)

    return {
        "test_invoice_length": len(test_ubl),
        "validation": {
            "is_valid": report.is_valid,
            "errors":   report.errors,
            "warnings": report.warnings,
        }
    }