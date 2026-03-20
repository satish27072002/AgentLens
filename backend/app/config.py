"""
Application configuration.

Uses environment variables with sensible defaults for local development.
In production, set DATABASE_URL to a PostgreSQL connection string.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Database: SQLite for dev, PostgreSQL for prod
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentlens.db")

# CORS: Allow frontend origins
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# JWT Authentication
# In production, set JWT_SECRET to a strong random string.
# Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
