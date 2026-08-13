from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.dependencies import get_current_user, set_user_context
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.models.user import  User
from app.models.company import Company
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceCounter, InvoiceLine,InvoiceStatus
from app.schemas.user import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
)
from app.schemas.client import ClientResponse, ClientCreate
from app.schemas.invoice import InvoiceResponse,InvoiceUpdateTotal, InvoiceCreate,InvoiceLineModify, InvoiceLineResponse, InvoiceLineCreate,InvoiceCreateResponse

import logging
import sentry_sdk
from io import BytesIO

from app.services.pdf.generator import InvoicePDFGenerator




router = APIRouter(prefix="/companies", tags=["Companies"])

@router.get("/", response_model=list[CompanyResponse])
async def get_my_companies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id,
            Company.is_active == True
        )
    )

    companies = result.scalars().all()

    if not companies:
        raise HTTPException(
            status_code=404,
            detail="Companies not found"
        )

    return companies

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_one_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id,
            Company.id == company_id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    return company

@router.get("/{company_id}/clients", response_model=list[ClientResponse])
async def get_clients_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id,
            Company.id == company_id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    result = await db.execute(
        select(Client).where(
            Client.user_id == current_user.id,
            Client.company_id == company_id,
        )
    )

    clients = result.scalars().all()

    if not clients:
        raise HTTPException(
            status_code=404,
            detail="No clients found for this company"
        )

    return clients

@router.get("/{company_id}/clients/{client_id}", response_model=ClientResponse)
async def get_client_company(
    company_id: int,
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Client).where(
            Client.user_id == current_user.id,
            Client.company_id == company_id,
            Client.id == client_id
        )
    )

    clients = result.scalar_one_or_none()

    if not clients:
        raise HTTPException(
            status_code=404,
            detail="No clients found for this company"
        )

    return clients

@router.get("/{company_id}/clients/{client_id}/invoices", response_model=list[InvoiceResponse])
async def get_invoices_clients_company(
    company_id: int,
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id,
            Company.id == company_id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    result = await db.execute(
        select(Invoice).where(
            Invoice.customer_id == client_id,
            Invoice.company_id == company_id
        )
    )

    invoices = result.scalars().all()

    if not invoices:
        raise HTTPException(
            status_code=404,
            detail="No invoice found for this company"
        )

    return invoices
@router.get("/{company_id}/clients/{client_id}/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice_clients_company(
    company_id: int,
    client_id: int,
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id,
            Company.id == company_id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    result = await db.execute(
        select(Invoice).where(
            Invoice.customer_id == client_id,
            Invoice.company_id == company_id,
            Invoice.id == invoice_id
        )
    )

    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    return invoice

@router.get("/{company_id}/clients/{client_id}/invoices/{invoice_id}/invoicelines", response_model=list[InvoiceLineResponse])
async def get_invoice_clients_company(
    company_id: int,
    client_id: int,
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id,
            Company.id == company_id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    result = await db.execute(
        select(Invoice).where(
            Invoice.customer_id == client_id,
            Invoice.company_id == company_id,
            Invoice.id == invoice_id
        )
    )

    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )
    
    result = await db.execute(
        select(InvoiceLine).where(
            InvoiceLine.invoice_id == invoice_id
        )
        )
    lines = result.scalars().all()

    return lines

@router.get("/{company_id}/clients/{client_id}/invoices/{invoice_id}/pdf")
async def generate_invoice_pdf(
    company_id: int,
    client_id: int,
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id,
            Company.id == company_id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )
    
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.company_id == company_id
        )
    )

    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )

    result = await db.execute(
        select(Invoice).where(
            Invoice.customer_id == client_id,
            Invoice.company_id == company_id,
            Invoice.id == invoice_id
        )
    )

    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )
    
    result = await db.execute(
        select(InvoiceLine).where(
            InvoiceLine.invoice_id == invoice_id
        )
        )
    invoice_lines = result.scalars().all()

    iPDFg = InvoicePDFGenerator()

    pdf = iPDFg.invoice_pdf_service(
        company,
        client,
        invoice,
        invoice_lines,
    )

    return Response(
    content=pdf,
    media_type="application/pdf",
    headers={
        "Content-Disposition": f'attachment; filename="Facture-{invoice.number}.pdf"'
    }
)

###_________________---- POST ----_________________###

