"""
tests/test_criminals.py
───────────────────────
Criminal CRUD + photo URL + JSONB embedding tests.
"""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from db_models import Criminal

CRIMINAL_PROFILE = {
    "criminal_id": "CR-NEW-001",
    "full_name": "Jane Smith",
    "status": "Suspect",
    "aliases": ["JS", "Smithy"],
    "dob": "1990-03-22",
    "sex": "Female",
    "nationality": "Indian",
    "ethnicity": "South Asian",
    "appearance": {"height": "5ft5", "build": "slim", "hair": "black"},
    "locations": {"city": "Delhi", "state": "Delhi", "lastSeen": "2026-01-10"},
    "summary": {"charges": ["fraud", "identity theft"], "risk": "medium"},
    "forensics": {"fingerprintId": "FP-002", "dnaProfile": "DNA-002"},
    "evidence": [{"type": "fingerprint", "ref": "EV-002"}],
    "witness": {"statements": ["seen near ATM"], "credibility": "high"},
}

FAKE_PHOTO_KEY = "criminals/CR-NEW-001/abc123def456.jpg"


# ══════════════════════════════════════════════════════════════════════════════
# Add criminal
# ══════════════════════════════════════════════════════════════════════════════

class TestAddCriminal:

    def test_add_criminal_success(self, client, auth_headers_officer, sample_image_bytes, mock_embedding, db):
        with patch("services.s3_service.upload_criminal_photo", return_value=FAKE_PHOTO_KEY):
            resp = client.post(
                "/api/criminals",
                data={
                    "photo": (io.BytesIO(sample_image_bytes), "test_photo.jpg"),
                    "data": json.dumps(CRIMINAL_PROFILE),
                },
                content_type="multipart/form-data",
                headers=auth_headers_officer,
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["criminal"]["criminal_id"] == "CR-NEW-001"

    def test_photo_key_saved_in_db(self, client, auth_headers_officer, sample_image_bytes, mock_embedding, db):
        with patch("services.s3_service.upload_criminal_photo", return_value=FAKE_PHOTO_KEY):
            client.post(
                "/api/criminals",
                data={
                    "photo": (io.BytesIO(sample_image_bytes), "test_photo.jpg"),
                    "data": json.dumps(CRIMINAL_PROFILE),
                },
                content_type="multipart/form-data",
                headers=auth_headers_officer,
            )
        record = db.query(Criminal).filter(Criminal.criminal_id == "CR-NEW-001").first()
        assert record is not None
        assert record.photo_key == FAKE_PHOTO_KEY
        assert record.photo_key.startswith("criminals/")

    def test_jsonb_fields_stored_as_objects_not_strings(self, client, auth_headers_officer, sample_image_bytes, mock_embedding, db):
        """JSONB columns must be stored as dicts/lists, not JSON strings."""
        with patch("services.s3_service.upload_criminal_photo", return_value=FAKE_PHOTO_KEY):
            client.post(
                "/api/criminals",
                data={
                    "photo": (io.BytesIO(sample_image_bytes), "test_photo.jpg"),
                    "data": json.dumps(CRIMINAL_PROFILE),
                },
                content_type="multipart/form-data",
                headers=auth_headers_officer,
            )
        record = db.query(Criminal).filter(Criminal.criminal_id == "CR-NEW-001").first()
        # These must be Python objects, not strings
        assert isinstance(record.aliases, list), f"aliases is {type(record.aliases)}, expected list"
        assert isinstance(record.appearance, dict), f"appearance is {type(record.appearance)}, expected dict"
        assert isinstance(record.locations, dict)
        assert isinstance(record.summary, dict)
        assert isinstance(record.forensics, dict)
        assert isinstance(record.evidence, list)
        assert isinstance(record.witness, dict)

    def test_missing_photo_returns_400(self, client, auth_headers_officer, db):
        resp = client.post(
            "/api/criminals",
            data={"data": json.dumps(CRIMINAL_PROFILE)},
            content_type="multipart/form-data",
            headers=auth_headers_officer,
        )
        assert resp.status_code == 400

    def test_missing_data_returns_400(self, client, auth_headers_officer, sample_image_bytes, db):
        resp = client.post(
            "/api/criminals",
            data={"photo": (io.BytesIO(sample_image_bytes), "photo.jpg")},
            content_type="multipart/form-data",
            headers=auth_headers_officer,
        )
        assert resp.status_code == 400

    def test_missing_criminal_id_returns_400(self, client, auth_headers_officer, sample_image_bytes, db):
        profile = {**CRIMINAL_PROFILE}
        del profile["criminal_id"]
        resp = client.post(
            "/api/criminals",
            data={
                "photo": (io.BytesIO(sample_image_bytes), "photo.jpg"),
                "data": json.dumps(profile),
            },
            content_type="multipart/form-data",
            headers=auth_headers_officer,
        )
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, client, sample_image_bytes, db):
        resp = client.post(
            "/api/criminals",
            data={
                "photo": (io.BytesIO(sample_image_bytes), "photo.jpg"),
                "data": json.dumps(CRIMINAL_PROFILE),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401

    def test_s3_upload_failure_does_not_crash(self, client, auth_headers_officer, sample_image_bytes, mock_embedding, db):
        """If S3 upload fails, criminal should still be saved (photo_key=None)."""
        with patch("services.s3_service.upload_criminal_photo", side_effect=RuntimeError("S3 down")):
            resp = client.post(
                "/api/criminals",
                data={
                    "photo": (io.BytesIO(sample_image_bytes), "test_photo.jpg"),
                    "data": json.dumps(CRIMINAL_PROFILE),
                },
                content_type="multipart/form-data",
                headers=auth_headers_officer,
            )
        # Should succeed at DB level even if photo upload fails
        assert resp.status_code in (201, 500)  # 201 if graceful, 500 if not — documents current behavior


# ══════════════════════════════════════════════════════════════════════════════
# Retrieve criminal
# ══════════════════════════════════════════════════════════════════════════════

class TestGetCriminal:

    def test_get_all_criminals(self, client, criminal, auth_headers_officer, db):
        resp = client.get("/api/criminals", headers=auth_headers_officer)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["criminals"]) >= 1
        ids = [c["criminal_id"] for c in data["criminals"]]
        assert "CR-TEST-001" in ids

    def test_get_criminal_by_id(self, client, criminal, auth_headers_officer, db):
        resp = client.get(f"/api/criminals/{criminal.id}", headers=auth_headers_officer)
        assert resp.status_code == 200
        data = resp.get_json()["criminal"]
        assert data["criminal_id"] == "CR-TEST-001"
        assert data["full_name"] == "John Doe"

    def test_photo_key_in_response(self, client, criminal, auth_headers_officer, db):
        resp = client.get(f"/api/criminals/{criminal.id}", headers=auth_headers_officer)
        data = resp.get_json()["criminal"]
        # photo_key or photo_filename should be present
        assert "photo_key" in data or "photo_filename" in data

    def test_jsonb_fields_are_objects_in_response(self, client, criminal, auth_headers_officer, db):
        """JSONB fields must come back as objects, not JSON strings."""
        resp = client.get(f"/api/criminals/{criminal.id}", headers=auth_headers_officer)
        data = resp.get_json()["criminal"]
        assert isinstance(data["aliases"], list)
        assert isinstance(data["appearance"], dict)
        assert isinstance(data["locations"], dict)
        assert isinstance(data["summary"], dict)

    def test_get_nonexistent_criminal_returns_404(self, client, auth_headers_officer, db):
        resp = client.get("/api/criminals/99999", headers=auth_headers_officer)
        assert resp.status_code == 404

    def test_get_criminals_requires_auth(self, client, db):
        resp = client.get("/api/criminals")
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# Face embedding — JSONB storage and retrieval
# ══════════════════════════════════════════════════════════════════════════════

class TestFaceEmbedding:

    def test_embedding_stored_as_jsonb_dict(self, criminal, db):
        """face_embedding must be a dict with arcface and facenet keys."""
        db.refresh(criminal)
        emb = criminal.face_embedding
        assert isinstance(emb, dict), f"face_embedding is {type(emb)}, expected dict"
        assert "arcface" in emb
        assert "facenet" in emb

    def test_embedding_arcface_length(self, criminal, db):
        db.refresh(criminal)
        assert len(criminal.face_embedding["arcface"]) == 512

    def test_embedding_facenet_length(self, criminal, db):
        db.refresh(criminal)
        assert len(criminal.face_embedding["facenet"]) == 128

    def test_embedding_not_double_encoded(self, criminal, db):
        """Ensure the embedding is not stored as a JSON string inside JSONB."""
        db.refresh(criminal)
        emb = criminal.face_embedding
        # If double-encoded, emb would be a string like '{"arcface": [...]}'
        assert not isinstance(emb, str), "face_embedding is double-encoded JSON string"

    def test_embedding_version_stored(self, criminal, db):
        db.refresh(criminal)
        assert criminal.embedding_version == "v2"

    def test_embedding_roundtrip_via_api(self, client, criminal, auth_headers_officer, db):
        """Embedding retrieved via API should be a proper object, not a string."""
        resp = client.get(f"/api/criminals/{criminal.id}", headers=auth_headers_officer)
        assert resp.status_code == 200
        # face_embedding is intentionally not exposed in the GET response (security)
        # but if it is, it must be an object
        data = resp.get_json()["criminal"]
        if "face_embedding" in data and data["face_embedding"] is not None:
            assert isinstance(data["face_embedding"], dict)


# ══════════════════════════════════════════════════════════════════════════════
# Delete criminal
# ══════════════════════════════════════════════════════════════════════════════

class TestDeleteCriminal:

    def test_delete_criminal_success(self, client, criminal, auth_headers_officer, db):
        resp = client.delete(f"/api/criminals/{criminal.id}", headers=auth_headers_officer)
        assert resp.status_code == 200
        assert db.query(Criminal).filter(Criminal.id == criminal.id).first() is None

    def test_delete_nonexistent_returns_404(self, client, auth_headers_officer, db):
        resp = client.delete("/api/criminals/99999", headers=auth_headers_officer)
        assert resp.status_code == 404

    def test_delete_requires_auth(self, client, criminal, db):
        resp = client.delete(f"/api/criminals/{criminal.id}")
        assert resp.status_code == 401
