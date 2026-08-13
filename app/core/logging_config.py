import logging
from logging.handlers import RotatingFileHandler
import os
import json

from app.middleware.request_context import (
    request_id_ctx,
    user_ctx,
)

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "time": self.formatTime(record),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "user_id": user_ctx.get(),
        })


def setup_logging():
    os.makedirs("logs", exist_ok=True)

    handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )

    handler.setFormatter(JsonFormatter())

    # Logger racine
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Supprime les handlers existants (uvicorn en ajoute souvent)
    root.handlers.clear()
    root.addHandler(handler)

    # Réduit le bruit
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)