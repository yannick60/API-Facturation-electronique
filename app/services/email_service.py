
from fastapi_mail import FastMail, MessageSchema

from app.core.mail import mail_config
from app.core.security import create_email_token

import os

FRONTEND_URL = os.getenv("FRONTEND_URL")


async def send_verification_email(email: str):

    token = create_email_token(email)

    verification_link = (
        f"{FRONTEND_URL}/verify-email?token={token}"
    )

    html = f"""
    <h1>Bienvenue sur Facture Moi</h1>

    <p>
        Cliquez sur le bouton ci-dessous
        pour vérifier votre email.
    </p>

    <a href="{verification_link}">
        Vérifier mon email
    </a>
    """

    message = MessageSchema(
        subject="Vérification email",
        recipients=[email],
        body=html,
        subtype="html"
    )

    fm = FastMail(mail_config)

    await fm.send_message(message)
