"""
Authentication utilities — password hashing and API key generation.

Two concepts:
1. Password hashing (bcrypt): Converts "mypassword" → "$2b$12$..." (irreversible).
   We store the hash, never the plain password. On login, we hash the input
   and compare hashes.

2. API key generation: Creates unique keys with the "al_" prefix for SDK auth.
   Auth0 handles JWT-based authentication for the frontend.
"""

import secrets

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt. Used during signup."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain-text password matches the stored hash. Used during login."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def generate_api_key() -> str:
    """
    Generate a new API key with the "al_" prefix.

    Example output: "al_k7x9m2abcDEF123ghiJKL456"

    The "al_" prefix is a common pattern (Stripe uses "sk_", OpenAI uses "sk-").
    It helps developers identify which service a key belongs to.
    """
    random_part = secrets.token_urlsafe(24)
    return f"al_{random_part}"
