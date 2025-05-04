"""API tests for the retrieve router endpoints."""

import json
from datetime import datetime, timedelta
import pytest
from unittest.mock import patch, AsyncMock
import numpy as np
from urllib.parse import urlencode
import uuid

from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app
from api.routers import retrieve_router


@pytest.fixture
def mock_retrieval_service():
    """Create a mock RetrievalService."""
    service_instance = AsyncMock()
    service_instance.retrieve_context = AsyncMock()
    service_instance.retrieve_enriched_context = AsyncMock()
    service_instance.retrieve_related_content = AsyncMock()
    service_instance.retrieve_by_topic = AsyncMock()
    # Store the original dependency resolver
    original_dependency = app.dependency_overrides.get(retrieve_router.get_retrieval_service)
    
    # Override the dependency with our mock
    app.dependency_overrides[retrieve_router.get_retrieval_service] = lambda: service_instance
    
    yield service_instance
    
    # Restore the original dependency after the test
    if original_dependency:
        app.dependency_overrides[retrieve_router.get_retrieval_service] = original_dependency
    else:
        del app.dependency_overrides[retrieve_router.get_retrieval_service]


@pytest.fixture
def mock_retrieval_service_with_message_connector():
    """Create a mock RetrievalService with message connector capabilities."""
    service_instance = AsyncMock()
    service_instance.retrieve_private_memory = AsyncMock()
    
    # Store the original dependency resolver
    original_dependency = app.dependency_overrides.get(retrieve_router.get_retrieval_service_with_message_connector)
    
    # Override the dependency with our mock
    app.dependency_overrides[retrieve_router.get_retrieval_service_with_message_connector] = lambda: service_instance
    
    yield service_instance
    
    # Restore the original dependency after the test
    if original_dependency:
        app.dependency_overrides[retrieve_router.get_retrieval_service_with_message_connector] = original_dependency
    else:
        del app.dependency_overrides[retrieve_router.get_retrieval_service_with_message_connector]


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


def test_retrieve_context_endpoint(test_client, mock_retrieval_service):
    """Test the /retrieve/context endpoint."""
    # Arrange
    now = datetime.now()
    # Use real UUIDs rather than plain strings
    test_project_id = str(uuid.uuid4())
    test_session_id = str(uuid.uuid4())
    test_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "This is test content 1",
            "source_type": "message",
            "user_id": "user-1",
            "project_id": test_project_id,
            "session_id": test_session_id,
            "timestamp": now.timestamp(),
            "score": 0.95,
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_context.return_value = test_results
    
    # Prepare query parameters with valid UUIDs
    query_params = {
        "query_text": "test query",
        "project_id": test_project_id,
        "session_id": test_session_id,
        "limit": 10,
        "include_messages_to_twin": True
    }
    
    # Act - Use query parameters directly
    response = test_client.get("/v1/retrieve/context", params=query_params)
    
    # Print the response body for debugging
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    
    # Verify the service was called with the correct parameters
    mock_retrieval_service.retrieve_context.assert_called_once()
    call_args = mock_retrieval_service.retrieve_context.call_args[1]
    assert call_args["query_text"] == query_params["query_text"]
    assert call_args["project_id"] == query_params["project_id"]
    assert call_args["session_id"] == query_params["session_id"]
    assert call_args["limit"] == query_params["limit"]
    assert call_args["include_messages_to_twin"] == query_params["include_messages_to_twin"]
    
    # Verify response structure
    assert "chunks" in response_data
    assert "total" in response_data
    assert response_data["total"] == 1
    
    # Verify first chunk contents
    chunk = response_data["chunks"][0]
    assert chunk["chunk_id"] == "test-id-1"
    assert chunk["text"] == "This is test content 1"
    assert chunk["source_type"] == "message"
    assert chunk["user_id"] == "user-1"
    assert chunk["project_id"] == test_project_id
    assert chunk["session_id"] == test_session_id
    assert chunk["score"] == 0.95


