"""API tests for the retrieve router endpoints."""

import json
from datetime import datetime, timedelta
import pytest
from unittest.mock import patch, AsyncMock
import numpy as np
from urllib.parse import urlencode

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
    test_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "This is test content 1",
            "source_type": "message",
            "user_id": "user-1",
            "project_id": "project-1",
            "session_id": "session-1",
            "timestamp": now.timestamp(),
            "score": 0.95,
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_context.return_value = test_results
    
    # Prepare query parameters
    query_params = {
        "query_text": "test query",
        "project_id": "project-1",
        "session_id": "session-1",
        "limit": 10
    }
    
    # Act
    response = test_client.get(f"/v1/retrieve/context?{urlencode(query_params)}")
    
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
    assert chunk["project_id"] == "project-1"
    assert chunk["session_id"] == "session-1"
    assert chunk["score"] == 0.95


def test_retrieve_private_memory_endpoint(test_client, mock_retrieval_service_with_message_connector):
    """Test the /v1/retrieve/private_memory endpoint."""
    # Arrange
    user_id = "user-1"
    now = datetime.now()
    test_results = [
        {
            "chunk_id": "private-chunk-1",
            "text_content": "This is private content",
            "source_type": "document",
            "user_id": user_id,
            "project_id": "project-1",
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
        "project_id": "project-1",
        "limit": 5
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
    assert chunk["project_id"] == "project-1"
    assert chunk["score"] == 0.88


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
    test_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "This is test content 1",
            "source_type": "message",
            "user_id": "user-1",
            "project_id": "project-1",
            "session_id": "session-1",
            "timestamp": now.timestamp(),
            "score": 0.95,
            "project_context": {
                "session_count": 3,
                "document_count": 5,
                "user_count": 2
            },
            "session_participants": [
                {"user_id": "user-1", "name": "Test User 1"},
                {"user_id": "user-2", "name": "Test User 2"}
            ]
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_enriched_context.return_value = test_results
    
    # Prepare query parameters
    query_params = {
        "query_text": "test query",
        "project_id": "project-1",
        "session_id": "session-1",
        "include_graph": True
    }
    
    # Act
    response = test_client.get(f"/v1/retrieve/context?{urlencode(query_params)}")
    
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
    assert "project_context" in chunk["metadata"]
    assert "session_participants" in chunk["metadata"]
    assert chunk["metadata"]["project_context"]["session_count"] == 3


def test_retrieve_related_content_endpoint(test_client, mock_retrieval_service):
    """Test the /retrieve/related_content endpoint."""
    # Arrange
    now = datetime.now()
    test_results = [
        {
            "chunk_id": "related-chunk-1",
            "text_content": "This is related content",
            "source_type": "message",
            "user_id": "user-1",
            "project_id": "project-1",
            "session_id": "session-1",
            "timestamp": now.timestamp(),
            "outgoing_relationships": [
                {"type": "MENTIONS", "target_id": "topic-1", "target_type": "Topic"}
            ],
            "incoming_relationships": []
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_related_content.return_value = test_results
    
    # Prepare query parameters
    query_params = {
        "chunk_id": "source-chunk-id",
        "limit": 5,
        "max_depth": 2,
        "relationship_types": ["MENTIONS", "SIMILAR_TO"]
    }
    
    # Act - use array notation for multiple values of the same parameter
    url = "/v1/retrieve/related_content"
    url += f"?chunk_id={query_params['chunk_id']}&limit={query_params['limit']}&max_depth={query_params['max_depth']}"
    url += f"&relationship_types={query_params['relationship_types'][0]}&relationship_types={query_params['relationship_types'][1]}"
    
    response = test_client.get(url)
    
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
    assert chunk["chunk_id"] == "related-chunk-1"
    assert chunk["text"] == "This is related content"
    assert "metadata" in chunk
    assert "outgoing_relationships" in chunk["metadata"]
    assert len(chunk["metadata"]["outgoing_relationships"]) == 1
    assert chunk["metadata"]["outgoing_relationships"][0]["type"] == "MENTIONS"


def test_retrieve_by_topic_endpoint(test_client, mock_retrieval_service):
    """Test the /retrieve/topic endpoint."""
    # Arrange
    now = datetime.now()
    test_results = [
        {
            "chunk_id": "topic-chunk-1",
            "text_content": "This content mentions a topic",
            "source_type": "message",
            "user_id": "user-1",
            "project_id": "project-1",
            "session_id": "session-1",
            "timestamp": now.timestamp(),
            "score": 0.92,
            "topic": {
                "name": "test-topic",
                "description": "This is a test topic"
            }
        }
    ]
    
    # Configure the mock to return test results
    mock_retrieval_service.retrieve_by_topic.return_value = test_results
    
    # Prepare query parameters
    query_params = {
        "topic_name": "test-topic",
        "limit": 5,
        "user_id": "user-1",
        "project_id": "project-1"
    }
    
    # Act
    response = test_client.get(f"/v1/retrieve/topic?{urlencode(query_params)}")
    
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
    assert chunk["chunk_id"] == "topic-chunk-1"
    assert chunk["text"] == "This content mentions a topic"
    assert "metadata" in chunk
    assert "topic" in chunk["metadata"]
    assert chunk["metadata"]["topic"]["name"] == "test-topic" 