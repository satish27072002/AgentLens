"""
API key management routes.

POST   /api/keys           — Generate a new API key
GET    /api/keys           — List all keys (masked)
DELETE /api/keys/{key_id}  — Deactivate a key
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ApiKey
from app.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyCreatedResponse
from app.auth import generate_api_key
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/api/keys", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key(
    request: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a new API key for the current user.

    Returns the FULL key — this is the only time it's shown in full.
    After this, only the last 8 characters are visible (for security).
    """
    key_value = generate_api_key()
    api_key = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user.id,
        key_value=key_value,
        name=request.name,
    )
    db.add(api_key)
    db.commit()

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=key_value,
        created_at=api_key.created_at,
    )


@router.get("/api/keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for the current user.

    Keys are masked — only the last 8 characters are shown.
    This is a security practice: if someone sees the response,
    they can't use the keys.
    """
    keys = db.query(ApiKey).filter(ApiKey.user_id == user.id).all()

    return [
        ApiKeyResponse(
            id=key.id,
            name=key.name,
            key_preview=f"al_...{key.key_value[-8:]}",
            is_active=key.is_active,
            created_at=key.created_at,
        )
        for key in keys
    ]


@router.delete("/api/keys/{key_id}")
def delete_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate an API key.

    We don't actually delete it (so existing data references stay valid).
    We just set is_active=False, which means the SDK can no longer use it.
    """
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == user.id,
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()

    return {"status": "deleted"}
