"""Tests for the ingest router endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi import status
from httpx import AsyncClient

from services.message_ingestion_service import MessageIngestionService
from api.routers import ingest_router


@pytest.fixture
def mock_message_ingestion_service():
    """Mock MessageIngestionService for testing."""
    service = AsyncMock(spec=MessageIngestionService)
    return service


class TestMessageIngestionEndpoint:
    """Tests for the message ingestion endpoint."""

    def test_ingest_message_success(self, client, mock_message_ingestion_service):
        """Test successful message ingestion."""
        # Arrange
        mock_message_ingestion_service.ingest_message.return_value = True
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_message_ingestion_service] = lambda: mock_message_ingestion_service
        
        # Test data
        message_data = {
            "text": "This is a test message",
            "source_type": "message",
            "user_id": str(uuid.uuid4()),
            "project_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "message_id": str(uuid.uuid4()),
            "is_twin_chat": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Act
        response = client.post("/v1/api/ingest/message", json=message_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "success", "message": "Message ingested successfully"}
        mock_message_ingestion_service.ingest_message.assert_called_once()
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_message_without_optional_fields(self, client, mock_message_ingestion_service):
        """Test message ingestion with only required fields."""
        # Arrange
        mock_message_ingestion_service.ingest_message.return_value = True
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_message_ingestion_service] = lambda: mock_message_ingestion_service
        
        # Test data with only required fields
        message_data = {
            "text": "This is a test message",
            "source_type": "message",  # This field is required by ContentBase
            "user_id": str(uuid.uuid4())
        }
        
        # Act
        response = client.post("/v1/api/ingest/message", json=message_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        mock_message_ingestion_service.ingest_message.assert_called_once()
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_message_missing_required_fields(self, client, mock_message_ingestion_service):
        """Test message ingestion fails with missing required fields."""
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_message_ingestion_service] = lambda: mock_message_ingestion_service
        
        # Test data missing required user_id
        message_data = {
            "text": "This is a test message",
            "source_type": "message"  # Include source_type but not user_id
        }
        
        # Act
        response = client.post("/v1/api/ingest/message", json=message_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_message_service_error(self, client, mock_message_ingestion_service):
        """Test handling of service errors during message ingestion."""
        # Arrange
        mock_message_ingestion_service.ingest_message.side_effect = Exception("Test error")
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_message_ingestion_service] = lambda: mock_message_ingestion_service
        
        # Test data
        message_data = {
            "text": "This is a test message",
            "source_type": "message",  # This field is required by ContentBase
            "user_id": str(uuid.uuid4())
        }
        
        # Act
        response = client.post("/v1/api/ingest/message", json=message_data)
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()["detail"]
        
        # Clean up
        app.dependency_overrides.clear() 