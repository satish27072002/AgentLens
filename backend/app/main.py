"""
AgentLens Backend — FastAPI application entry point.

This file:
1. Creates the FastAPI app
2. Adds CORS middleware (so the React frontend can call the API)
3. Creates database tables on startup
4. Includes all route modules (auth, keys, traces, executions, stats)
5. Provides a /health endpoint for quick checks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import engine, Base
from app.routes import auth_routes, keys, traces, executions, stats

# Create the FastAPI application
app = FastAPI(
    title="AgentLens",
    description="Open-source observability for AI agents. See what your agents actually do.",
    version="0.2.0",
)

# CORS middleware — allows the frontend (running on a different port) to call this API.
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
