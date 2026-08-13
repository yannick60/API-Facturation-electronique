from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import get_current_user

from app.core.database import get_db

from app.models.company import Company
from app.models.user import  User
from app.models.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.schemas.invoice import InvoiceResponse, InvoiceStatusResponse

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.get("/" , response_model=list[InvoiceResponse]  )
async def get_invoices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Invoice)
        .join(Invoice.company)
        .where(
            Company.user_id == current_user.id,
        )
    )

    invoices = result.scalars().all()
    print(f"invoices: {invoices}")
    if not invoices:
        raise HTTPException(
            status_code=404,
            detail="No Invoices found"
        )

    return invoices

@router.get("/status", response_model=list[InvoiceStatusResponse])
async def get_invoice_statuses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(InvoiceStatus)
    )

    statuses = result.scalars().all()

    if not statuses:
        raise HTTPException(
            status_code=404,
            detail="No Invoice Statuses found"
        )

    return statuses

@router.get("/status/{code}", response_model=InvoiceStatusResponse)
async def get_invoice_statuses(
    code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(InvoiceStatus).where(InvoiceStatus==code)
    )

    statuses = result.scalar_one_or_none()

    if not statuses:
        raise HTTPException(
            status_code=404,
            detail="No Invoice Statuses found"
        )

    return statuses
