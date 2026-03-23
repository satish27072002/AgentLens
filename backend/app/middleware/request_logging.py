"""
Request logging middleware — adds correlation IDs and structured logging.

Every request gets a unique request_id (UUID) that's:
1. Attached to the request state (accessible in route handlers)
2. Returned in the X-Request-ID response header
3. Logged with the request method, path, status, and duration
"""

import time
import uuid
import logging
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("agentlens.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Adds request IDs and logs all requests with timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                json.dumps({
                    "event": "request_error",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 1),
                    "error": str(exc),
                })
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Skip logging health checks to reduce noise
        if request.url.path != "/health":
            log_data = {
                "event": "request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
            }
            if response.status_code >= 400:
                logger.warning(json.dumps(log_data))
            else:
                logger.info(json.dumps(log_data))

        return response
