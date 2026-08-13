"""
app/services/ubl.py

Génération de factures au format UBL 2.1 (Universal Business Language).
C'est le format XML attendu par SUPER PDP pour l'envoi électronique.
Conforme à la norme AFNOR XP Z12-013 et au standard Peppol BIS Billing 3.0.
"""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.invoice import Invoice,InvoiceLine
from app.models.user import User
from app.models.company import Company
from app.models.client import Client


def _escape_xml(text: str) -> str:
    """Échappe les caractères spéciaux XML."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )

def vat_number(company):

    if company.vat_number:
        return company.vat_number

    if company.siren:
        return f"FR{company.siren}"

    return ""


async def generate_ubl(facture: Invoice, db: AsyncSession) -> str:
    """
    Génère le XML UBL 2.1 d'une facture Facture-moi.

    Args:
        facture: Objet Facture SQLAlchemy avec toutes ses relations
        db:      Session AsyncSession pour charger les relations

    Returns:
        str: XML UBL 2.1 valide, prêt à être envoyé à SUPER PDP
    """
    # ── Charge les données nécessaires ───────────────────────────
    # Profil entreprise (vendeur)
    result  = await db.execute(
        select(Company).where(Company.id == facture.company_id)
    )
    profil  = result.scalar_one_or_none()

    # Client (acheteur)
    result  = await db.execute(
        select(Client).where(Client.id == facture.customer_id)
    )
    client  = result.scalar_one_or_none()

    # Lignes de la facture
    result  = await db.execute(
        select(InvoiceLine).where(InvoiceLine.invoice_id == facture.id)
    )
    lignes  = result.scalars().all()

    today = (
    facture.issue_date
    if facture.issue_date
    else date.today()
)
    echeance = facture.due_date or today

    # ── Construction du XML UBL ───────────────────────────────────
    lines_xml = _generate_lines(lignes)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">

  <!-- ── En-tête ── -->
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
  <cbc:ProfileID>S1</cbc:ProfileID>
  <cbc:ID>{_escape_xml(facture.number)}</cbc:ID>
  <cbc:IssueDate>{today.isoformat()}</cbc:IssueDate>
  <cbc:DueDate>{echeance.isoformat()}</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
   <!-- Mentions françaises -->
    <cbc:Note>
    #PMT#Indemnité forfaitaire pour frais de recouvrement en cas de retard de paiement : 40 €.
    #PMD#Tout retard de paiement entraîne une pénalité calculée sur la base de trois fois le taux d'intérêt légal.
    #AAB#Aucun escompte ne sera accordé pour paiement anticipé.
    </cbc:Note>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cbc:BuyerReference>{ client.name }</cbc:BuyerReference>

  <!-- ── Note franchise en base TVA si applicable ── -->
  {_franchise_note(facture)}

  <!-- ── Vendeur (ton entreprise) ── -->
  <cac:AccountingSupplierParty>
    <cac:Party>
    <cbc:EndpointID schemeID="0225">{profil.pdp_adress_electronique if profil and profil.pdp_adress_electronique else ""}</cbc:EndpointID>
      <cac:PartyIdentification>
        <cbc:ID schemeID="0002">{_escape_xml(profil.siren)}</cbc:ID>
      </cac:PartyIdentification>
      <cac:PartyName>
        <cbc:Name>{_escape_xml(profil.name if profil else "")}</cbc:Name>
      </cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>{_escape_xml(profil.address if profil else "")}</cbc:StreetName>
        <cbc:CityName>{_escape_xml(profil.city if profil else "")}</cbc:CityName>
        <cbc:PostalZone>{_escape_xml(profil.zip_code if profil else "")}</cbc:PostalZone>
        <cac:Country>
          <cbc:IdentificationCode>FR</cbc:IdentificationCode>
        </cac:Country>
      </cac:PostalAddress>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>{vat_number(profil)}</cbc:CompanyID>
        <cac:TaxScheme>
          <cbc:ID>VAT</cbc:ID>
        </cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>{_escape_xml(profil.name if profil else "")}</cbc:RegistrationName>
        <cbc:CompanyID schemeID="0002">{_escape_xml(profil.siren if profil else "")}</cbc:CompanyID>
      </cac:PartyLegalEntity>
      <cac:Contact>
        <cbc:ElectronicMail>{_escape_xml(profil.email if profil else "")}</cbc:ElectronicMail>
      </cac:Contact>
    </cac:Party>
  </cac:AccountingSupplierParty>

  <!-- ── Acheteur (ton client) ── -->
  <cac:AccountingCustomerParty>
    <cac:Party>
    <cbc:EndpointID schemeID="0225">{client.pdp_routing_id if client and client.pdp_routing_id else ""}</cbc:EndpointID>
      <cac:PartyName>
        <cbc:Name>{_escape_xml(client.name if client else "")}</cbc:Name>
      </cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>{_escape_xml(client.address if client else "")}</cbc:StreetName>
        <cbc:CityName>{_escape_xml(client.city if client else "")}</cbc:CityName>
        <cbc:PostalZone>{_escape_xml(client.zip_code if client else "")}</cbc:PostalZone>
        <cac:Country>
          <cbc:IdentificationCode>FR</cbc:IdentificationCode>
        </cac:Country>
      </cac:PostalAddress>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>{_escape_xml(client.name if client else "")}</cbc:RegistrationName>
        {f'<cbc:CompanyID>{_escape_xml(client.siret[:9])}</cbc:CompanyID>' if client and client.siret else ""}
      </cac:PartyLegalEntity>
      <cac:Contact>
        <cbc:ElectronicMail>{_escape_xml(client.email if client else "")}</cbc:ElectronicMail>
      </cac:Contact>
    </cac:Party>
  </cac:AccountingCustomerParty>

  <!-- ── Coordonnées bancaires ── -->
  {_payment_means(profil)}

  <!-- ── Conditions de paiement ── -->
  <cac:PaymentTerms>
    <cbc:Note>{_escape_xml(facture.payment_terms or "Paiement à réception")}</cbc:Note>
  </cac:PaymentTerms>

  <!-- ── Totaux TVA ── -->
  {_tax_totals(facture, lignes)}

  <!-- ── Totaux de la facture ── -->
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">{facture.subtotal_ht:.2f}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">{facture.subtotal_ht:.2f}</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">{facture.total_ttc:.2f}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">{facture.total_ttc:.2f}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>

  <!-- ── Lignes de la facture ── -->
{lines_xml}

</Invoice>"""

    return xml


