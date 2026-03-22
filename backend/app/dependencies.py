"""
FastAPI dependencies for authentication.

Dependencies are functions that FastAPI calls before your route handler.
They extract and validate credentials, then pass the result to your route.

Two auth mechanisms:
1. Auth0 JWT (for frontend/dashboard): "Authorization: Bearer <token>"
   - Token is issued by Auth0, verified using Auth0's public keys (RS256)
   - On first login, auto-creates a local User + first API key (JIT provisioning)
2. API Key (for SDK/telemetry): "X-API-Key: al_..."
   - Unchanged from before — the SDK sends API keys, not Auth0 tokens
"""

import uuid

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ApiKey
from app.auth0 import verify_auth0_token, Auth0Error
from app.auth import generate_api_key


def get_current_user(
    authorization: str = Header(..., description="Bearer Auth0 JWT token"),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency for frontend routes — extracts user from Auth0 JWT.

    Flow:
    1. Extract the Bearer token from the Authorization header
    2. Verify it with Auth0's public keys (RS256)
    3. Look up the user by auth0_sub (their Auth0 ID)
    4. If first login → auto-create user + API key (JIT provisioning)
    5. Return the User object

    JIT (Just-In-Time) Provisioning:
    Instead of a separate signup step, we create the user record automatically
    the first time they hit any protected endpoint. This is standard practice
    with external auth providers (Auth0, Firebase, Clerk, etc.).
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]  # Strip "Bearer " prefix

    # Verify the token with Auth0
    try:
        payload = verify_auth0_token(token)
    except Auth0Error as e:
        raise HTTPException(status_code=401, detail=str(e))

    auth0_sub = payload.get("sub")
    if not auth0_sub:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    # Look up existing user by Auth0 ID
    user = db.query(User).filter(User.auth0_sub == auth0_sub).first()

    if not user:
        # JIT Provisioning — first login, create the user automatically
        email = payload.get("email", f"{auth0_sub}@auth0.user")
        name = payload.get("name")

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            auth0_sub=auth0_sub,
            name=name,
        )
        db.add(user)

        # Auto-generate first API key (same as old signup flow)
        api_key = ApiKey(
            id=str(uuid.uuid4()),
            user_id=user.id,
            key_value=generate_api_key(),
            name="Default",
        )
        db.add(api_key)
        db.commit()
        db.refresh(user)

    return user


def get_user_from_api_key(
    x_api_key: str = Header(..., description="AgentLens API key (al_...)"),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency for SDK routes — extracts user from API key.

    The SDK sends: X-API-Key: al_k7x9m2abc123
    We look up the key in the api_keys table, find the user, and return them.

    This is UNCHANGED — API key auth is completely separate from Auth0.
    """
    api_key = db.query(ApiKey).filter(
        ApiKey.key_value == x_api_key,
        ApiKey.is_active == True,
    ).first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    return api_key.user
