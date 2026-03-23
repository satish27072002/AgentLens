"""
Authentication routes — user profile and first API key.

With Auth0, signup and login happen on Auth0's hosted page.
The backend only needs:
- GET /api/auth/me  — Return user profile (auto-creates on first call via JIT provisioning)
- POST /api/auth/me — Update profile with name/email from Auth0 ID token

The old POST /api/auth/signup and POST /api/auth/login are no longer needed
because Auth0 handles those flows entirely.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ApiKey
from app.schemas import UserResponse
from app.dependencies import get_current_user

router = APIRouter()


class ProfileUpdate(BaseModel):
    """Optional profile fields from Auth0 ID token (name, email, picture)."""

    name: str | None = None
    email: str | None = None


@router.get("/api/auth/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """
    Get the current user's profile.

    Requires a valid Auth0 JWT in the Authorization header.

    On first call (new user):
    - The get_current_user dependency auto-creates the user (JIT provisioning)
    - Auto-generates their first API key
    - Returns the new user profile

    On subsequent calls:
    - Simply returns the existing user profile
    """
    return user


@router.post("/api/auth/me", response_model=UserResponse)
def update_me(
    profile: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the user's profile with data from Auth0 ID token.

    The access token doesn't include name/email, but the frontend has
    that info from the ID token. This endpoint lets the frontend sync it.
    Only updates fields that are provided and different from current values.
    """
    updated = False

    if profile.name and profile.name != user.name:
        user.name = profile.name
        updated = True

    if (
        profile.email
        and not user.email.endswith("@auth0.user")
        and profile.email != user.email
    ):
        # Don't overwrite a real email with Auth0's
        pass
    elif profile.email and user.email.endswith("@auth0.user"):
        user.email = profile.email
        updated = True

    if updated:
        db.commit()
        db.refresh(user)

    return user


@router.get("/api/auth/api-key")
def get_first_api_key(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the user's first API key (for onboarding).

    After Auth0 login, the frontend redirects to /onboarding.
    This endpoint returns the full API key so the user can copy it.
    Only returns the FIRST active key — used for initial setup display.
    """
    api_key = (
        db.query(ApiKey)
        .filter(
            ApiKey.user_id == user.id,
            ApiKey.is_active.is_(True),
        )
        .first()
    )

    if not api_key:
        return {"api_key": None}

    return {"api_key": api_key.key_value}
