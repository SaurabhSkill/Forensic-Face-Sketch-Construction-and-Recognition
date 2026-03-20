"""
tests/test_admin.py
───────────────────
Admin officer management endpoint tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from db_models import User


OFFICER_PAYLOAD = {
    "full_name": "New Officer",
    "department_name": "Forensics",
    "email": "newofficer@forensic.gov.in",
    "officer_id": "OFF-NEW-001",
}


class TestGetOfficers:

    def test_admin_can_list_officers(self, client, officer_user, auth_headers_admin, db):
        resp = client.get("/api/admin/officers", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "officers" in data
        ids = [o["officer_id"] for o in data["officers"]]
        assert "OFF-TEST-001" in ids

    def test_officer_cannot_list_officers(self, client, auth_headers_officer, db):
        resp = client.get("/api/admin/officers", headers=auth_headers_officer)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_officers(self, client, db):
        resp = client.get("/api/admin/officers")
        assert resp.status_code == 401


class TestAddOfficer:

    def test_admin_can_add_officer(self, client, admin_user, auth_headers_admin, db):
        resp = client.post(
            "/api/admin/officers",
            json=OFFICER_PAYLOAD,
            headers=auth_headers_admin,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["officer"]["email"] == OFFICER_PAYLOAD["email"]

    def test_officer_saved_with_temp_password(self, client, admin_user, auth_headers_admin, db):
        client.post("/api/admin/officers", json=OFFICER_PAYLOAD, headers=auth_headers_admin)
        record = db.query(User).filter(User.email == OFFICER_PAYLOAD["email"], User.role == "officer").first()
        assert record is not None
        assert record.is_temp_password is True

    def test_duplicate_email_returns_400(self, client, officer_user, auth_headers_admin, db):
        payload = {**OFFICER_PAYLOAD, "email": officer_user.email}
        resp = client.post("/api/admin/officers", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400

    def test_missing_required_field_returns_400(self, client, auth_headers_admin, db):
        payload = {k: v for k, v in OFFICER_PAYLOAD.items() if k != "email"}
        resp = client.post("/api/admin/officers", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400

    def test_officer_cannot_add_officer(self, client, auth_headers_officer, db):
        resp = client.post("/api/admin/officers", json=OFFICER_PAYLOAD, headers=auth_headers_officer)
        assert resp.status_code == 403


class TestResetOfficerPassword:

    def test_admin_can_reset_password(self, client, officer_user, auth_headers_admin, db):
        resp = client.post(
            f"/api/admin/officers/{officer_user.id}/reset-password",
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        # Re-query instead of refresh (avoids cross-session issues)
        updated = db.query(User).filter(User.id == officer_user.id).first()
        assert updated.is_temp_password is True

    def test_reset_nonexistent_officer_returns_404(self, client, auth_headers_admin, db):
        resp = client.post("/api/admin/officers/99999/reset-password", headers=auth_headers_admin)
        assert resp.status_code == 404

    def test_officer_cannot_reset_password(self, client, officer_user, auth_headers_officer, db):
        resp = client.post(
            f"/api/admin/officers/{officer_user.id}/reset-password",
            headers=auth_headers_officer,
        )
        assert resp.status_code == 403


class TestDeleteOfficer:

    def test_admin_can_delete_officer(self, client, officer_user, auth_headers_admin, db):
        officer_id = officer_user.id
        resp = client.delete(f"/api/admin/officers/{officer_id}", headers=auth_headers_admin)
        assert resp.status_code == 200
        assert db.query(User).filter(User.id == officer_id).first() is None

    def test_delete_nonexistent_officer_returns_404(self, client, auth_headers_admin, db):
        resp = client.delete("/api/admin/officers/99999", headers=auth_headers_admin)
        assert resp.status_code == 404

    def test_officer_cannot_delete_officer(self, client, officer_user, auth_headers_officer, db):
        resp = client.delete(f"/api/admin/officers/{officer_user.id}", headers=auth_headers_officer)
        assert resp.status_code == 403
