"""API tests for the retrieve router endpoints."""

import json
from datetime import datetime, timedelta
import pytest
from unittest.mock import patch, AsyncMock
import numpy as np

from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app
from api.routers import retrieve_router


@pytest.fixture
def mock_retrieval_service():
    """Create a mock RetrievalService."""
    service_instance = AsyncMock()
    service_instance.retrieve_context = AsyncMock()
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
    
    # Prepare the request payload
    payload = {
        "query_text": "test query",
        "project_id": "project-1",
        "session_id": "session-1",
        "limit": 10
    }
    
    # Act
    response = test_client.post("/v1/retrieve/context", json=payload)
    
    # Assert
    assert response.status_code == 200
    response_data = response.json()
    
    # Verify the service was called with the correct parameters
    mock_retrieval_service.retrieve_context.assert_called_once()
    call_args = mock_retrieval_service.retrieve_context.call_args[1]
    assert call_args["query_text"] == payload["query_text"]
    assert call_args["project_id"] == payload["project_id"]
    assert call_args["session_id"] == payload["session_id"]
    assert call_args["limit"] == payload["limit"]
    
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
    
    # Prepare the request payload
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
    # Missing required field (project_id)
    payload = {
        "query_text": "test query",
        "session_id": "session-1",
        "limit": 10
    }
    
    response = test_client.post("/v1/retrieve/context", json=payload)
    assert response.status_code == 422  # Unprocessable Entity (validation error)
    
    # Verify error message mentions the missing field
    assert "project_id" in response.text


def test_retrieve_private_memory_validation_error(test_client):
    """Test validation errors for the /retrieve/private_memory endpoint."""
    # Missing required field (user_id)
    payload = {
        "query_text": "test query",
        "project_id": "project-1",
        "limit": 5
    }
    
    response = test_client.post("/v1/retrieve/private_memory", json=payload)
    assert response.status_code == 422  # Unprocessable Entity (validation error)
    
    # Verify error message mentions the missing field
    assert "user_id" in response.text 