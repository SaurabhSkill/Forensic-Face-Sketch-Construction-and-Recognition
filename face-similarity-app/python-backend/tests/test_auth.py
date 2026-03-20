"""
tests/test_auth.py
──────────────────
Auth flow tests:
  - Admin 2-step login (OTP)
  - Officer direct login
  - Token verification
  - Password change
  - Edge cases: wrong password, expired OTP, reused OTP, role mismatch
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from auth_v2 import hash_password, store_otp
from db_models import OTP, User


# ══════════════════════════════════════════════════════════════════════════════
# Admin login — Step 1
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminLoginStep1:

    def test_valid_credentials_returns_user_id(self, client, admin_user, db):
        resp = client.post("/api/auth/admin/login-step1", json={
            "email": admin_user.email,
            "password": "AdminPass123!",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["requires_otp"] is True
        assert data["user_id"] == admin_user.id

    def test_otp_stored_in_db(self, client, admin_user, db):
        client.post("/api/auth/admin/login-step1", json={
            "email": admin_user.email,
            "password": "AdminPass123!",
        })
        otp_record = db.query(OTP).filter(OTP.user_id == admin_user.id).first()
        assert otp_record is not None
        assert otp_record.is_used is False
        assert otp_record.otp_hash != ""

    def test_wrong_password_returns_401(self, client, admin_user, db):
        resp = client.post("/api/auth/admin/login-step1", json={
            "email": admin_user.email,
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401
        assert "Invalid" in resp.get_json()["error"]

    def test_unknown_email_returns_401(self, client, db):
        resp = client.post("/api/auth/admin/login-step1", json={
            "email": "nobody@forensic.gov.in",
            "password": "anything",
        })
        assert resp.status_code == 401

    def test_officer_email_cannot_use_admin_login(self, client, officer_user, db):
        """Officer role must not be able to trigger admin OTP flow."""
        resp = client.post("/api/auth/admin/login-step1", json={
            "email": officer_user.email,
            "password": "OfficerPass123!",
        })
        assert resp.status_code == 401

    def test_missing_fields_returns_400(self, client, db):
        resp = client.post("/api/auth/admin/login-step1", json={"email": "x@x.com"})
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# Admin login — Step 2 (OTP verification)
# ══════════════════════════════════════════════════════════════════════════════

class TestAdminLoginStep2:

    def _get_otp_dev(self, client, admin_user) -> tuple[int, str]:
        """Helper: run step1 and extract otp_dev from response."""
        resp = client.post("/api/auth/admin/login-step1", json={
            "email": admin_user.email,
            "password": "AdminPass123!",
        })
        data = resp.get_json()
        return data["user_id"], data.get("otp_dev", "")

    def test_valid_otp_returns_jwt(self, client, admin_user, db):
        user_id, otp = self._get_otp_dev(client, admin_user)
        resp = client.post("/api/auth/admin/login-step2", json={
            "user_id": user_id,
            "otp": otp,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert data["user"]["role"] == "admin"

    def test_otp_marked_used_after_verification(self, client, admin_user, db):
        user_id, otp = self._get_otp_dev(client, admin_user)
        client.post("/api/auth/admin/login-step2", json={"user_id": user_id, "otp": otp})
        otp_record = db.query(OTP).filter(OTP.user_id == admin_user.id).first()
        assert otp_record.is_used is True

    def test_wrong_otp_returns_401(self, client, admin_user, db):
        user_id, _ = self._get_otp_dev(client, admin_user)
        resp = client.post("/api/auth/admin/login-step2", json={
            "user_id": user_id,
            "otp": "000000",
        })
        assert resp.status_code == 401

    def test_reused_otp_returns_401(self, client, admin_user, db):
        """OTP cannot be used twice."""
        user_id, otp = self._get_otp_dev(client, admin_user)
        client.post("/api/auth/admin/login-step2", json={"user_id": user_id, "otp": otp})
        resp = client.post("/api/auth/admin/login-step2", json={"user_id": user_id, "otp": otp})
        assert resp.status_code == 401

    def test_expired_otp_returns_401(self, client, admin_user, db):
        """Manually insert an already-expired OTP."""
        from auth_v2 import hash_password as hp
        expired_otp = OTP(
            user_id=admin_user.id,
            otp_hash=hp("123456"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            is_used=False,
        )
        db.add(expired_otp)
        db.flush()

        resp = client.post("/api/auth/admin/login-step2", json={
            "user_id": admin_user.id,
            "otp": "123456",
        })
        assert resp.status_code == 401

    def test_missing_fields_returns_400(self, client, db):
        resp = client.post("/api/auth/admin/login-step2", json={"user_id": 1})
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# Officer login
# ══════════════════════════════════════════════════════════════════════════════

class TestOfficerLogin:

    def test_valid_login_returns_token(self, client, officer_user, db):
        resp = client.post("/api/auth/officer/login", json={
            "email": officer_user.email,
            "password": "OfficerPass123!",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert data["user"]["role"] == "officer"
        assert data["requires_password_change"] is False

    def test_temp_password_flag_in_response(self, client, db):
        """Officer with is_temp_password=True should get requires_password_change=True."""
        temp_officer = User(
            full_name="Temp Officer",
            department_name="Forensics",
            email="temp@forensic.gov.in",
            officer_id="OFF-TEMP-001",
            password_hash=hash_password("TempPass123!"),
            role="officer",
            is_temp_password=True,
        )
        db.add(temp_officer)
        db.flush()

        resp = client.post("/api/auth/officer/login", json={
            "email": "temp@forensic.gov.in",
            "password": "TempPass123!",
        })
        assert resp.status_code == 200
        assert resp.get_json()["requires_password_change"] is True

    def test_wrong_password_returns_401(self, client, officer_user, db):
        resp = client.post("/api/auth/officer/login", json={
            "email": officer_user.email,
            "password": "wrong",
        })
        assert resp.status_code == 401

    def test_admin_cannot_use_officer_login(self, client, admin_user, db):
        """Admin role must not be found by the officer login endpoint."""
        resp = client.post("/api/auth/officer/login", json={
            "email": admin_user.email,
            "password": "AdminPass123!",
        })
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# Token verification & password change
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenAndPasswordChange:

    def test_verify_valid_token(self, client, auth_headers_officer, db):
        resp = client.get("/api/auth/verify", headers=auth_headers_officer)
        assert resp.status_code == 200
        assert resp.get_json()["valid"] is True

    def test_verify_invalid_token_returns_401(self, client, db):
        resp = client.get("/api/auth/verify", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401

    def test_verify_missing_token_returns_401(self, client, db):
        resp = client.get("/api/auth/verify")
        assert resp.status_code == 401

    def test_change_password_success(self, client, auth_headers_officer, officer_user, db):
        resp = client.post("/api/auth/change-password",
                           json={"new_password": "NewSecurePass123!"},
                           headers=auth_headers_officer)
        assert resp.status_code == 200
        # Re-query instead of refresh (avoids cross-session issues)
        from db_models import User
        updated = db.query(User).filter(User.id == officer_user.id).first()
        assert updated.is_temp_password is False

    def test_change_password_too_short_returns_400(self, client, auth_headers_officer, db):
        resp = client.post("/api/auth/change-password",
                           json={"new_password": "short"},
                           headers=auth_headers_officer)
        assert resp.status_code == 400

    def test_change_password_requires_auth(self, client, db):
        resp = client.post("/api/auth/change-password", json={"new_password": "NewPass123!"})
        assert resp.status_code == 401
