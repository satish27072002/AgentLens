"""
Auth0 JWT verification.

HOW IT WORKS:
1. Auth0 signs tokens with RS256 (asymmetric). The private key stays at Auth0,
   the public key is published at /.well-known/jwks.json.
2. When a request comes in with a Bearer token, we:
   a. Decode the token header to find which key was used (the "kid" field)
   b. Fetch Auth0's public keys (JWKS) and find the matching key
   c. Verify the token signature with that public key
   d. Check that the token is for our API (audience) and not expired
3. If valid, we extract the "sub" claim — this is the user's unique Auth0 ID
   (e.g., "auth0|abc123" or "google-oauth2|12345").

WHY RS256 instead of HS256?
- HS256: Both sides share the same secret. If the secret leaks, anyone can forge tokens.
- RS256: Auth0 holds the private key. We only need the public key to verify.
  Even if our server is compromised, attackers can't create new tokens.
"""

import jwt
import httpx
from functools import lru_cache

from app.config import AUTH0_AUDIENCE, AUTH0_ISSUER, AUTH0_JWKS_URL


class Auth0Error(Exception):
    """Raised when Auth0 token verification fails."""

    pass


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """
    Fetch Auth0's public signing keys (JWKS = JSON Web Key Set).

    Cached with lru_cache so we don't fetch on every request.
    The keys rarely change (Auth0 rotates them every ~year).

    In production, you'd add a TTL cache. For our project, lru_cache is fine.
    """
    response = httpx.get(AUTH0_JWKS_URL, timeout=10)
    response.raise_for_status()
    return response.json()


def _get_signing_key(token: str) -> dict:
    """
    Find the correct public key for this specific token.

    JWT header contains "kid" (Key ID) — tells us which key was used to sign it.
    We match this against the keys published at Auth0's JWKS endpoint.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError:
        raise Auth0Error("Invalid token format")

    jwks = _get_jwks()

    for key in jwks.get("keys", []):
        if key["kid"] == unverified_header.get("kid"):
            return key

    # If we don't find the key, Auth0 might have rotated keys.
    # Clear cache and try once more.
    _get_jwks.cache_clear()
    jwks = _get_jwks()

    for key in jwks.get("keys", []):
        if key["kid"] == unverified_header.get("kid"):
            return key

    raise Auth0Error(
        "Unable to find signing key — Auth0 key rotation may be in progress"
    )


def verify_auth0_token(token: str) -> dict:
    """
    Verify an Auth0-issued JWT and return the decoded payload.

    Returns a dict like:
    {
        "sub": "auth0|abc123",       # The user's unique Auth0 ID
        "email": "user@example.com", # If email scope was requested
        "name": "John Doe",          # If profile scope was requested
        ...
    }

    Raises Auth0Error if the token is invalid, expired, or not for our API.
    """
    signing_key = _get_signing_key(token)

    try:
        # Build the RSA public key from the JWK
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(signing_key)

        # Decode and verify the token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=AUTH0_ISSUER,
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise Auth0Error("Token has expired")
    except jwt.InvalidAudienceError:
        raise Auth0Error("Token audience doesn't match — check AUTH0_AUDIENCE config")
    except jwt.InvalidIssuerError:
        raise Auth0Error("Token issuer doesn't match — check AUTH0_DOMAIN config")
    except jwt.PyJWTError as e:
        raise Auth0Error(f"Token verification failed: {str(e)}")
