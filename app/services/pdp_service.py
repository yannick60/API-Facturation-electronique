"""
app/services/pdp.py

Service d'intégration SUPER PDP.
Gère l'authentification OAuth2 (client_credentials + authorization_code),
l'envoi de factures électroniques UBL, la validation, le suivi de statut
et les événements de cycle de vie.

Endpoints utilisés (API SUPER PDP v1.beta) :
  POST /oauth2/token                          — obtention du token
  GET  /v1.beta/companies/me                  — info entreprise connectée
  GET  /v1.beta/invoices/generate_test_invoice — facture de test
  POST /v1.beta/validation_reports            — validation avant envoi
  POST /v1.beta/invoices                      — envoi de la facture
  GET  /v1.beta/invoices                      — liste des factures
  GET  /v1.beta/invoices/{id}                 — détail d'une facture
  POST /v1.beta/invoice_events                — mise à jour du statut (ex: encaissée)

Doc officielle : https://www.superpdp.tech/documentation
"""

import httpx
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────────
SUPERPDP_ENDPOINT  = "https://api.superpdp.tech"
SUPERPDP_AUTH_URL  = f"{SUPERPDP_ENDPOINT}/oauth2/authorize"
SUPERPDP_TOKEN_URL = f"{SUPERPDP_ENDPOINT}/oauth2/token"
API_BASE           = f"{SUPERPDP_ENDPOINT}/v1.beta"

# Codes statut SUPER PDP (norme française)
class StatusCode:
    ENVOYEE   = "fr:201"   # Facture envoyée
    RECUE     = "fr:202"   # Facture reçue par l'acheteur
    ACCEPTEE  = "fr:205"   # Acceptée par l'acheteur
    REFUSEE   = "fr:210"   # Refusée par l'acheteur
    ENCAISSEE = "fr:212"   # Paiement reçu
    PAIDSEND   = "fr:211"   # Paiment envoyé (ex: virement initié)


# ── Token cache en mémoire ───────────────────────────────────────
@dataclass
class TokenCache:
    access_token: str
    expires_at:   datetime

    def is_valid(self) -> bool:
        # Marge de 60s pour éviter les expirations en vol
        return datetime.now(timezone.utc) < (self.expires_at - timedelta(seconds=60))


# ── Schémas de données ───────────────────────────────────────────
@dataclass
class PDPCompany:
    """Informations entreprise retournées par SUPER PDP."""
    formal_name: str
    siren:       str
    siret:       Optional[str] = None


@dataclass
class PDPInvoice:
    """Facture retournée par SUPER PDP après envoi."""
    id:         int
    status:     str
    direction:     str
    amount:     str
    number:     Optional[str] = None
    en_invoice: Optional[dict] = None   
    events:     Optional[list[dict]] = None
    created_at: Optional[str] = None


@dataclass
class ValidationReport:
    """Résultat de validation d'une facture."""
    is_valid: bool
    errors:   list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════
# SERVICE PRINCIPAL
# ════════════════════════════════════════════════════════════════

