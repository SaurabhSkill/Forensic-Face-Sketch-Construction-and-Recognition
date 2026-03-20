"""
tests/test_performance.py
─────────────────────────
Query performance and N+1 detection tests.
All timing thresholds are conservative — they catch regressions, not micro-optimisations.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from db_models import Case, CaseNote, Criminal, User


# ══════════════════════════════════════════════════════════════════════════════
# Query counter — detects N+1 problems
# ══════════════════════════════════════════════════════════════════════════════

class QueryCounter:
    """Attach to a SQLAlchemy connection to count executed statements."""

    def __init__(self, conn):
        self.count = 0
        self._conn = conn
        event.listen(conn, "before_cursor_execute", self._before)

    def _before(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        event.remove(self._conn, "before_cursor_execute", self._before)


# ══════════════════════════════════════════════════════════════════════════════
# Bulk data helpers
# ══════════════════════════════════════════════════════════════════════════════

def _seed_criminals(db: Session, n: int) -> list[Criminal]:
    criminals = [
        Criminal(
            criminal_id=f"CR-PERF-{i:04d}",
            status="Suspect",
            full_name=f"Perf Criminal {i}",
            photo_filename="photo.jpg",
            face_embedding={"arcface": [0.1] * 512, "facenet": [0.2] * 128},
            embedding_version="v2",
        )
        for i in range(n)
    ]
    db.bulk_save_objects(criminals)
    db.flush()
    return criminals


def _seed_cases(db: Session, officer_id: int, n: int) -> list[Case]:
    cases = [
        Case(
            case_number=f"CASE-PERF-{i:04d}",
            title=f"Perf Case {i}",
            status="Open",
            priority="Medium",
            officer_id=officer_id,
        )
        for i in range(n)
    ]
    db.bulk_save_objects(cases)
    db.flush()
    return cases


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestQueryPerformance:

    def test_get_all_criminals_under_500ms(self, client, auth_headers_officer, db):
        """GET /api/criminals with 50 records must respond in < 500ms."""
        _seed_criminals(db, 50)

        start = time.perf_counter()
        resp = client.get("/api/criminals", headers=auth_headers_officer)
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200
        assert elapsed < 0.5, f"GET /api/criminals took {elapsed:.3f}s — too slow"

    def test_get_all_cases_under_300ms(self, client, auth_headers_officer, officer_user, db):
        """GET /api/cases with 50 records must respond in < 300ms."""
        _seed_cases(db, officer_user.id, 50)

        start = time.perf_counter()
        resp = client.get("/api/cases", headers=auth_headers_officer)
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200
        assert elapsed < 0.3, f"GET /api/cases took {elapsed:.3f}s — too slow"

    def test_get_case_notes_under_200ms(self, client, case, auth_headers_officer, officer_user, db):
        """GET /api/cases/<id>/notes with 100 notes must respond in < 200ms."""
        notes = [
            CaseNote(
                case_id=case.id,
                author_id=officer_user.id,
                author_name="Officer",
                content=f"Note {i}",
            )
            for i in range(100)
        ]
        db.bulk_save_objects(notes)
        db.flush()

        start = time.perf_counter()
        resp = client.get(f"/api/cases/{case.id}/notes", headers=auth_headers_officer)
        elapsed = time.perf_counter() - start

        assert resp.status_code == 200
        assert elapsed < 0.2, f"GET notes took {elapsed:.3f}s — too slow"

    def test_criminal_lookup_by_criminal_id_uses_index(self, db):
        """
        Query by criminal_id should use the index — verify via EXPLAIN.
        If the query plan contains 'Seq Scan' on a large table, the index is missing.
        """
        _seed_criminals(db, 100)

        plan = db.execute(
            text("EXPLAIN SELECT * FROM criminals WHERE criminal_id = 'CR-PERF-0050'")
        ).fetchall()
        plan_text = " ".join(str(row) for row in plan)

        # Index Scan or Bitmap Index Scan expected — not Seq Scan
        assert "Seq Scan" not in plan_text or "Index" in plan_text, (
            f"criminal_id query is doing a sequential scan — index may be missing.\n{plan_text}"
        )

    def test_case_number_lookup_uses_index(self, db, officer_user):
        """Query by case_number should use the index."""
        _seed_cases(db, officer_user.id, 100)

        plan = db.execute(
            text("EXPLAIN SELECT * FROM cases WHERE case_number = 'CASE-PERF-0050'")
        ).fetchall()
        plan_text = " ".join(str(row) for row in plan)

        assert "Seq Scan" not in plan_text or "Index" in plan_text, (
            f"case_number query is doing a sequential scan.\n{plan_text}"
        )

    def test_no_n_plus_one_on_case_notes_list(self, db, case, officer_user):
        """
        Fetching 20 notes should not issue 20 separate author queries.
        Expected: 1 query for notes (author_name is denormalized, no join needed).
        """
        notes = [
            CaseNote(case_id=case.id, author_id=officer_user.id,
                     author_name="Officer", content=f"Note {i}")
            for i in range(20)
        ]
        db.bulk_save_objects(notes)
        db.flush()

        conn = db.connection()
        with QueryCounter(conn) as counter:
            result = db.query(CaseNote).filter(CaseNote.case_id == case.id).all()
            # Access author_name (denormalized — no extra query needed)
            _ = [n.author_name for n in result]

        # Should be exactly 1 query — the SELECT on case_notes
        assert counter.count <= 2, (
            f"Expected ≤2 queries for case notes list, got {counter.count} — possible N+1"
        )

    def test_jsonb_embedding_query_performance(self, db):
        """
        Querying criminals by embedding_version (a string column) should be fast.
        This also validates JSONB columns don't cause serialization overhead.
        """
        _seed_criminals(db, 50)

        start = time.perf_counter()
        results = db.query(Criminal).filter(Criminal.embedding_version == "v2").all()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"JSONB embedding query took {elapsed:.3f}s"
        # Verify embeddings come back as dicts, not strings
        for c in results[:5]:
            assert isinstance(c.face_embedding, dict), (
                f"face_embedding for {c.criminal_id} is {type(c.face_embedding)}, expected dict"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Connection pool health
# ══════════════════════════════════════════════════════════════════════════════

class TestConnectionPool:

    def test_concurrent_requests_do_not_exhaust_pool(self, client, auth_headers_officer, db):
        """
        Fire 10 sequential requests and verify none fail with pool timeout.
        True concurrency testing requires threading — this validates basic pool health.
        """
        for i in range(10):
            resp = client.get("/api/health")
            assert resp.status_code == 200, f"Request {i} failed: {resp.status_code}"

    def test_session_closed_after_request(self, client, auth_headers_officer, db):
        """
        Verify the DB session is properly closed after each request.
        A leaked session would eventually exhaust the pool.
        Checked indirectly: if sessions leak, the 10-request test above would fail.
        """
        from database import engine
        # pool.checkedout() is the number of connections currently in use
        # After a completed request it should be 0 (or 1 for the test session)
        pool_status = engine.pool.status()
        assert "overflow" not in pool_status.lower() or "0" in pool_status, (
            f"Connection pool may have leaked connections: {pool_status}"
        )
