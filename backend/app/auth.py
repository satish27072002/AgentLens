"""
Authentication utilities — JWT tokens and password hashing.

Two concepts:
1. Password hashing (bcrypt): Converts "mypassword" → "$2b$12$..." (irreversible).
   We store the hash, never the plain password. On login, we hash the input
   and compare hashes.

2. JWT tokens: A signed JSON payload like {"user_id": "abc", "exp": 1234567890}.
   The server signs it with JWT_SECRET. The frontend stores it and sends it
   back on every request. The server verifies the signature to trust the payload.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_HOURS


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt. Used during signup."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain-text password matches the stored hash. Used during login."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_jwt_token(user_id: str) -> str:
    """
    Create a JWT token containing the user's ID.

    The token expires after JWT_EXPIRE_HOURS (default: 24 hours).
    The frontend stores this and sends it in the Authorization header.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,      # "sub" (subject) is the standard JWT claim for the user ID
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> str | None:
    """
    Decode a JWT token and return the user_id.

    Returns None if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def generate_api_key() -> str:
    """
    Generate a new API key with the "al_" prefix.

    Example output: "al_k7x9m2abcDEF123ghiJKL456"

    The "al_" prefix is a common pattern (Stripe uses "sk_", OpenAI uses "sk-").
    It helps developers identify which service a key belongs to.
    """
    random_part = secrets.token_urlsafe(24)
    return f"al_{random_part}"
