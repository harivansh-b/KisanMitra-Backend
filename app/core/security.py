import time
from typing import Any, Dict, Optional
import jwt
from supabase import create_client, Client

from app.core.config import settings
from app.core.exceptions import UnauthorizedException


# Initialize Supabase Admin Client
def get_supabase_admin_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def verify_supabase_token(token: str) -> Dict[str, Any]:
    """
    Validates the Supabase JWT token.
    1. First attempts local verification using SUPABASE_JWT_SECRET.
    2. Fallback to Supabase Auth API verification if secret decoding fails or isn't matching.
    """
    # 1. Local JWT decode attempt
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False, "verify_signature": True}
            )
            # Ensure subject (user ID) exists
            if not payload.get("sub"):
                raise UnauthorizedException("JWT missing subject 'sub'")
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException("Token has expired")
        except jwt.InvalidTokenError:
            pass  # Fall through to Supabase API check

    # 2. Supabase API check
    try:
        supabase = get_supabase_admin_client()
        user_res = supabase.auth.get_user(token)
        if user_res and user_res.user:
            u = user_res.user
            return {
                "sub": str(u.id),
                "email": u.email,
                "phone": u.phone,
                "user_metadata": u.user_metadata or {},
                "app_metadata": u.app_metadata or {}
            }
    except Exception as e:
        raise UnauthorizedException(f"Token verification failed: {str(e)}")

    raise UnauthorizedException("Invalid authentication credentials")


def create_test_jwt(auth_user_id: str, email: str = "test@example.com", expires_in: int = 3600) -> str:
    """Helper to generate valid JWTs for unit and integration testing."""
    secret = settings.SUPABASE_JWT_SECRET or "super-secret-jwt-key-for-local-development-and-testing-32-chars-minimum"
    payload = {
        "sub": auth_user_id,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")
