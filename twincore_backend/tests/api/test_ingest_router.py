"""Tests for the ingestion API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
import uuid

from api.routers.ingest_router import router, get_message_ingestion_service
from services.message_ingestion_service import MessageIngestionService, MessageIngestionServiceError


@pytest.fixture
def mock_message_ingestion_service():
    """Create a mock MessageIngestionService."""
    mock = MagicMock(spec=MessageIngestionService)
    mock.ingest_message = AsyncMock()
    return mock


@pytest.fixture
def test_app(mock_message_ingestion_service):
    """Create a test FastAPI application with mocked dependencies."""
    app = FastAPI()
    
    # Override the dependency - now use the router function
    app.dependency_overrides[get_message_ingestion_service] = lambda: mock_message_ingestion_service
    
    # Include the ingest router
    app.include_router(router)
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the FastAPI application."""
    return TestClient(test_app)


class TestIngestRouter:
    """Tests for the ingestion API router."""

    def test_ingest_message_success(self, client, mock_message_ingestion_service):
        """Test successful message ingestion."""
        # Setup
        message_id = "test-message-id"
        chunk_id = f"msg_{message_id}"
        timestamp = "2023-01-01T12:00:00"
        
        mock_message_ingestion_service.ingest_message.return_value = {
            "message_id": message_id,
            "chunk_id": chunk_id,
            "timestamp": timestamp,
            "success": True
        }
        
        # Execute
        response = client.post(
            "/v1/api/ingest/message",
            json={
                "message_id": message_id,
                "content": "This is a test message",
                "user_id": "test-user",
                "project_id": "test-project",
                "session_id": "test-session",
                "is_twin_interaction": True,
                "is_private": False
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] == message_id
        assert data["chunk_id"] == chunk_id
        assert data["timestamp"] == timestamp
        assert data["success"] is True
        
        # Verify the service was called with correct arguments
        mock_message_ingestion_service.ingest_message.assert_called_once()
        call_kwargs = mock_message_ingestion_service.ingest_message.call_args[1]
        assert call_kwargs["message_id"] == message_id
        assert call_kwargs["content"] == "This is a test message"
        assert call_kwargs["user_id"] == "test-user"
        assert call_kwargs["project_id"] == "test-project"
        assert call_kwargs["session_id"] == "test-session"
        assert call_kwargs["is_twin_interaction"] is True
        assert call_kwargs["is_private"] is False

    def test_ingest_message_error(self, client, mock_message_ingestion_service):
        """Test error handling in message ingestion endpoint."""
        # Setup
        mock_message_ingestion_service.ingest_message.side_effect = MessageIngestionServiceError("Test error")
        
        # Execute
        response = client.post(
            "/v1/api/ingest/message",
            json={
                "content": "This is a test message",
                "user_id": "test-user"
            }
        )
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "Failed to ingest message: Test error" in data["detail"]

    def test_ingest_message_invalid_request(self, client):
        """Test validation for invalid request."""
        # Execute - missing required field 'user_id'
        response = client.post(
            "/v1/api/ingest/message",
            json={
                "content": "This is a test message"
                # Missing required user_id
            }
        )
        
        # Assert
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "Field required" in str(data)  # Fixed capitalization 