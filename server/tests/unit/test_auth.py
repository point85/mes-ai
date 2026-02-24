"""
Unit tests for AUTH module.

Tests cover:
- Password hashing and verification
- JWT token creation and decoding
- Permission wildcard matching
- Auth service logic (no DB required)
"""

from __future__ import annotations

import time

import pytest

from mes.framework.auth.service import AuthService


# --- Password hashing tests ---


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "SecurePassword123!"
        hashed = AuthService.hash_password(password)
        assert AuthService.verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = AuthService.hash_password("correctpassword")
        assert AuthService.verify_password("wrongpassword", hashed) is False

    def test_hash_produces_unique_salts(self):
        h1 = AuthService.hash_password("same_password")
        h2 = AuthService.hash_password("same_password")
        assert h1 != h2  # Different salts

    def test_malformed_hash_returns_false(self):
        assert AuthService.verify_password("password", "not_a_valid_hash") is False
        assert AuthService.verify_password("password", "") is False


# --- JWT token tests ---


class TestJWTTokens:
    def test_create_and_decode_access_token(self):
        token = AuthService.create_access_token(
            user_id="user-123",
            username="testuser",
            roles=["operator"],
            permissions=["wip.*", "dispatch.read"],
        )
        payload = AuthService.decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["username"] == "testuser"
        assert payload["roles"] == ["operator"]
        assert payload["type"] == "access"
        assert "wip.*" in payload["permissions"]

    def test_create_and_decode_refresh_token(self):
        token = AuthService.create_refresh_token(user_id="user-456")
        payload = AuthService.decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self):
        import jwt

        with pytest.raises(jwt.InvalidTokenError):
            AuthService.decode_token("this.is.not.a.valid.token")


# --- Permission matching tests ---


class TestPermissionMatching:
    def test_exact_match(self):
        assert AuthService.check_permission(["wip.unit.move"], "wip.unit.move") is True

    def test_no_match(self):
        assert AuthService.check_permission(["wip.unit.move"], "quality.test.read") is False

    def test_global_wildcard(self):
        """Admin '*' permission matches everything."""
        assert AuthService.check_permission(["*"], "wip.unit.move") is True
        assert AuthService.check_permission(["*"], "quality.test.read") is True
        assert AuthService.check_permission(["*"], "anything") is True

    def test_module_wildcard(self):
        """'wip.*' matches all wip sub-permissions."""
        perms = ["wip.*"]
        assert AuthService.check_permission(perms, "wip.unit.move") is True
        assert AuthService.check_permission(perms, "wip.lot.created") is True
        assert AuthService.check_permission(perms, "quality.test.read") is False

    def test_action_wildcard(self):
        """'*.read' matches read permission in any module."""
        perms = ["*.read"]
        assert AuthService.check_permission(perms, "wip.read") is True
        assert AuthService.check_permission(perms, "quality.read") is True
        assert AuthService.check_permission(perms, "wip.unit.read") is True  # Last part is 'read'
        assert AuthService.check_permission(perms, "wip.unit.move") is False

    def test_multiple_permissions(self):
        perms = ["wip.unit.move", "dispatch.read", "quality.*"]
        assert AuthService.check_permission(perms, "wip.unit.move") is True
        assert AuthService.check_permission(perms, "dispatch.read") is True
        assert AuthService.check_permission(perms, "quality.test.passed") is True
        assert AuthService.check_permission(perms, "material.consume") is False

    def test_empty_permissions(self):
        assert AuthService.check_permission([], "wip.unit.move") is False
