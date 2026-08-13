from google.oauth2 import id_token

from google.auth.transport import requests

from app.core.config import settings


def verify_google_token(token: str):

    idinfo = id_token.verify_oauth2_token(

        token,

        requests.Request(),
        
        settings.GOOGLE_CLIENT_ID
    )
    #print(idinfo)

    return {
        "email": idinfo["email"],
        "first_name": idinfo.get("given_name"), 
        "last_name": idinfo.get("family_name"),
    }

