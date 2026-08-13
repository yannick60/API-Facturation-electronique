
from datetime import datetime, timedelta, UTC
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


def create_email_token(email: str):
    expire = datetime.now(UTC) + timedelta(hours=24)

    payload = {
        "sub": email,
        "exp": expire,
        "type": "email_verification"
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_email_token(token: str):
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )

    if payload.get("type") != "email_verification":
        return None

    return payload.get("sub")