@router.post("/", response_model=CompanyResponse)
async def create_company(
        data: CompanyCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        ):
    logger = logging.getLogger("companies")

    """ res = await db.execute(
        select(Company).where(
            Company.user_id == current_user.id
        ))
    
    company = res.scalars().all()

    if company :
        raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A company already exists for this user."
    )"""

    try:
        company = Company(
            **data.model_dump(),
            siren = data.siret[:9],
            user_id=current_user.id
        )

        db.add(company)
        await db.flush()

        counter = InvoiceCounter(
            company_id=company.id
        )
        db.add(counter)
        await db.commit()
        await db.refresh(company)
        
        logger.info(
        "company_created",
            extra={
                "company_id": company.id,
                "company_name": company.name,
            },
        )

        return company
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create company")
        sentry_sdk.capture_exception(e)
        raise

@router.post("/{company_id}/clients", response_model=ClientResponse)
async def create_client(
    data: ClientCreate,
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    logger = logging.getLogger("Customer")

    try:
        client = Client(
            **data.model_dump(),
            user_id=current_user.id,
            company_id=company_id
        )

        db.add(client)
        await db.commit()
        await db.refresh(client)
        
        logger.info("customer_created",
                    extra={
                        "customer_id":client.id,
                        "customer_name":client.name,
                        "comapny_id":client.company_id

                    })
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create customer")
        sentry_sdk.capture_exception(e)
        raise

    return client

@router.post("/{company_id}/clients/{client_id}/invoices", response_model=InvoiceCreateResponse)
async def create_invoice(
    company_id: int,
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    logger = logging.getLogger("Invoice")
    res = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id
        ).with_for_update()    )
    company = res.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )
    
    client = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.company_id == company_id
        )
    )
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    try:
        next_invoice_number = await generate_invoice_number(db,company)

        invoice = Invoice(
            company_id=company_id,
            customer_id=client_id,
            number=next_invoice_number,
            issue_date=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            status_id=1
        )

        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        set_user_context(current_user)
    
        logger.info("Invoice created")

        return invoice
    

    except IntegrityError as ie:
        await db.rollback()
        logger.exception("Failed invoice number conflict")
        sentry_sdk.capture_exception(ie)
        raise HTTPException(
            status_code=409,
            detail="Invoice number conflict"
        )
    except Exception as e :
        await db.rollback()
        logger.exception("Failed to create invoice")
        sentry_sdk.capture_exception(e)

@router.post("/{company_id}/clients/{client_id}/invoices/{invoice_id}/invoicelines", response_model=list[InvoiceLineResponse])
async def create_invoice_lines_clients_company(
    company_id: int,
    client_id: int,
    invoice_id: int,
    data: list[InvoiceLineCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    logger = logging.getLogger("InvoiceLine")

    res = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id
        ).with_for_update()    )
    company = res.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )
    
    client = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.company_id == company_id
        )
    )
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    invoice = await db.execute(select(Invoice).where(Invoice.id == invoice_id,Invoice.customer_id == client_id))

    invoice = invoice.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée")
    
    try:
        invoicelines: list[InvoiceLine] = []
        for line in data:
            invoice_line = InvoiceLine(
            invoice_id=line.invoice_id,
            description=line.description,
            quantity=line.quantity,
            unit_price_ht=line.unit_price_ht,
            vat_rate=line.vat_rate,
            total_ht=line.total_ht,
            total_ttc=line.total_ttc,
            total_vat=line.total_vat,
            )

            db.add(invoice_line)
            invoicelines.append(invoice_line)

        await db.commit()

        for line in invoicelines:
            db.refresh(line)

        return invoicelines
    

    except Exception as e:
        await db.rollback()
        logger.exception("Failed to create invoice lines",extra={
            "data":data
        })
        sentry_sdk.capture_exception(e)
###_______________---- PUT ----_______________###

@router.put("/{company_id}/clients/{client_id}/invoices/{invoice_id}", response_model=InvoiceResponse)
async def modify_invoice(
    company_id: int,
    client_id: int,
    invoice_id: int,
    data: InvoiceUpdateTotal,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.company_id == company_id,
            Client.user_id == current_user.id
        )
    )

    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.company_id == company_id,
            Invoice.customer_id == client_id,
        )
    )

    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )
    invoice.subtotal_ht = data.total_ht
    invoice.total_vat = data.total_vat
    invoice.total_ttc = data.total_ttc

    db.commit()
    return invoice



