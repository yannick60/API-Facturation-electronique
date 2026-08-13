from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, company, vat_settings, client, invoice, pdp
import app.models
from app.core.logging_config import setup_logging
from app.core.sentry import init_sentry
from app.middleware.request_context import RequestContextMiddleware

setup_logging()
init_sentry()

app = FastAPI(title="Facture-moi API")

app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_credentials=True,                    
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(company.router, prefix="/api")
app.include_router(vat_settings.router, prefix="/api")
app.include_router(client.router, prefix="/api")
app.include_router(invoice.router, prefix="/api")
app.include_router(pdp.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}