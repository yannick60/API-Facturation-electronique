import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import contextvars

request_id_ctx = contextvars.ContextVar("request_id", default=None)
user_ctx = contextvars.ContextVar("user_id", default=None)

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        request_id_ctx.set(request_id)

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response