from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import get_current_user

from app.core.database import get_db
from app.models.company import VatSetting

router = APIRouter(prefix="/vat", tags=["vat_settings"])

@router.get("/")
async def get_vat_settings(
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(VatSetting).where(
            VatSetting.is_active == True
        )
    )

    vat_settings = result.scalars().all()

    return vat_settings