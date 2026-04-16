from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # skip CSP for docs
        if request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            return response

        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        return response
