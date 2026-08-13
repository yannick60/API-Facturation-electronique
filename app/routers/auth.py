from fastapi import APIRouter, Depends, Response, Cookie, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.user import ( GoogleAuthRequest ) 
from app.services.google_service import ( verify_google_token )

from app.core.database import get_db
from app.core.dependencies import get_current_user, set_user_context
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.core.security import verify_email_token
from app.services.auth import (
    create_user, get_user_by_email, verify_password,
    create_access_token, create_refresh_token, decode_token,
)

from app.models.user import User

import os

from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth

import logging

logger = logging.getLogger("Authentification")

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth = OAuth()

# ── Inscription ──────────────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, body.email, body.password)
    set_user_context(user)
    
    logger.info("Création du User ok")
    return user

@router.get("/verify-email") 
async def verify_email( token: str, db: Session = Depends(get_db) ): 
    email = verify_email_token(token) 
    if not email: 
        raise HTTPException( status_code=400, detail="Token invalide" ) 
    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()
    if not user: 
        raise HTTPException( status_code=404, detail="Utilisateur introuvable" ) 
    user.is_verified = True 

    set_user_context(user)
    
    logger.info("Utilisateur vérifié")

    db.commit() 
    return { "message": "Email vérifié" }

@router.post('/google') 
async def google_auth( payload: GoogleAuthRequest,response: Response, db: Session = Depends(get_db) ): 
    google_user = verify_google_token( payload.token ) 
    email = google_user["email"] 
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user: 
        user = User( email=email, firstname=google_user[ "first_name" ],lastname=google_user[ "last_name" ], hashed_password="GOOGLE_AUTH", is_verified=True, ) 
        db.add(user) 
        db.commit() 
        db.refresh(user) 
    
    refresh_token = create_refresh_token(user.id)

    response.set_cookie(
        key="refresh_token", value=refresh_token,
        httponly=True, secure=False, samesite="lax",
        max_age=60 * 60 * 24 * 7,   # 7 jours
    )
        
    access_token = create_access_token( user_id=user.id ) 
    print("Access token créé :", access_token)

    set_user_context(user)
    
    logger.info("Authentification google ok")

    return { "access_token": access_token, "token_type": "bearer" ,
                "user": {
                    "id": user.id,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "email": user.email,
                }
            }

@router.get("/google/callback")
async def auth_google_callback(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)

    user_info = token["userinfo"]

    email = user_info["email"]
    name = user_info["name"]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email, name=name, is_verified=True)
        db.add(user)
        await db.commit()

    set_user_context(user)
    
    logger.info("Authentification google ok")

    access_token  = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    response.set_cookie(
        key="refresh_token", value=refresh_token,
        httponly=True, secure=False, samesite="lax",
        max_age=60 * 60 * 24 * 7,   # 7 jours
    )

    return {"access_token": access_token,"token_type": "bearer",
                "user": {
                    "id": user.id,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "email": user.email,
                }
            }

# ── Connexion ────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, body.email)

    if not user or not verify_password(body.password, user.hashed_password) or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
        )

    access_token  = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    set_user_context(user)
    
    logger.info("Authentification email/mdp ok")

    # Refresh token en cookie HttpOnly — jamais accessible en JS
    response.set_cookie(
        key="refresh_token", value=refresh_token,
        httponly=True, secure=False, samesite="lax",
        max_age=60 * 60 * 24 * 7,   
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False, # True en prod HTTPS
        samesite="lax",
    )

    return {"access_token": access_token,
                "user": {
                    "id": user.id,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "email": user.email,
                }
            }

# ── Refresh silencieux ───────────────────────────────────────────
@router.post("/token/refresh", response_model=TokenResponse)
async def refresh(request: Request,response: Response, refresh_token: str = Cookie(None)):
    print("Cookies reçus :", request.cookies)
    print("Refresh token :", refresh_token)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token manquant")

    user_id      = decode_token(refresh_token)
    access_token = create_access_token(user_id)
    new_refresh  = create_refresh_token(user_id)

    response.set_cookie(
        key="refresh_token", value=new_refresh,
        httponly=True, secure=False, samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {"access_token": access_token}

# ── Profil utilisateur connecté ──────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

# ── Déconnexion ──────────────────────────────────────────────────
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Déconnecté"}

# _________ test pdp _________________________
@router.get("/pdp")
async def pdp(response: Response):
    return get_token()

@router.get("/pdp/factures")
async def pdp(response: Response):
    return get_factures()

@router.get("/pdp/authorize")
async def pdp(response: Response):
    return get_authorize()

