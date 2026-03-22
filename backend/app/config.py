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

# JWT Authentication (legacy — kept for API key generation and backward compatibility)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Auth0 Configuration
# The backend validates JWTs issued by Auth0 (RS256 algorithm).
# AUTH0_DOMAIN: Your Auth0 tenant (e.g., "dev-xxxxx.us.auth0.com")
# AUTH0_AUDIENCE: The API identifier you created in Auth0 dashboard
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "dev-f40hclgqhiimob42.us.auth0.com")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://api.agentlens.dev")
AUTH0_ISSUER = f"https://{AUTH0_DOMAIN}/"
AUTH0_JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