@router.put("/{company_id}/clients/{client_id}/invoices/{invoice_id}/invoicelines", response_model=list[InvoiceLineResponse])
async def modify_invoice_lines_clients_company(
    company_id: int,
    client_id: int,
    invoice_id: int,
    data: list[InvoiceLineModify],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.company_id == company_id,
            Client.user_id == current_user.id
        )
    )

    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.company_id == company_id,
            Invoice.customer_id == client_id,
        )
    )

    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )
    
    result = await db.execute(
    select(InvoiceLine).where(
        InvoiceLine.invoice_id == invoice.id
    )
    )

    existing_lines = {line.id: line for line in result.scalars().all()}

    try:
        invoicelines: list[InvoiceLine] = []
        for line in data:

            invoice_line = existing_lines[line.id]
            
            invoice_line.description = line.description
            invoice_line.quantity = line.quantity
            invoice_line.unit_price_ht = line.unit_price_ht
            invoice_line.vat_rate = line.vat_rate
            invoice_line.total_ht = line.total_ht
            invoice_line.total_vat = line.total_vat
            invoice_line.total_ttc = line.total_ttc

            invoicelines.append(invoice_line)

        await db.commit()

        for line in invoicelines:
            db.refresh(line)

        return invoicelines
    

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Invoice number conflict"
        )

@router.put("/{company_id}/clients/{client_id}/invoices/{invoice_id}/status/{code}", response_model=InvoiceResponse)
async def change_status_invoice(
    company_id: int,
    client_id: int,
    invoice_id:int,
    code:str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    res = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id
        ).with_for_update()    )
    company = res.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )
    
    client = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.company_id == company_id
        )
    )
    client = client.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    invoice = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.company_id == company_id,
            Invoice.customer_id == client_id
        )
    )

    invoice = invoice.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    status = await db.execute(select(InvoiceStatus).where(InvoiceStatus.code==code))

    status = status.scalar_one_or_none()

    if not status:
        raise HTTPException(status_code=404, detail="Status not found")

    invoice.status_id = status.id

    await db.commit()
    await db.refresh(invoice)

    return invoice

@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
        company_id: int,
        data: CompanyUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        ):

    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id
        )
    )

    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(company, key, value)

    await db.commit()
    await db.refresh(company)

    return company


###_______________---- DELETE ----_______________###

@router.delete("/{company_id}/clients/{client_id}/invoices/{invoice_id}/invoicelines{invoiceLine_id}", response_model=list[InvoiceLineResponse])
async def delete_company(
        company_id: int,
            client_id: int,
            invoice_id: int,
            invoiceLine_id: int,
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
            ):

    logger = logging.getLogger("InvoiceLine")

    result = await db.execute(
           select(Company).where(
               Company.id == company_id,
               Company.user_id == current_user.id
           )
       )
   
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.company_id == company_id,
            Client.user_id == current_user.id
        )
    )

    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.company_id == company_id,
            Invoice.customer_id == client_id,
        )
    )

    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )
    
    result = await db.execute(
    select(InvoiceLine).where(
        InvoiceLine.invoice_id == invoice.id,
        InvoiceLine.id == invoiceLine_id
    )
    )

    invoice_line = result.scalar_one_or_none()

    if(not invoice_line):
        raise HTTPException(
            status_code=404,
            detail="Invoice line not found"
        )
    await db.delete(invoice_line)
    await db.commit()
    
    logger.info("Company_désactive", extra={"company_id":company_id,"company_name":company.name})

    return {"message": "Company deleted"}


@router.delete("/{company_id}")
async def delete_company(
        company_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):

    logger = logging.getLogger("companies")

    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == current_user.id
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found"
        )

    company.is_active = False
    await db.commit()

    set_user_context(current_user)
    
    logger.info("Company_désactive", extra={"company_id":company_id,"company_name":company.name})
    return {"message": "Company deleted"}


#------------------------------------------------------------
async def generate_invoice_number(db:AsyncSession,company:Company) -> str:
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(InvoiceCounter)
            .where(InvoiceCounter.company_id == company.id)
        )

        

        counter = result.scalar_one()
        print(counter)
        if company.invoice_reset_yearly and company.last_invoice_year != now.year:
            counter.last_number = 0
            
        counter.last_number += 1
        next_number = counter.last_number

        print(next_number)
       

        invoice_number = company.invoice_pattern.format(
            year=now.year,
            month=f"{now.month:02d}",
            day=f"{now.day:02d}",
            sequence=next_number,
        )
        print(invoice_number)

        return invoice_number