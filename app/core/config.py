from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL:                   str
    SECRET_KEY:                     str
    ALGORITHM:                      str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES:    int = 15
    REFRESH_TOKEN_EXPIRE_DAYS:      int = 7
    MAIL_USERNAME:                  str 
    MAIL_PASSWORD:                  str 
    MAIL_FROM:                      str 
    MAIL_PORT:                      int 
    MAIL_SERVER:                    str 
    MAIL_FROM_NAME:                 str 
    FRONTEND_URL:                   str
    GOOGLE_CLIENT_ID:               str
    GOOGLE_CLIENT_SECRET:           str
    GOOGLE_REDIRECT_URI:            str
    SECRET_PDP:                     str
    SECRET_PDP_TEST:                str
    ID_PDP:                         str
    ID_PDP_TEST:                    str
    PDP_URL:                        str
    SENTRY_DSN:                     str
 

    class Config:
        env_file = ".env"

settings = Settings()