from fastapi import Depends, HTTPException, Cookie, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi.security import (
HTTPBearer,
HTTPAuthorizationCredentials
)
from app.middleware.request_context import (
    user_ctx,
)
import sentry_sdk

from app.core.database import get_db
from app.models.user import User
from app.services.auth import decode_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié",
        )
    token = credentials.credentials
    user_id = decode_token(token)
    result  = await db.execute(select(User).where(User.id == user_id))
    user    = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
        )
    return user

def set_user_context(user):
    user_ctx.set(user.id)

    sentry_sdk.set_user({
        "id": str(user.id),
        "email": user.email,
    })