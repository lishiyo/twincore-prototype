"""Tests for the main application endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test that the root endpoint returns the expected response."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "TwinCore API" 