from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import get_current_user

from app.core.database import get_db
from app.models.user import  User
from app.schemas.client import ClientCreate, ClientResponse
from app.models.client import Client
router = APIRouter(prefix="/clients", tags=["Client"])

@router.get("/" , response_model=list[ClientResponse]  )
async def get_clients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ):

    result = await db.execute(
        select(Client).where(
            Client.user_id == current_user.id
        )
    )

    clients = result.scalars().all()

    if not clients:
        raise HTTPException(
            status_code=404,
            detail="No Clients found"
        )

    return clients