def _franchise_note(facture: Invoice) -> str:
    """Ajoute la mention légale si franchise en base de TVA."""
    if not facture.with_vat:
        return '<cbc:Note>TVA non applicable, article 293 B du CGI</cbc:Note>'
    return ""


def _payment_means(profil) -> str:
    """Génère les moyens de paiement (virement bancaire)."""
    if not profil or not profil.iban:
        return ""
    return f"""<cac:PaymentMeans>
    <cbc:PaymentMeansCode>30</cbc:PaymentMeansCode>
    <cac:PayeeFinancialAccount>
      <cbc:ID>{_escape_xml(profil.iban)}</cbc:ID>
    </cac:PayeeFinancialAccount>
  </cac:PaymentMeans>"""


def _tax_totals(facture: Invoice, lignes: list[InvoiceLine]) -> str:
    """Génère les blocs TaxTotal groupés par taux de TVA."""
    if not facture.with_vat:
        return f"""<cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">{facture.subtotal_ht:.2f}</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>
      <cac:TaxCategory>
        <cbc:ID>E</cbc:ID>
        <cbc:Percent>0</cbc:Percent>
        <cbc:TaxExemptionReasonCode>VATEX-EU-AE</cbc:TaxExemptionReasonCode>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>"""

    # Groupe par taux de TVA
    taux_map: dict[float, dict] = {}
    for ligne in lignes:
        taux = float(ligne.vat_rate or 0)
        if taux not in taux_map:
            taux_map[taux] = {"ht": 0.0, "tva": 0.0}
        taux_map[taux]["ht"]  += float(ligne.total_ht or 0)
        taux_map[taux]["tva"] += float((ligne.total_vat) or 0)

    total_tva = sum(v["tva"] for v in taux_map.values())
    subtotals = ""
    
    for taux, montants in taux_map.items():
        percent = taux * 100
        subtotals += f"""
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">{montants['ht']:.2f}</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">{montants['tva']:.2f}</cbc:TaxAmount>
      <cac:TaxCategory>
        <cbc:ID>S</cbc:ID>
        <cbc:Percent>{percent:.0f}</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>"""

    return f"""<cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">{total_tva:.2f}</cbc:TaxAmount>
    {subtotals}
  </cac:TaxTotal>"""


def _generate_lines(lignes: list[InvoiceLine]) -> str:
    """Génère les lignes de la facture en XML UBL."""
    xml = ""
    for i, ligne in enumerate(lignes, start=1):
        taux   = float(ligne.vat_rate or 0)
        cat_id = "S" if taux > 0 else "E"
        percent = taux * 100
        xml += f"""  <cac:InvoiceLine>
    <cbc:ID>{i}</cbc:ID>
    <cbc:InvoicedQuantity unitCode="C62">{ligne.quantity:.2f}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">{float(ligne.total_ht or 0):.2f}</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Description>{_escape_xml(ligne.description)}</cbc:Description>
      <cbc:Name>{_escape_xml(ligne.description[:50] if ligne.description else "")}</cbc:Name>
      <cac:ClassifiedTaxCategory>
        <cbc:ID>{cat_id}</cbc:ID>
        <cbc:Percent>{percent:.0f}</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:ClassifiedTaxCategory>
    </cac:Item>
    <cac:Price>
    <cbc:PriceAmount currencyID="EUR">
        {float(ligne.unit_price_ht):.2f}
    </cbc:PriceAmount>

    <cbc:BaseQuantity unitCode="C62">
        1
    </cbc:BaseQuantity>

</cac:Price>
  </cac:InvoiceLine>
"""
    return xml