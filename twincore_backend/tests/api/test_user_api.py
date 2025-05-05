from fastapi.testclient import TestClient
from main import app
import pytest

def test_get_user_context_success(
    client: TestClient
):
    test_user_id = "test_user_id"
    """Test successful retrieval of user context via API."""
    query_text = "what did i say about project X?"
    response = client.get(
        f"/v1/users/{test_user_id}/context",
        params={
            "query_text": query_text,
            "limit": 5,
            "include_private": True,
            "include_messages_to_twin": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "chunks" in data
    assert "total" in data
    assert isinstance(data["chunks"], list)
    assert isinstance(data["total"], int)
    # Further schema validation could be added here if needed

def test_get_user_context_missing_query(
    client: TestClient
):
    test_user_id = "test_user_id"
    """Test API response when query_text is missing."""
    response = client.get(f"/v1/users/{test_user_id}/context")
    # Expect 422 Unprocessable Entity from FastAPI validation
    assert response.status_code == 422 