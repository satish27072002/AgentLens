"""
AgentLens Backend — FastAPI application entry point.

This file:
1. Creates the FastAPI app
2. Adds CORS middleware (so the React frontend can call the API)
3. Adds request logging middleware (correlation IDs, structured logs)
4. Creates database tables on startup
5. Includes all route modules (auth, keys, traces, executions, stats)
6. Provides a /health endpoint for quick checks
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import engine, Base
from app.routes import auth_routes, keys, traces, executions, stats
from app.middleware.request_logging import RequestLoggingMiddleware

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Create the FastAPI application
app = FastAPI(
    title="AgentLens",
    description="Open-source observability for AI agents. See what your agents actually do.",
    version="0.2.0",
)

# Middleware (order matters — first added = outermost)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup.
Base.metadata.create_all(bind=engine)

# Include route modules
app.include_router(auth_routes.router, tags=["Auth"])
app.include_router(keys.router, tags=["API Keys"])
app.include_router(traces.router, tags=["Traces"])
app.include_router(executions.router, tags=["Executions"])
app.include_router(stats.router, tags=["Stats"])


@app.get("/health")
def health_check():
    """Simple health check — returns 200 if the server is running."""
    return {"status": "ok", "service": "agentlens-backend"}