class SuperPDPService:
    """
    Service d'intégration SUPER PDP.

    Deux modes d'authentification selon le contexte :

    1. CLIENT CREDENTIALS (machine-to-machine)
       → Pour envoyer des factures en ton propre nom.
       → Utilise SUPERPDP_CLIENT_ID + SUPERPDP_CLIENT_SECRET du .env.

    2. AUTHORIZATION CODE (au nom d'un utilisateur)
       → Pour que tes clients connectent leur compte SUPER PDP 
       → Utilise le token stocké en base pour cet utilisateur.
    """

    def __init__(self):
        self._token_cache: Optional[TokenCache] = None
        self._client = httpx.AsyncClient(timeout=30.0)

    # ── Auth : Client Credentials ────────────────────────────────

    async def _get_token_client_credentials(self) -> str:
        """
        Obtient ou renouvelle le token OAuth2 en mode client_credentials.
        Équivalent Python du code Go fourni, section /oauth2/token.
        """
        if self._token_cache and self._token_cache.is_valid():
            return self._token_cache.access_token

        logger.info("Renouvellement du token SUPER PDP (client_credentials)")

        resp = await self._client.post(
            SUPERPDP_TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     settings.ID_PDP_TEST,
                "client_secret": settings.SECRET_PDP_TEST,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self._raise_for_status(resp, "Obtention du token SUPER PDP")

        data       = resp.json()
        expires_in = data.get("expires_in", 3600)

        self._token_cache = TokenCache(
            access_token=data["access_token"],
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        )
        return self._token_cache.access_token

    # ── Auth : Authorization Code (au nom d'un utilisateur) ──────

    def get_authorization_url(self, state: str) -> str:
        """
        Génère l'URL de redirection vers le tunnel SUPER PDP.
        Équivalent Python de oauth2Config.AuthCodeURL(state).

        Utilisation dans ton router FastAPI :
            url = pdp_service.get_authorization_url(state)
            return RedirectResponse(url)
        """
        import urllib.parse
        params = {
            "response_type": "code",
            "client_id":     settings.SUPERPDP_CLIENT_ID,
            "redirect_uri":  settings.SUPERPDP_REDIRECT_URI,
            "state":         state,
        }
        return f"{SUPERPDP_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> dict:
        """
        Échange le code d'autorisation contre un token.
        Équivalent Python de oauth2Config.Exchange().
        Appelé dans ton endpoint /callback.
        """
        resp = await self._client.post(
            SUPERPDP_TOKEN_URL,
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "client_id":     settings.SUPERPDP_CLIENT_ID,
                "client_secret": settings.SUPERPDP_CLIENT_SECRET,
                "redirect_uri":  settings.SUPERPDP_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self._raise_for_status(resp, "Échange du code OAuth2")
        return resp.json()   # contient access_token, refresh_token, expires_in

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # ── Entreprise ────────────────────────────────────────────────

    async def get_company(self, token: Optional[str] = None) -> PDPCompany:
        """
        Récupère les infos de l'entreprise connectée.
        Équivalent de GET /v1.beta/companies/me.
        """
        token = token or await self._get_token_client_credentials()
        resp  = await self._client.get(
            f"{API_BASE}/directory_entries",
            headers=self._auth_headers(token),
        )
        self._raise_for_status(resp, "Récupération entreprise SUPER PDP")
        data = resp.json()
        return PDPCompany(
            formal_name=data.get("formal_name", ""),
            siren=data.get("siren", ""),
            siret=data.get("siret"),
        )

    # ── Validation ────────────────────────────────────────────────

    async def validate_invoice(self, ubl_xml: str) -> ValidationReport:
        """
        Valide une facture UBL avant envoi.
        Équivalent de POST /v1.beta/validation_reports du code Go.

        À appeler TOUJOURS avant send_invoice pour éviter les rejets.
        """

        files = {
            "file_name": (
                "facture.xml",
                ubl_xml.encode("utf-8"),
                "application/xml",
            )
        }

        resp = await self._client.post(
            f"{API_BASE}/validation_reports",
            files=files,
            headers=self._auth_headers(await self._get_token_client_credentials()),
        )
        self._raise_for_status(resp, "Validation de la facture")

        data    = resp.json()
        results = data.get("data", [{}])
        first   = results[0] if results else {}

        return ValidationReport(
            is_valid=first.get("is_valid", False),
            errors=first.get("errors", []),
            warnings=first.get("warnings", []),
        )

    # ── Génération d'une facture de test ──────────────────────────

    async def generate_test_invoice(
        self,
        format: str = "ubl",
        token: Optional[str] = None,
    ) -> str:
        """
        Télécharge une facture de test prête à être envoyée.
        Utile pour les tests en sandbox.
        Équivalent de GET /v1.beta/invoices/generate_test_invoice du code Go.
        """
        token = token or await self._get_token_client_credentials()
        resp  = await self._client.get(
            f"{API_BASE}/invoices/generate_test_invoice",
            params={"format": format},
            headers=self._auth_headers(token),
        )
        self._raise_for_status(resp, "Génération facture de test")
        return resp.text

    # ── Envoi de facture ──────────────────────────────────────────

    async def send_invoice(
        self,
        ubl_xml:     str,
        facture_id:  int,
        db:          AsyncSession,
        token:       Optional[str] = None,
    ) -> PDPInvoice:
        """
        Envoie une facture électronique à SUPER PDP.
        Équivalent de POST /v1.beta/invoices du code Go.

        Étapes :
          1. Validation de la facture (rejet si invalide)
          2. Envoi à SUPER PDP
          3. Mise à jour du statut en base
          4. Attente du traitement (polling)

        Args:
            ubl_xml:    Contenu XML de la facture au format UBL 2.1
            facture_id: ID de la facture dans ta base Facture-moi
            db:         Session SQLAlchemy
            token:      Token OAuth2 (optionnel, sinon client_credentials)
        """
        token = token or await self._get_token_client_credentials()
        print(token)
        # ── 1. Validation préalable ──────────────────────────────
        logger.info(f"Validation facture {facture_id} avant envoi PDP")
        report = await self.validate_invoice(ubl_xml)

        if not report.is_valid:
            errors_str = "; ".join(report.errors)
            logger.error(f"Facture {facture_id} invalide : {errors_str}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Facture invalide pour envoi électronique : {errors_str}",
            )

        if report.warnings:
            logger.warning(f"Facture {facture_id} — avertissements : {report.warnings}")

        # ── 2. Envoi ─────────────────────────────────────────────
        logger.info(f"Envoi facture {facture_id} à SUPER PDP")
        resp = await self._client.post(
            f"{API_BASE}/invoices",
            content=ubl_xml.encode("utf-8"),
            headers={
                **self._auth_headers(token),
                "Content-Type": "application/xml",
            },
        )
        self._raise_for_status(resp, f"Envoi facture {facture_id}")
        data        = resp.json()
        pdp_invoice = PDPInvoice(id=data["id"], status=data.get("status", ""),created_at=data.get("created_at"),direction=data.get("direction", ""),amount=data.get("en_invoice", {}).get("totals", {}).get("total_with_vat"),en_invoice=data.get("en_invoice"),events=data.get("events"))

        # ── 3. Mise à jour en base ───────────────────────────────
        await db.execute(
            update(Invoice)
            .where(Invoice.id == facture_id)
            .values(
                pdp_invoice_id=pdp_invoice.id,
                pdp_sent_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        logger.info(f"Facture {facture_id} envoyée — ID PDP : {pdp_invoice.id}")

        # ── 4. Polling jusqu'au traitement ───────────────────────
        pdp_invoice = await self._wait_for_processing(pdp_invoice.id, token)

        return pdp_invoice

    async def _wait_for_processing(
        self,
        pdp_id:   int,
        token:    str,
        max_wait: int = 10,
    ) -> PDPInvoice:
        """
        Attend que SUPER PDP traite la facture (max 10 tentatives, 500ms entre chaque).
        Équivalent de la boucle d'attente du code Go.
        """
        for i in range(max_wait):
            invoice = await self.get_invoice(pdp_id, token)
            if invoice.en_invoice:
                logger.info(f"Facture PDP {pdp_id} traitée après {i+1} tentative(s)")
                return invoice
            await asyncio.sleep(0.5)

        logger.warning(f"Facture PDP {pdp_id} pas encore traitée après {max_wait} tentatives")
        return PDPInvoice(id=pdp_id, status="en_traitement")

    # ── Récupération d'une facture ────────────────────────────────

    async def get_invoice(
        self,
        pdp_id: int,
        token:  Optional[str] = None,
    ) -> PDPInvoice:
        """
        Récupère le détail d'une facture par son ID SUPER PDP.
        Équivalent de GET /v1.beta/invoices/{id} du code Go.
        """
        token = token or await self._get_token_client_credentials()
        resp  = await self._client.get(
            f"{API_BASE}/invoices/{pdp_id}",
            headers=self._auth_headers(token),
        )
        self._raise_for_status(resp, f"Récupération facture PDP {pdp_id}")
        data = resp.json()
        return PDPInvoice(
            id=data["id"],
            status=data.get("status", ""),
            en_invoice=data.get("en_invoice"),
            created_at=data.get("created_at"),
            direction=data.get("direction", ""),
            amount=data.get("en_invoice", {}).get("totals", {}).get("total_with_vat"),
            events=data.get("events"),
        )

    async def list_invoices(
        self,
        order:             str = "desc",
        starting_after_id: Optional[int] = None,
        token:             Optional[str] = None,
        direction: Optional[str] = "in",  
    ) -> list[PDPInvoice]:
        """
        Liste les factures reçues ou envoyées.
        Équivalent de GET /v1.beta/invoices du code Go.
        """
        token  = token or await self._get_token_client_credentials()
        params = {"order": order}
        if starting_after_id:
            params["starting_after_id"] = starting_after_id
        params["direction"] = direction  
        params["expand"] = ["en_invoice","en_invoice.invoice","en_invoice.seller","events"] # Limite max par la doc SUPER PDP

        resp = await self._client.get(
            f"{API_BASE}/invoices",
            params=params,
            headers=self._auth_headers(token),
        )
        self._raise_for_status(resp, "Liste des factures PDP")
        data = resp.json()
        print("Invoices from PDP:", data)  # Debug : affiche la réponse brute
        return [
            PDPInvoice(id=inv["id"],created_at=inv["created_at"],direction=inv["direction"],number=inv.get("en_invoice",{}).get("number","") ,status=inv.get("status", ""),amount=inv.get("en_invoice", {}).get("totals",{}).get("total_with_vat"),en_invoice=inv.get("en_invoice"),events=inv.get("events"))
            for inv in data.get("data", [])
        ]

    # ── Événements de cycle de vie ────────────────────────────────

    async def send_status(
        self,
        pdp_invoice_id: int,
        note:        list[dict],
        status_code:    str = StatusCode.ENCAISSEE,
        token:          Optional[str] = None,
    ) -> bool:
        """
        Envoie un événement de statut (ex: facture encaissée/payée).
        Équivalent de POST /v1.beta/invoice_events du code Go.

        Args:
            pdp_invoice_id: ID de la facture chez SUPER PDP
            amounts:        Liste des montants encaissés par taux de TVA
            status_code:    Code statut (voir StatusCode)

        Exemple d'amounts :
            [
                {"net_amount": "1800.00", "currency_code": "EUR",
                 "type_code": "MEN", "vat_rate": "20.0", "date": "2026-03-31"},
                {"net_amount": "63.79", "currency_code": "EUR",
                 "type_code": "MEN", "vat_rate": "5.5", "date": "2026-03-31"},
            ]
        """
        import json as json_lib
        token = token or await self._get_token_client_credentials()

        payload = {
            "invoice_id":  pdp_invoice_id,
            "status_code": status_code,
            "details":     [{"note": [{"contents":[{"content":note}]}]}],
        }

        resp = await self._client.post(
            f"{API_BASE}/invoice_events",
            content=json_lib.dumps(payload).encode("utf-8"),
            headers={
                **self._auth_headers(token),
                "Content-Type": "application/json",
            },
        )
        self._raise_for_status(resp, f"Envoi statut facture PDP {pdp_invoice_id}")
        logger.info(f"Statut {status_code} envoyé pour facture PDP {pdp_invoice_id}")
        return True

    
    

    async def mark_as_paid(
        self,
        facture_id:  int,
        pdp_id:      int,
        db:          AsyncSession,
        token:       Optional[str] = None,
    ) -> bool:
        """
        Raccourci : marque une facture comme encaissée côté PDP
        et met à jour le statut en base.

        Args:
            facture_id: ID local dans Facture-moi
            pdp_id:     ID chez SUPER PDP
            net_amount: Montant HT encaissé (ex: "1800.00")
            vat_rate:   Taux TVA (ex: "20.0")
            paid_date:  Date encaissement format "YYYY-MM-DD"
        """
        success = await self.send_status(
            pdp_invoice_id=pdp_id,
            status_code=StatusCode.ENCAISSEE,
            note="Paiement reçu",
            token=token,
        )

        if success:
            result = await db.execute(select(InvoiceStatus).where(InvoiceStatus.code=="paid"))
            status = result.scalar_one_or_none()
            await db.execute(
                update(Invoice)
                .where(Invoice.id == facture_id)
                .values(statut_id=status.id, paid_at=datetime.now(timezone.utc))
            )
            await db.commit()

        return success

    async def mark_as_paid_send(
            self,
            facture_id:  int,
            pdp_id:      int,
            db:          AsyncSession,
            token:       Optional[str] = None,
        ) -> bool:
            success = await self.send_status(
                pdp_invoice_id=pdp_id,
                status_code=StatusCode.PAIDSEND,
                note="Virement bancaire initié",
                token=token,
            )
    
            return success

    async def mark_as_accept(
                self,
                pdp_id:      int,
                token:       Optional[str] = None,
            ) -> bool:
                success = await self.send_status(
                    pdp_invoice_id=pdp_id,
                    status_code=StatusCode.ACCEPTEE,
                    note="Facture acceptée par l'acheteur",
                    token=token,
                )
        
                return success

    async def mark_as_refused(
                    self,
                    pdp_id:      int,
                    token:       Optional[str] = None,
                ) -> bool:
                    success = await self.send_status(
                        pdp_invoice_id=pdp_id,
                        status_code=StatusCode.REFUSEE,
                        note="Facture refusée par l'acheteur",
                        token=token,
                    )
            
                    return success

    # ── Utilitaires ───────────────────────────────────────────────

    def _raise_for_status(self, resp: httpx.Response, context: str) -> None:
        if resp.status_code >= 400:
            logger.error(f"{context} — HTTP {resp.status_code} : {resp.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Erreur SUPER PDP ({context}) : HTTP {resp.status_code}",
            )

    async def close(self):
        await self._client.aclose()


# ── Singleton injectable via FastAPI Depends ──────────────────────
_pdp_service: Optional[SuperPDPService] = None

def get_pdp_service() -> SuperPDPService:
    global _pdp_service
    if _pdp_service is None:
        _pdp_service = SuperPDPService()
    return _pdp_service