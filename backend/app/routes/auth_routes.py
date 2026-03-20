"""
Authentication routes — signup, login, and profile.

POST /api/auth/signup  — Create account, get JWT + first API key
POST /api/auth/login   — Log in, get JWT
GET  /api/auth/me      — Get current user's profile (requires JWT)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, ApiKey
from app.schemas import SignupRequest, LoginRequest, AuthResponse, UserResponse
from app.auth import hash_password, verify_password, create_jwt_token, generate_api_key
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Create a new user account.

    Steps:
    1. Check email isn't already taken
    2. Hash the password (never store plain text)
    3. Create the user
    4. Auto-generate their first API key
    5. Return a JWT token + the API key

    The API key is shown only once on the onboarding page.
    The developer must copy it — we never show the full key again.
    """
    # Check for existing user
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate password length
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Create user
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
    )
    db.add(user)

    # Auto-generate first API key
    api_key_value = generate_api_key()
    api_key = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user_id,
        key_value=api_key_value,
        name="Default",
    )
    db.add(api_key)
    db.commit()

    # Generate JWT token
    token = create_jwt_token(user_id)

    return AuthResponse(
        user_id=user_id,
        token=token,
        api_key=api_key_value,
    )


@router.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Log in with email and password.

    Steps:
    1. Find user by email
    2. Verify password against stored hash
    3. Return a JWT token
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_jwt_token(user.id)

    return AuthResponse(
        user_id=user.id,
        token=token,
    )


@router.get("/api/auth/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """
    Get the current user's profile.

    Requires a valid JWT token in the Authorization header.
    Used by the frontend to check if the user is still logged in.
    """
    return user
