from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_token_payload, get_current_user, get_db
from app.models.user import User
from app.schemas.auth import AuthUserResponse, RegisterProfileRequest, TokenPayload, UpdateRoleRequest
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register-profile", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
def register_profile(
    req: RegisterProfileRequest,
    token: TokenPayload = Depends(get_current_token_payload),
    db: Session = Depends(get_db),
):
    """
    Onboards a newly authenticated Supabase user by linking their Supabase Auth ID
    with an application User profile and role (Farmer, FPO, or Buyer).
    """
    user = auth_service.register_user_profile(
        db=db,
        auth_user_id=token.sub,
        token_email=token.email,
        token_phone=req.phone,
        req=req,
    )
    return auth_service.get_user_full_profile(db, user)


@router.get("/me", response_model=AuthUserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the authenticated user's profile and active role."""
    return auth_service.get_user_full_profile(db, current_user)


@router.put("/role", response_model=AuthUserResponse)
def update_user_role(
    req: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates the user's role and account profile details."""
    updated_user = auth_service.update_user_role(db, current_user, req.role)
    return auth_service.get_user_full_profile(db, updated_user)

