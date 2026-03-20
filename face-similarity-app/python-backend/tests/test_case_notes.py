"""
tests/test_case_notes.py
────────────────────────
Case notes tests:
  - Add notes
  - Retrieve notes
  - Cascade delete (case deleted → notes deleted)
  - Author FK integrity
  - Orphan prevention
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from db_models import Case, CaseNote, User


# ══════════════════════════════════════════════════════════════════════════════
# Add notes
# ══════════════════════════════════════════════════════════════════════════════

class TestAddCaseNote:

    def test_add_note_success(self, client, case, auth_headers_officer, officer_user, db):
        resp = client.post(
            f"/api/cases/{case.id}/notes",
            json={"content": "Suspect identified at CCTV footage."},
            headers=auth_headers_officer,
        )
        assert resp.status_code == 201
        data = resp.get_json()["note"]
        assert data["content"] == "Suspect identified at CCTV footage."
        assert data["case_id"] == case.id
        assert data["author_id"] == officer_user.id

    def test_note_author_name_defaults_to_full_name(self, client, case, auth_headers_officer, officer_user, db):
        resp = client.post(
            f"/api/cases/{case.id}/notes",
            json={"content": "Test note"},
            headers=auth_headers_officer,
        )
        data = resp.get_json()["note"]
        assert data["author_name"] == officer_user.full_name

    def test_note_author_name_can_be_overridden(self, client, case, auth_headers_officer, db):
        resp = client.post(
            f"/api/cases/{case.id}/notes",
            json={"content": "Test note", "author_name": "Custom Name"},
            headers=auth_headers_officer,
        )
        assert resp.get_json()["note"]["author_name"] == "Custom Name"

    def test_empty_content_returns_400(self, client, case, auth_headers_officer, db):
        resp = client.post(
            f"/api/cases/{case.id}/notes",
            json={"content": ""},
            headers=auth_headers_officer,
        )
        assert resp.status_code == 400

    def test_missing_content_returns_400(self, client, case, auth_headers_officer, db):
        resp = client.post(
            f"/api/cases/{case.id}/notes",
            json={},
            headers=auth_headers_officer,
        )
        assert resp.status_code == 400

    def test_note_on_nonexistent_case_returns_404(self, client, auth_headers_officer, db):
        resp = client.post(
            "/api/cases/99999/notes",
            json={"content": "Ghost note"},
            headers=auth_headers_officer,
        )
        assert resp.status_code == 404

    def test_add_note_requires_auth(self, client, case, db):
        resp = client.post(f"/api/cases/{case.id}/notes", json={"content": "Unauthorized"})
        assert resp.status_code == 401

    def test_adding_note_updates_case_updated_at(self, client, case, auth_headers_officer, db):
        original_updated_at = case.updated_at
        client.post(
            f"/api/cases/{case.id}/notes",
            json={"content": "Timestamp test"},
            headers=auth_headers_officer,
        )
        updated = db.query(Case).filter(Case.id == case.id).first()
        # Normalize both to naive UTC for comparison (SQLite stores naive datetimes)
        from datetime import timezone as tz
        def _naive(dt):
            if dt and dt.tzinfo is not None:
                return dt.astimezone(tz.utc).replace(tzinfo=None)
            return dt
        assert _naive(updated.updated_at) >= _naive(original_updated_at)


# ══════════════════════════════════════════════════════════════════════════════
# Retrieve notes
# ══════════════════════════════════════════════════════════════════════════════

class TestGetCaseNotes:

    def test_get_notes_for_case(self, client, case, auth_headers_officer, officer_user, db):
        # Add two notes directly
        db.add(CaseNote(case_id=case.id, author_id=officer_user.id,
                        author_name="Officer", content="Note 1"))
        db.add(CaseNote(case_id=case.id, author_id=officer_user.id,
                        author_name="Officer", content="Note 2"))
        db.flush()

        resp = client.get(f"/api/cases/{case.id}/notes", headers=auth_headers_officer)
        assert resp.status_code == 200
        notes = resp.get_json()["notes"]
        assert len(notes) == 2

    def test_notes_ordered_by_created_at_desc(self, client, case, auth_headers_officer, officer_user, db):
        from datetime import datetime, timedelta, timezone
        t1 = datetime.now(timezone.utc) - timedelta(minutes=5)
        t2 = datetime.now(timezone.utc)
        db.add(CaseNote(case_id=case.id, author_id=officer_user.id,
                        author_name="Officer", content="Older note", created_at=t1))
        db.add(CaseNote(case_id=case.id, author_id=officer_user.id,
                        author_name="Officer", content="Newer note", created_at=t2))
        db.flush()

        resp = client.get(f"/api/cases/{case.id}/notes", headers=auth_headers_officer)
        notes = resp.get_json()["notes"]
        assert notes[0]["content"] == "Newer note"

    def test_get_notes_for_nonexistent_case_returns_404(self, client, auth_headers_officer, db):
        resp = client.get("/api/cases/99999/notes", headers=auth_headers_officer)
        assert resp.status_code == 404

    def test_get_notes_requires_auth(self, client, case, db):
        resp = client.get(f"/api/cases/{case.id}/notes")
        assert resp.status_code == 401

    def test_empty_notes_returns_empty_list(self, client, case, auth_headers_officer, db):
        resp = client.get(f"/api/cases/{case.id}/notes", headers=auth_headers_officer)
        assert resp.status_code == 200
        assert resp.get_json()["notes"] == []


# ══════════════════════════════════════════════════════════════════════════════
# Cascade delete
# ══════════════════════════════════════════════════════════════════════════════

class TestCascadeDelete:

    def test_deleting_case_deletes_notes(self, client, case, auth_headers_officer, officer_user, db):
        """CaseNote has ondelete=CASCADE — deleting the case must delete all notes."""
        note = CaseNote(
            case_id=case.id,
            author_id=officer_user.id,
            author_name="Officer",
            content="Will be deleted",
        )
        db.add(note)
        db.flush()
        note_id = note.id

        # Delete directly via ORM to test cascade (same session)
        db.delete(case)
        db.flush()

        # Note must be gone
        assert db.query(CaseNote).filter(CaseNote.id == note_id).first() is None

    def test_deleting_case_does_not_delete_author(self, client, case, auth_headers_officer, officer_user, db):
        """Deleting a case must NOT delete the author user."""
        note = CaseNote(
            case_id=case.id,
            author_id=officer_user.id,
            author_name="Officer",
            content="Author should survive",
        )
        db.add(note)
        db.flush()

        db.delete(case)
        db.flush()

        assert db.query(User).filter(User.id == officer_user.id).first() is not None

    def test_deleting_user_deletes_their_notes(self, db, officer_user, case):
        """User has cascade=all,delete-orphan on case_notes relationship."""
        note = CaseNote(
            case_id=case.id,
            author_id=officer_user.id,
            author_name="Officer",
            content="Orphan note",
        )
        db.add(note)
        db.flush()
        note_id = note.id

        db.delete(officer_user)
        db.flush()

        assert db.query(CaseNote).filter(CaseNote.id == note_id).first() is None

    def test_note_fk_case_id_enforced(self, db, officer_user):
        """Inserting a note with a non-existent case_id must fail."""
        from sqlalchemy.exc import IntegrityError
        note = CaseNote(
            case_id=99999,  # does not exist
            author_id=officer_user.id,
            author_name="Officer",
            content="Bad FK",
        )
        db.add(note)
        with pytest.raises(IntegrityError):
            db.flush()

    def test_note_fk_author_id_enforced(self, db, case):
        """Inserting a note with a non-existent author_id must fail."""
        from sqlalchemy.exc import IntegrityError
        note = CaseNote(
            case_id=case.id,
            author_id=99999,  # does not exist
            author_name="Ghost",
            content="Bad FK",
        )
        db.add(note)
        with pytest.raises(IntegrityError):
            db.flush()
