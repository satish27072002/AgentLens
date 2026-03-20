"""
FastAPI dependencies for authentication.

Dependencies are functions that FastAPI calls before your route handler.
They extract and validate credentials, then pass the result to your route.

Two auth mechanisms:
1. JWT Token (for frontend/dashboard): "Authorization: Bearer <token>"
2. API Key (for SDK/telemetry): "X-API-Key: al_..."

Both resolve to a user_id. The difference is HOW the user_id is determined.
"""

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import decode_jwt_token
from app.models import User, ApiKey


def get_current_user(
    authorization: str = Header(..., description="Bearer JWT token"),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency for frontend routes — extracts user from JWT token.

    The frontend sends: Authorization: Bearer eyJhbGciOi...
    We decode the JWT, find the user in the database, and return them.

    Usage in a route:
        @router.get("/something")
        def get_something(user: User = Depends(get_current_user)):
            # user is guaranteed to be a valid, logged-in user
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]  # Strip "Bearer " prefix
    user_id = decode_jwt_token(token)

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_user_from_api_key(
    x_api_key: str = Header(..., description="AgentLens API key (al_...)"),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency for SDK routes — extracts user from API key.

    The SDK sends: X-API-Key: al_k7x9m2abc123
    We look up the key in the api_keys table, find the user, and return them.

    Usage in a route:
        @router.post("/api/traces")
        def create_trace(user: User = Depends(get_user_from_api_key)):
            # user is the developer who owns this API key
    """
    api_key = db.query(ApiKey).filter(
        ApiKey.key_value == x_api_key,
        ApiKey.is_active == True,
    ).first()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    return api_key.user