def test_retrieve_context_default_include_messages_to_twin(test_client, mock_retrieval_service):
    """Test the /retrieve/context endpoint with default include_messages_to_twin parameter."""
    # Arrange
    test_project_id = str(uuid.uuid4())
    test_session_id = str(uuid.uuid4())
    test_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "This is test content 1",
            "source_type": "message",
            "user_id": "user-1",
            "project_id": test_project_id,
            "session_id": test_session_id,
            "timestamp": datetime.now().timestamp(),
            "score": 0.95,
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_context.return_value = test_results
    
    # Prepare query parameters without include_messages_to_twin
    query_params = {
        "query_text": "test query",
        "project_id": test_project_id,
        "session_id": test_session_id,
    }
    
    # Act
    response = test_client.get("/v1/retrieve/context", params=query_params)
    
    # Assert
    assert response.status_code == 200
    
    # Verify the service was called with the correct default parameter
    mock_retrieval_service.retrieve_context.assert_called_once()
    call_args = mock_retrieval_service.retrieve_context.call_args[1]
    
    # Default for context endpoint should be False
    assert call_args["include_messages_to_twin"] is False


def test_retrieve_private_memory_endpoint(test_client, mock_retrieval_service_with_message_connector):
    """Test the /v1/retrieve/private_memory endpoint."""
    # Arrange
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    now = datetime.now()
    test_results = [
        {
            "chunk_id": "private-chunk-1",
            "text_content": "This is private content",
            "source_type": "document",
            "user_id": user_id,
            "project_id": project_id,
            "timestamp": now.timestamp(),
            "is_private": True,
            "score": 0.88,
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service_with_message_connector.retrieve_private_memory.return_value = test_results
    
    # Prepare the request payload - still using POST for private_memory since it has side effects
    payload = {
        "user_id": user_id,
        "query_text": "find my private notes",
        "project_id": project_id,
        "limit": 5,
        "include_messages_to_twin": False
    }
    
    # Act
    response = test_client.post("/v1/retrieve/private_memory", json=payload)
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    
    # Verify the service was called with the correct parameters
    mock_retrieval_service_with_message_connector.retrieve_private_memory.assert_called_once()
    call_args = mock_retrieval_service_with_message_connector.retrieve_private_memory.call_args[1]
    assert call_args["query_text"] == payload["query_text"]
    assert call_args["user_id"] == payload["user_id"]
    assert call_args["project_id"] == payload["project_id"]
    assert call_args["limit"] == payload["limit"]
    assert call_args["include_messages_to_twin"] == payload["include_messages_to_twin"]
    
    # Verify response structure
    assert "chunks" in response_data
    assert "total" in response_data
    assert response_data["total"] == 1
    
    # Verify first chunk contents
    chunk = response_data["chunks"][0]
    assert chunk["chunk_id"] == "private-chunk-1"
    assert chunk["text"] == "This is private content"
    assert chunk["source_type"] == "document"
    assert chunk["user_id"] == user_id
    assert chunk["project_id"] == project_id
    assert chunk["score"] == 0.88


def test_retrieve_private_memory_default_include_messages_to_twin(test_client, mock_retrieval_service_with_message_connector):
    """Test the /v1/retrieve/private_memory endpoint with default include_messages_to_twin parameter."""
    # Arrange
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    test_results = [
        {
            "chunk_id": "private-chunk-1",
            "text_content": "This is private content",
            "source_type": "document",
            "user_id": user_id,
            "project_id": project_id,
            "timestamp": datetime.now().timestamp(),
            "is_private": True,
            "score": 0.88,
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service_with_message_connector.retrieve_private_memory.return_value = test_results
    
    # Prepare the request payload without include_messages_to_twin
    payload = {
        "user_id": user_id,
        "query_text": "find my private notes",
        "project_id": project_id,
        "limit": 5
    }
    
    # Act
    response = test_client.post("/v1/retrieve/private_memory", json=payload)
    
    # Assert
    assert response.status_code == 200
    
    # Verify the service was called with the correct default parameter
    mock_retrieval_service_with_message_connector.retrieve_private_memory.assert_called_once()
    call_args = mock_retrieval_service_with_message_connector.retrieve_private_memory.call_args[1]
    
    # Default for private_memory endpoint should be True
    assert call_args["include_messages_to_twin"] is True


def test_retrieve_context_validation_error(test_client):
    """Test validation errors for the /retrieve/context endpoint."""
    # Missing required query_text parameter
    response = test_client.get("/v1/retrieve/context")
    assert response.status_code == 422  # Unprocessable Entity (validation error)
    
    # Verify error message mentions the missing field
    assert "query_text" in response.text


def test_retrieve_context_with_graph_data(test_client, mock_retrieval_service):
    """Test the /retrieve/context endpoint with graph enrichment."""
    # Arrange
    now = datetime.now()
    # Use real UUIDs rather than plain strings
    test_project_id = str(uuid.uuid4())
    test_session_id = str(uuid.uuid4())
    test_user1_id = str(uuid.uuid4())
    test_user2_id = str(uuid.uuid4())
    test_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "This is test content 1",
            "source_type": "message",
            "user_id": test_user1_id,
            "project_id": test_project_id,
            "session_id": test_session_id,
            "timestamp": now.timestamp(),
            "score": 0.95,
            "project_context": {
                "session_count": 3,
                "document_count": 5,
                "user_count": 2
            },
            "session_participants": [
                {"user_id": test_user1_id, "name": "Test User 1"},
                {"user_id": test_user2_id, "name": "Test User 2"}
            ]
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_enriched_context.return_value = test_results
    
    # Prepare query parameters
    query_params = {
        "query_text": "test query",
        "project_id": test_project_id,
        "session_id": test_session_id,
        "include_graph": True
    }
    
    # Act - Use query parameters directly
    response = test_client.get("/v1/retrieve/context", params=query_params)
    
    # Print response details for debugging
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    
    # Verify the service was called with the correct parameters
    mock_retrieval_service.retrieve_enriched_context.assert_called_once()
    call_args = mock_retrieval_service.retrieve_enriched_context.call_args[1]
    assert call_args["query_text"] == query_params["query_text"]
    assert call_args["project_id"] == query_params["project_id"]
    assert call_args["session_id"] == query_params["session_id"]
    
    # Verify response structure
    assert "chunks" in response_data
    assert "total" in response_data
    assert response_data["total"] == 1
    
    # Verify first chunk contents including graph data
    chunk = response_data["chunks"][0]
    assert chunk["chunk_id"] == "test-id-1"
    assert chunk["text"] == "This is test content 1"
    assert "metadata" in chunk
    print(f"Chunk metadata: {chunk['metadata']}")
    assert "project_context" in chunk["metadata"]
    assert "session_participants" in chunk["metadata"]
    assert chunk["metadata"]["project_context"]["session_count"] == 3


def test_retrieve_related_content_endpoint(test_client, mock_retrieval_service):
    """Test the /retrieve/related_content endpoint."""
    # Arrange
    now = datetime.now()
    source_chunk_id = str(uuid.uuid4())
    related_chunk_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    topic_id = str(uuid.uuid4())
    test_results = [
        {
            "chunk_id": related_chunk_id,
            "text_content": "This is related content",
            "source_type": "message",
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "timestamp": now.timestamp(),
            "outgoing_relationships": [
                {"type": "MENTIONS", "target_id": topic_id, "target_type": "Topic"}
            ],
            "incoming_relationships": []
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_related_content.return_value = test_results
    
    # Prepare query parameters
    query_params = {
        "chunk_id": source_chunk_id,
        "limit": 5,
        "max_depth": 2,
        "relationship_types": ["MENTIONS", "SIMILAR_TO"]
    }
    
    # Act - Use query parameters directly with relationship_types as a list
    response = test_client.get("/v1/retrieve/related_content", params={
        "chunk_id": query_params["chunk_id"],
        "limit": query_params["limit"],
        "max_depth": query_params["max_depth"],
        "relationship_types": query_params["relationship_types"]
    })
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    
    # Verify the service was called with the correct parameters
    mock_retrieval_service.retrieve_related_content.assert_called_once()
    call_args = mock_retrieval_service.retrieve_related_content.call_args[1]
    assert call_args["chunk_id"] == query_params["chunk_id"]
    assert call_args["limit"] == query_params["limit"]
    assert call_args["max_depth"] == query_params["max_depth"]
    assert sorted(call_args["relationship_types"]) == sorted(query_params["relationship_types"])
    
    # Verify response structure
    assert "chunks" in response_data
    assert "total" in response_data
    assert response_data["total"] == 1
    
    # Verify chunk contents including relationship data
    chunk = response_data["chunks"][0]
    assert chunk["chunk_id"] == related_chunk_id
    assert chunk["text"] == "This is related content"
    assert "metadata" in chunk
    assert "outgoing_relationships" in chunk["metadata"]
    assert len(chunk["metadata"]["outgoing_relationships"]) == 1
    assert chunk["metadata"]["outgoing_relationships"][0]["type"] == "MENTIONS"


def test_retrieve_by_topic_endpoint(test_client, mock_retrieval_service):
    """Test the /retrieve/topic endpoint."""
    # Arrange
    now = datetime.now()
    topic_name = "test-topic"
    chunk_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    test_results = [
        {
            "chunk_id": chunk_id,
            "text_content": "This content mentions a topic",
            "source_type": "message",
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "timestamp": now.timestamp(),
            "score": 0.92,
            "topic": {
                "name": topic_name,
                "description": "This is a test topic"
            }
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_by_topic.return_value = test_results
    
    # Prepare query parameters
    query_params = {
        "topic_name": topic_name,
        "limit": 5,
        "user_id": user_id,
        "project_id": project_id
    }
    
    # Act - Use query parameters directly
    response = test_client.get("/v1/retrieve/topic", params=query_params)
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    
    # Verify the service was called with the correct parameters
    mock_retrieval_service.retrieve_by_topic.assert_called_once()
    call_args = mock_retrieval_service.retrieve_by_topic.call_args[1]
    assert call_args["topic_name"] == query_params["topic_name"]
    assert call_args["limit"] == query_params["limit"]
    assert call_args["user_id"] == query_params["user_id"]
    assert call_args["project_id"] == query_params["project_id"]
    
    # Verify response structure
    assert "chunks" in response_data
    assert "total" in response_data
    assert response_data["total"] == 1
    
    # Verify chunk contents including topic data
    chunk = response_data["chunks"][0]
    assert chunk["chunk_id"] == chunk_id
    assert chunk["text"] == "This content mentions a topic"
    assert "metadata" in chunk
    assert "topic" in chunk["metadata"]
    assert chunk["metadata"]["topic"]["name"] == topic_name


@pytest.fixture
def mock_preference_service():
    """Create a mock PreferenceService."""
    service_instance = AsyncMock()
    service_instance.query_user_preference = AsyncMock()
    
    # Store the original dependency resolver
    original_dependency = app.dependency_overrides.get(retrieve_router.get_preference_service)
    
    # Override the dependency with our mock
    app.dependency_overrides[retrieve_router.get_preference_service] = lambda: service_instance
    
    yield service_instance
    
    # Restore the original dependency after the test
    if original_dependency:
        app.dependency_overrides[retrieve_router.get_preference_service] = original_dependency
    else:
        del app.dependency_overrides[retrieve_router.get_preference_service]


def test_retrieve_preferences_endpoint(test_client, mock_preference_service):
    """Test the preferences retrieval endpoint."""
    # Create mock preference data with valid UUIDs
    test_user_id = str(uuid.uuid4())
    test_chunk_1 = str(uuid.uuid4())
    test_chunk_2 = str(uuid.uuid4())
    decision_topic = "dark mode"
    
    mock_preferences = {
        "user_id": test_user_id,
        "decision_topic": decision_topic,
        "has_preferences": True,
        "preference_statements": [
            {
                "chunk_id": test_chunk_1,
                "text_content": "I prefer dark mode for all my apps.",
                "source_type": "message",
                "user_id": test_user_id,
                "score": 0.95,
                "source": "vector"
            },
            {
                "chunk_id": test_chunk_2,
                "text_content": "Dark mode is easier on my eyes at night.",
                "source_type": "message",
                "user_id": test_user_id,
                "source": "graph"
            }
        ],
        "graph_results_count": 1,
        "vector_results_count": 1
    }
    
    # Configure the mock to return test results
    mock_preference_service.query_user_preference.return_value = mock_preferences
    
    # Call the endpoint with individual parameters
    response = test_client.get(
        "/v1/retrieve/preferences",
        params={
            "user_id": test_user_id,
            "decision_topic": decision_topic,
            "limit": 5
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user_id
    assert data["decision_topic"] == decision_topic
    assert data["has_preferences"] is True
    assert len(data["preference_statements"]) == 2
    assert data["graph_results_count"] == 1
    assert data["vector_results_count"] == 1 


def test_retrieve_preferences_with_include_messages_to_twin_param(test_client, mock_preference_service):
    """Test the preferences retrieval endpoint with include_messages_to_twin parameter."""
    # Create mock preference data with valid UUIDs
    test_user_id = str(uuid.uuid4())
    test_chunk_1 = str(uuid.uuid4())
    test_chunk_2 = str(uuid.uuid4())
    decision_topic = "dark mode"
    
    mock_preferences = {
        "user_id": test_user_id,
        "decision_topic": decision_topic,
        "has_preferences": True,
        "preference_statements": [
            {
                "chunk_id": test_chunk_1,
                "text_content": "I prefer dark mode for all my apps.",
                "source_type": "message",
                "user_id": test_user_id,
                "score": 0.95,
                "source": "vector"
            },
            {
                "chunk_id": test_chunk_2,
                "text_content": "Dark mode is easier on my eyes at night.",
                "source_type": "message",
                "user_id": test_user_id,
                "source": "graph"
            }
        ],
        "graph_results_count": 1,
        "vector_results_count": 1
    }
    
    # Configure the mock to return test results
    mock_preference_service.query_user_preference.return_value = mock_preferences
    
    # Call the endpoint with include_messages_to_twin = False (override default)
    response = test_client.get(
        "/v1/retrieve/preferences",
        params={
            "user_id": test_user_id,
            "decision_topic": decision_topic,
            "limit": 5,
            "include_messages_to_twin": "false"  # String param from URL
        }
    )
    
    # Verify response
    assert response.status_code == 200
    
    # Verify service was called with correct parameter
    mock_preference_service.query_user_preference.assert_called_once()
    call_args = mock_preference_service.query_user_preference.call_args[1]
    assert call_args["include_messages_to_twin"] is False


def test_retrieve_preferences_default_include_messages_to_twin(test_client, mock_preference_service):
    """Test the preferences retrieval endpoint with default include_messages_to_twin parameter."""
    # Create mock preference data with valid UUIDs
    test_user_id = str(uuid.uuid4())
    decision_topic = "dark mode"
    
    mock_preferences = {
        "user_id": test_user_id,
        "decision_topic": decision_topic,
        "has_preferences": True,
        "preference_statements": [],
        "graph_results_count": 0,
        "vector_results_count": 0
    }
    
    # Configure the mock to return test results
    mock_preference_service.query_user_preference.return_value = mock_preferences
    
    # Call the endpoint without specifying include_messages_to_twin
    response = test_client.get(
        "/v1/retrieve/preferences",
        params={
            "user_id": test_user_id,
            "decision_topic": decision_topic,
            "limit": 5
        }
    )
    
    # Verify response
    assert response.status_code == 200
    
    # Verify service was called with correct default parameter
    mock_preference_service.query_user_preference.assert_called_once()
    call_args = mock_preference_service.query_user_preference.call_args[1]
    
    # Default for preferences endpoint should be True
    assert call_args["include_messages_to_twin"] is True 