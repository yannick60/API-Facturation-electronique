import os

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def init_sentry():
    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.2,
        send_default_pii=False,
        environment=os.getenv("ENVIRONMENT", "development"),
    )