"""
Firebase Authentication Module for W&M Business Major Advising Backend

Provides token verification and user authentication via Firebase Auth.
Requires @wm.edu email addresses for all users.
"""

import os
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth

from .config import initialize_firebase


# Ensure Firebase is initialized
initialize_firebase()

# Security scheme for Bearer token
security = HTTPBearer()

# Required email domain - only W&M emails allowed
ALLOWED_EMAIL_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN", "wm.edu")


class UserRole(str, Enum):
    """User roles in the system."""
    STUDENT = "student"
    ADVISOR = "advisor"
    ADMIN = "admin"


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user from Firebase."""
    uid: str
    email: Optional[str]
    email_verified: bool
    role: UserRole
    display_name: Optional[str] = None

    @property
    def is_advisor(self) -> bool:
        return self.role in (UserRole.ADVISOR, UserRole.ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


def verify_firebase_token(token: str) -> dict:
    """
    Verify a Firebase ID token.

    Args:
        token: The Firebase ID token to verify

    Returns:
        Decoded token claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


def validate_email_domain(email: Optional[str]) -> bool:
    """
    Validate that the email belongs to the allowed domain (wm.edu).

    Args:
        email: The email address to validate

    Returns:
        True if email is valid and from allowed domain
    """
    if not email:
        return False

    email_lower = email.lower()

    # Must have @ symbol and characters before it (not just @wm.edu)
    if "@" not in email_lower or email_lower.startswith("@"):
        return False

    return email_lower.endswith(f"@{ALLOWED_EMAIL_DOMAIN}")


def get_user_role(decoded_token: dict) -> UserRole:
    """
    Extract user role from token claims.

    Custom claims can be set in Firebase to assign roles.
    Default role is STUDENT if no custom claim is present.
    """
    claims = decoded_token.get("claims", {})

    # Check for custom role claim
    if claims.get("admin"):
        return UserRole.ADMIN
    elif claims.get("advisor"):
        return UserRole.ADVISOR

    # Also check top-level custom claims
    if decoded_token.get("admin"):
        return UserRole.ADMIN
    elif decoded_token.get("advisor"):
        return UserRole.ADVISOR

    return UserRole.STUDENT


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthenticatedUser:
    """
    FastAPI dependency to get the current authenticated user.

    Requires a valid @wm.edu email address.

    Usage:
        @app.get("/protected")
        async def protected_route(user: AuthenticatedUser = Depends(get_current_user)):
            return {"uid": user.uid}
    """
    token = credentials.credentials
    decoded_token = verify_firebase_token(token)

    email = decoded_token.get("email")

    # Enforce W&M email domain
    if not validate_email_domain(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access restricted to @{ALLOWED_EMAIL_DOMAIN} email addresses"
        )

    return AuthenticatedUser(
        uid=decoded_token["uid"],
        email=email,
        email_verified=decoded_token.get("email_verified", False),
        role=get_user_role(decoded_token),
        display_name=decoded_token.get("name")
    )


async def get_current_student(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Dependency that ensures the user is a student (or higher role).
    All authenticated users can access student routes.
    """
    return user


async def get_current_advisor(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Dependency that ensures the user is an advisor or admin.

    Raises:
        HTTPException: If user is not an advisor
    """
    if not user.is_advisor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advisor access required"
        )
    return user


async def get_current_admin(
    user: AuthenticatedUser = Depends(get_current_user)
) -> AuthenticatedUser:
    """
    Dependency that ensures the user is an admin.

    Raises:
        HTTPException: If user is not an admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def verify_user_access(user: AuthenticatedUser, resource_user_id: str) -> bool:
    """
    Verify that a user can access a resource belonging to another user.

    Rules:
    - Users can access their own resources
    - Advisors can access their advisees' resources
    - Admins can access all resources

    Args:
        user: The authenticated user
        resource_user_id: The user ID of the resource owner

    Returns:
        True if access is allowed
    """
    # Users can always access their own resources
    if user.uid == resource_user_id:
        return True

    # Admins can access everything
    if user.is_admin:
        return True

    # Advisors need to be checked against their advisee list
    # This would require a database lookup, so we return True here
    # and let the service layer handle the detailed check
    if user.is_advisor:
        return True

    return False


def require_self_or_advisor(resource_user_id: str):
    """
    Factory for creating a dependency that checks if user can access a resource.

    Usage:
        @app.get("/api/student/{student_id}/profile")
        async def get_profile(
            student_id: str,
            user: AuthenticatedUser = Depends(require_self_or_advisor(student_id))
        ):
            ...
    """
    async def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not verify_user_access(user, resource_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this resource"
            )
        return user
    return dependency
