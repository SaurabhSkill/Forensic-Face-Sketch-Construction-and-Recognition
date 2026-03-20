"""
tests/test_health.py
────────────────────
Health check endpoint tests.
"""

from __future__ import annotations

from datetime import datetime, timezone


class TestHealthCheck:

    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_response_structure(self, client):
        data = client.get("/api/health").get_json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data

    def test_health_timestamp_is_valid_iso(self, client):
        data = client.get("/api/health").get_json()
        # Should parse without raising
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))

    def test_health_no_auth_required(self, client):
        """Health endpoint must be publicly accessible (no token needed)."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
