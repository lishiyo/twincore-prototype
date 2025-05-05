from fastapi.testclient import TestClient
from main import app
import pytest
from unittest.mock import AsyncMock, patch
import uuid

@pytest.fixture
def mock_preference_service():
    """Create a mock PreferenceService."""
    from api.routers import user_router
    from services.preference_service import PreferenceService
    
    service_instance = AsyncMock()
    service_instance.query_user_preference = AsyncMock()
    
    # Store the original dependency resolver
    original_dependency = app.dependency_overrides.get(user_router.get_preference_service)
    
    # Override the dependency with our mock
    app.dependency_overrides[user_router.get_preference_service] = lambda: service_instance
    
    yield service_instance
    
    # Restore the original dependency after the test
    if original_dependency:
        app.dependency_overrides[user_router.get_preference_service] = original_dependency
    else:
        del app.dependency_overrides[user_router.get_preference_service]

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

def test_get_user_preferences_success(
    client: TestClient,
    mock_preference_service
):
    """Test successful retrieval of user preferences."""
    # Setup test data
    user_id = "test-user-123"
    decision_topic = "dark mode"
    
    # Mock return value for query_user_preference
    mock_preference_service.query_user_preference.return_value = {
        "user_id": user_id,
        "decision_topic": decision_topic,
        "has_preferences": True,
        "preference_statements": [
            {
                "chunk_id": "chunk1",
                "text_content": "I prefer dark mode",
                "source_type": "message",
                "user_id": user_id,
                "source": "vector"
            }
        ],
        "graph_results_count": 0,
        "vector_results_count": 1
    }
    
    # Call the endpoint
    response = client.get(
        f"/v1/users/{user_id}/preferences",
        params={
            "decision_topic": decision_topic,
            "limit": 5
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["decision_topic"] == decision_topic
    assert data["has_preferences"] is True
    assert len(data["preference_statements"]) == 1
    assert data["preference_statements"][0]["text_content"] == "I prefer dark mode"
    
    # Verify service was called with correct parameters
    mock_preference_service.query_user_preference.assert_called_once()
    call_args = mock_preference_service.query_user_preference.call_args[1]
    assert call_args["user_id"] == user_id
    assert call_args["decision_topic"] == decision_topic

def test_get_user_preferences_missing_topic(
    client: TestClient
):
    """Test API response when decision_topic is missing."""
    user_id = "test-user-123"
    response = client.get(f"/v1/users/{user_id}/preferences")
    # Expect 422 Unprocessable Entity from FastAPI validation
    assert response.status_code == 422
    assert "decision_topic" in response.text

def test_get_user_preferences_include_messages_to_twin(
    client: TestClient,
    mock_preference_service
):
    """Test the preferences endpoint with include_messages_to_twin parameter."""
    user_id = "test-user-123"
    decision_topic = "dark mode"
    
    # Mock return value
    mock_preference_service.query_user_preference.return_value = {
        "user_id": user_id,
        "decision_topic": decision_topic,
        "has_preferences": True,
        "preference_statements": [],
        "graph_results_count": 0,
        "vector_results_count": 0
    }
    
    # Test with include_messages_to_twin=false
    response = client.get(
        f"/v1/users/{user_id}/preferences",
        params={
            "decision_topic": decision_topic,
            "include_messages_to_twin": "false"
        }
    )
    
    assert response.status_code == 200
    mock_preference_service.query_user_preference.assert_called_once()
    call_args = mock_preference_service.query_user_preference.call_args[1]
    assert call_args["include_messages_to_twin"] is False
    
    # Reset mock
    mock_preference_service.query_user_preference.reset_mock()
    
    # Test with default (should be true)
    response = client.get(
        f"/v1/users/{user_id}/preferences",
        params={
            "decision_topic": decision_topic
        }
    )
    
    assert response.status_code == 200
    mock_preference_service.query_user_preference.assert_called_once()
    call_args = mock_preference_service.query_user_preference.call_args[1]
    assert call_args["include_messages_to_twin"] is True 