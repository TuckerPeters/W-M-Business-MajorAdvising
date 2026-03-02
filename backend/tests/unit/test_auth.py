"""
Unit tests for the authentication module.

Tests email domain validation and user role checks.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.auth import (
    validate_email_domain,
    get_user_role,
    UserRole,
    AuthenticatedUser,
    ALLOWED_EMAIL_DOMAIN
)


class TestEmailDomainValidation:
    """Tests for email domain validation"""

    def test_valid_wm_edu_email(self):
        """Should accept valid @wm.edu emails"""
        assert validate_email_domain("student@wm.edu") is True
        assert validate_email_domain("john.doe@wm.edu") is True
        assert validate_email_domain("advisor123@wm.edu") is True

    def test_valid_wm_edu_email_case_insensitive(self):
        """Should accept @wm.edu emails regardless of case"""
        assert validate_email_domain("STUDENT@WM.EDU") is True
        assert validate_email_domain("Student@Wm.Edu") is True
        assert validate_email_domain("test@WM.edu") is True

    def test_invalid_non_wm_email(self):
        """Should reject non-wm.edu emails"""
        assert validate_email_domain("user@gmail.com") is False
        assert validate_email_domain("user@yahoo.com") is False
        assert validate_email_domain("user@virginia.edu") is False
        assert validate_email_domain("user@email.wm.edu") is False  # subdomain

    def test_invalid_empty_email(self):
        """Should reject empty or None emails"""
        assert validate_email_domain(None) is False
        assert validate_email_domain("") is False

    def test_invalid_malformed_email(self):
        """Should reject malformed emails"""
        assert validate_email_domain("not-an-email") is False
        assert validate_email_domain("wm.edu") is False
        assert validate_email_domain("@wm.edu") is False

    def test_similar_domain_rejected(self):
        """Should reject domains that look similar but aren't wm.edu"""
        assert validate_email_domain("user@fake-wm.edu") is False
        assert validate_email_domain("user@wmm.edu") is False
        assert validate_email_domain("user@wm.edu.fake.com") is False


class TestUserRole:
    """Tests for user role extraction from tokens"""

    def test_default_role_is_student(self):
        """Should return STUDENT role by default"""
        token = {"uid": "123", "email": "test@wm.edu"}
        assert get_user_role(token) == UserRole.STUDENT

    def test_advisor_role_from_claims(self):
        """Should recognize advisor custom claim"""
        token = {"uid": "123", "email": "test@wm.edu", "advisor": True}
        assert get_user_role(token) == UserRole.ADVISOR

    def test_admin_role_from_claims(self):
        """Should recognize admin custom claim"""
        token = {"uid": "123", "email": "test@wm.edu", "admin": True}
        assert get_user_role(token) == UserRole.ADMIN

    def test_admin_takes_precedence(self):
        """Admin claim should take precedence over advisor"""
        token = {"uid": "123", "email": "test@wm.edu", "admin": True, "advisor": True}
        assert get_user_role(token) == UserRole.ADMIN

    def test_nested_claims(self):
        """Should check nested claims object"""
        token = {"uid": "123", "claims": {"advisor": True}}
        assert get_user_role(token) == UserRole.ADVISOR


class TestAuthenticatedUser:
    """Tests for AuthenticatedUser dataclass"""

    def test_student_is_not_advisor(self):
        """Student should not have advisor access"""
        user = AuthenticatedUser(
            uid="123",
            email="student@wm.edu",
            email_verified=True,
            role=UserRole.STUDENT
        )
        assert user.is_advisor is False
        assert user.is_admin is False

    def test_advisor_has_advisor_access(self):
        """Advisor should have advisor access"""
        user = AuthenticatedUser(
            uid="123",
            email="advisor@wm.edu",
            email_verified=True,
            role=UserRole.ADVISOR
        )
        assert user.is_advisor is True
        assert user.is_admin is False

    def test_admin_has_all_access(self):
        """Admin should have both advisor and admin access"""
        user = AuthenticatedUser(
            uid="123",
            email="admin@wm.edu",
            email_verified=True,
            role=UserRole.ADMIN
        )
        assert user.is_advisor is True
        assert user.is_admin is True


class TestVerifyUserAccess:
    """Tests for user access verification"""

    def test_user_can_access_own_resource(self):
        """Users should be able to access their own resources"""
        from core.auth import verify_user_access

        user = AuthenticatedUser(
            uid="user123",
            email="test@wm.edu",
            email_verified=True,
            role=UserRole.STUDENT
        )
        assert verify_user_access(user, "user123") is True

    def test_user_cannot_access_other_resource(self):
        """Students should not access other students' resources"""
        from core.auth import verify_user_access

        user = AuthenticatedUser(
            uid="user123",
            email="test@wm.edu",
            email_verified=True,
            role=UserRole.STUDENT
        )
        assert verify_user_access(user, "other456") is False

    def test_advisor_can_access_any_resource(self):
        """Advisors should be able to access any resource"""
        from core.auth import verify_user_access

        user = AuthenticatedUser(
            uid="advisor123",
            email="advisor@wm.edu",
            email_verified=True,
            role=UserRole.ADVISOR
        )
        assert verify_user_access(user, "student456") is True

    def test_admin_can_access_any_resource(self):
        """Admins should be able to access any resource"""
        from core.auth import verify_user_access

        user = AuthenticatedUser(
            uid="admin123",
            email="admin@wm.edu",
            email_verified=True,
            role=UserRole.ADMIN
        )
        assert verify_user_access(user, "student456") is True
