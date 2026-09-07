from typing import Optional, Tuple
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.security import verify_auth_token
from app.models.buyer import BuyerProfile
from app.models.farmer import FarmerProfile
from app.models.fpo import FPOProfile
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.utils.enums import UserRole

bearer_security = HTTPBearer(auto_error=False)


def get_current_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_security),
) -> TokenPayload:
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Authorization token missing")

    token = credentials.credentials
    try:
        payload = verify_auth_token(token)
        return TokenPayload(
            sub=payload["sub"],
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
            exp=payload.get("exp"),
        )
    except Exception:
        raise UnauthorizedException("Invalid authentication token")


def get_current_user(
    db: Session = Depends(get_db),
    token_payload: TokenPayload = Depends(get_current_token_payload),
) -> User:
    user = db.query(User).filter(User.auth_user_id == token_payload.sub).first()
    if not user:
        raise UnauthorizedException("User profile not registered")
    return user


def get_current_farmer(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.FARMER and current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Access restricted to registered Farmers.")
    return current_user


def get_current_fpo(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.FPO and current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Access restricted to registered FPOs.")
    return current_user


def get_current_buyer(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.BUYER and current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Access restricted to registered Buyers.")
    return current_user


def get_current_seller(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in [UserRole.FARMER, UserRole.FPO, UserRole.ADMIN]:
        raise ForbiddenException("Access restricted to sellers (Farmers or FPOs).")
    return current_user
