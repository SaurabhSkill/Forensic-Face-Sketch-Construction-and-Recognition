"""
tests/test_cases.py
───────────────────
Case management tests:
  - Create / read / update / delete
  - Link criminals (many-to-many via case_criminals)
  - Add evidence items (many-to-many via case_evidence)
  - Case notes + cascade delete
  - Role-based visibility (officer sees own cases only)
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from db_models import Case, CaseNote, Criminal, EvidenceItem, case_criminals, case_evidence


# ══════════════════════════════════════════════════════════════════════════════
# Create case
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateCase:

    def test_create_case_success(self, client, auth_headers_officer, officer_user, db):
        resp = client.post("/api/cases", json={
            "title": "Bank Robbery 2026",
            "description": "Armed robbery at SBI branch",
            "status": "Open",
            "priority": "High",
            "crime_type": "Robbery",
            "location": "Mumbai",
        }, headers=auth_headers_officer)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "case_id" in data
        assert "case_number" in data

    def test_case_officer_id_set_to_current_user(self, client, auth_headers_officer, officer_user, db):
        resp = client.post("/api/cases", json={"title": "Test Case"}, headers=auth_headers_officer)
        case_id = resp.get_json()["case_id"]
        case = db.query(Case).filter(Case.id == case_id).first()
        assert case.officer_id == officer_user.id

    def test_case_number_is_unique(self, client, auth_headers_officer, db):
        r1 = client.post("/api/cases", json={"title": "Case A"}, headers=auth_headers_officer)
        r2 = client.post("/api/cases", json={"title": "Case B"}, headers=auth_headers_officer)
        assert r1.get_json()["case_number"] != r2.get_json()["case_number"]

    def test_missing_title_returns_400(self, client, auth_headers_officer, db):
        resp = client.post("/api/cases", json={"description": "no title"}, headers=auth_headers_officer)
        assert resp.status_code == 400

    def test_create_case_requires_auth(self, client, db):
        resp = client.post("/api/cases", json={"title": "Unauthorized"})
        assert resp.status_code == 401

    def test_default_status_is_open(self, client, auth_headers_officer, db):
        resp = client.post("/api/cases", json={"title": "Default Status"}, headers=auth_headers_officer)
        case_id = resp.get_json()["case_id"]
        case = db.query(Case).filter(Case.id == case_id).first()
        assert case.status == "Open"

    def test_default_priority_is_medium(self, client, auth_headers_officer, db):
        resp = client.post("/api/cases", json={"title": "Default Priority"}, headers=auth_headers_officer)
        case_id = resp.get_json()["case_id"]
        case = db.query(Case).filter(Case.id == case_id).first()
        assert case.priority == "Medium"


# ══════════════════════════════════════════════════════════════════════════════
# Read cases
# ══════════════════════════════════════════════════════════════════════════════

class TestGetCases:

    def test_officer_sees_only_own_cases(self, client, auth_headers_officer, auth_headers_admin,
                                         officer_user, admin_user, db):
        """Officers must only see cases they own."""
        # Create a case as officer
        client.post("/api/cases", json={"title": "Officer Case"}, headers=auth_headers_officer)
        # Create a case as admin (different officer_id)
        client.post("/api/cases", json={"title": "Admin Case"}, headers=auth_headers_admin)

        resp = client.get("/api/cases", headers=auth_headers_officer)
        cases = resp.get_json()["cases"]
        officer_ids = {c["officer_id"] for c in cases}
        assert officer_ids == {officer_user.id}

    def test_admin_sees_all_cases(self, client, auth_headers_officer, auth_headers_admin, db):
        client.post("/api/cases", json={"title": "Officer Case"}, headers=auth_headers_officer)
        client.post("/api/cases", json={"title": "Admin Case"}, headers=auth_headers_admin)

        resp = client.get("/api/cases", headers=auth_headers_admin)
        assert resp.status_code == 200
        # Admin should see both
        assert len(resp.get_json()["cases"]) >= 2

    def test_get_case_by_id(self, client, case, auth_headers_officer, db):
        resp = client.get(f"/api/cases/{case.id}", headers=auth_headers_officer)
        assert resp.status_code == 200
        data = resp.get_json()["case"]
        assert data["case_number"] == case.case_number
        assert data["title"] == "Test Case"

    def test_get_nonexistent_case_returns_404(self, client, auth_headers_officer, db):
        resp = client.get("/api/cases/99999", headers=auth_headers_officer)
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Update case
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateCase:

    def test_update_case_status(self, client, case, auth_headers_officer, db):
        resp = client.patch(f"/api/cases/{case.id}",
                            json={"status": "Closed"},
                            headers=auth_headers_officer)
        assert resp.status_code == 200
        updated = db.query(Case).filter(Case.id == case.id).first()
        assert updated.status == "Closed"

    def test_update_case_title(self, client, case, auth_headers_officer, db):
        resp = client.patch(f"/api/cases/{case.id}",
                            json={"title": "Updated Title"},
                            headers=auth_headers_officer)
        assert resp.status_code == 200
        updated = db.query(Case).filter(Case.id == case.id).first()
        assert updated.title == "Updated Title"

    def test_update_nonexistent_case_returns_404(self, client, auth_headers_officer, db):
        resp = client.patch("/api/cases/99999", json={"status": "Closed"}, headers=auth_headers_officer)
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Link criminals to case (many-to-many)
# ══════════════════════════════════════════════════════════════════════════════

class TestCaseCriminalLink:

    def test_link_criminal_via_update(self, client, case, criminal, auth_headers_officer, db):
        """
        The API accepts linked_criminals as a list of criminal_id strings.
        """
        resp = client.patch(
            f"/api/cases/{case.id}",
            json={"linked_criminals": [criminal.criminal_id]},
            headers=auth_headers_officer,
        )
        assert resp.status_code == 200

    def test_direct_association_table_insert(self, case, criminal, db):
        """Directly test the case_criminals association table."""
        db.execute(
            case_criminals.insert().values(case_id=case.id, criminal_id=criminal.id)
        )
        db.flush()

        # Verify the link exists
        result = db.execute(
            case_criminals.select().where(
                (case_criminals.c.case_id == case.id) &
                (case_criminals.c.criminal_id == criminal.id)
            )
        ).fetchone()
        assert result is not None

    def test_duplicate_link_raises_integrity_error(self, case, criminal, db):
        """Composite PK on case_criminals prevents duplicate links."""
        from sqlalchemy.exc import IntegrityError
        db.execute(case_criminals.insert().values(case_id=case.id, criminal_id=criminal.id))
        db.flush()
        with pytest.raises(IntegrityError):
            db.execute(case_criminals.insert().values(case_id=case.id, criminal_id=criminal.id))
            db.flush()

    def test_cascade_delete_removes_case_criminal_link(self, case, criminal, db):
        """Deleting a case must cascade-delete case_criminals rows."""
        db.execute(case_criminals.insert().values(case_id=case.id, criminal_id=criminal.id))
        db.flush()

        db.delete(case)
        db.flush()

        result = db.execute(
            case_criminals.select().where(case_criminals.c.case_id == case.id)
        ).fetchall()
        assert result == []

    def test_criminal_not_deleted_when_case_deleted(self, case, criminal, db):
        """Deleting a case must NOT delete the criminal record."""
        db.execute(case_criminals.insert().values(case_id=case.id, criminal_id=criminal.id))
        db.flush()
        db.delete(case)
        db.flush()

        assert db.query(Criminal).filter(Criminal.id == criminal.id).first() is not None


# ══════════════════════════════════════════════════════════════════════════════
# Evidence items
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceItems:

    def test_create_evidence_item(self, db):
        ev = EvidenceItem(
            evidence_ref="EV-AUDIT-001",
            evidence_type="fingerprint",
            description="Latent print from door handle",
            file_url="https://example.supabase.co/storage/v1/object/public/criminal-images/evidence/EV-AUDIT-001.jpg",
            metadata={"lab": "FSL Mumbai", "analyst": "Dr. Sharma"},
        )
        db.add(ev)
        db.flush()
        assert ev.id is not None

    def test_evidence_metadata_is_jsonb_dict(self, db):
        ev = EvidenceItem(
            evidence_ref="EV-AUDIT-002",
            evidence_type="DNA",
            metadata={"profile": "XY-001", "confidence": 0.99},
        )
        db.add(ev)
        db.flush()
        db.refresh(ev)
        assert isinstance(ev.metadata, dict)
        assert ev.metadata["confidence"] == 0.99

    def test_link_evidence_to_case(self, case, db):
        ev = EvidenceItem(evidence_ref="EV-LINK-001", evidence_type="photo")
        db.add(ev)
        db.flush()

        db.execute(case_evidence.insert().values(case_id=case.id, evidence_id=ev.id))
        db.flush()

        result = db.execute(
            case_evidence.select().where(case_evidence.c.case_id == case.id)
        ).fetchall()
        assert len(result) == 1

    def test_cascade_delete_removes_case_evidence_link(self, case, db):
        ev = EvidenceItem(evidence_ref="EV-CASCADE-001", evidence_type="photo")
        db.add(ev)
        db.flush()
        db.execute(case_evidence.insert().values(case_id=case.id, evidence_id=ev.id))
        db.flush()

        db.delete(case)
        db.flush()

        result = db.execute(
            case_evidence.select().where(case_evidence.c.case_id == case.id)
        ).fetchall()
        assert result == []

    def test_evidence_item_not_deleted_when_case_deleted(self, case, db):
        ev = EvidenceItem(evidence_ref="EV-PERSIST-001", evidence_type="photo")
        db.add(ev)
        db.flush()
        db.execute(case_evidence.insert().values(case_id=case.id, evidence_id=ev.id))
        db.flush()

        db.delete(case)
        db.flush()

        assert db.query(EvidenceItem).filter(EvidenceItem.id == ev.id).first() is not None

    def test_duplicate_evidence_ref_raises_error(self, db):
        from sqlalchemy.exc import IntegrityError
        db.add(EvidenceItem(evidence_ref="EV-DUP-001", evidence_type="photo"))
        db.flush()
        with pytest.raises(IntegrityError):
            db.add(EvidenceItem(evidence_ref="EV-DUP-001", evidence_type="DNA"))
            db.flush()


# ══════════════════════════════════════════════════════════════════════════════
# Delete case
# ══════════════════════════════════════════════════════════════════════════════

class TestDeleteCase:

    def test_delete_case_success(self, client, case, auth_headers_officer, db):
        resp = client.delete(f"/api/cases/{case.id}", headers=auth_headers_officer)
        assert resp.status_code == 200
        assert db.query(Case).filter(Case.id == case.id).first() is None

    def test_delete_nonexistent_case_returns_404(self, client, auth_headers_officer, db):
        resp = client.delete("/api/cases/99999", headers=auth_headers_officer)
        assert resp.status_code == 404

    def test_delete_requires_auth(self, client, case, db):
        resp = client.delete(f"/api/cases/{case.id}")
        assert resp.status_code == 401
