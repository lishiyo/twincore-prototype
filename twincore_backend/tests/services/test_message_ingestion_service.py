"""Tests for MessageIngestionService."""

import asyncio
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from services.message_ingestion_service import MessageIngestionService
from services.ingestion_service import IngestionService, IngestionServiceError


@pytest.fixture
def mock_ingestion_service():
    """Mock IngestionService for testing."""
    service = AsyncMock(spec=IngestionService)
    return service


@pytest.fixture
def message_ingestion_service(mock_ingestion_service):
    """Create MessageIngestionService with mocked dependencies."""
    return MessageIngestionService(
        ingestion_service=mock_ingestion_service
    )


class TestMessageIngestionService:
    """Tests for MessageIngestionService."""

    @pytest.mark.asyncio
    async def test_ingest_message_success(self, message_ingestion_service, mock_ingestion_service):
        """Test successful message ingestion."""
        # Arrange
        message_data = {
            "text": "This is a test message",
            "source_type": "message",
            "user_id": str(uuid.uuid4()),
            "message_id": str(uuid.uuid4()),
            "project_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "is_twin_chat": False,
            "timestamp": datetime.now()
        }
        
        mock_ingestion_service.ingest_chunk.return_value = True
        
        # Act
        result = await message_ingestion_service.ingest_message(message_data)
        
        # Assert
        assert result is True
        mock_ingestion_service.ingest_chunk.assert_called_once()
        
        # Verify correct parameters were passed to ingest_chunk
        call_args = mock_ingestion_service.ingest_chunk.call_args[1]
        assert call_args["text_content"] == message_data["text"]
        assert call_args["source_type"] == "message"
        assert call_args["user_id"] == message_data["user_id"]
        assert call_args["message_id"] == message_data["message_id"]
        assert call_args["project_id"] == message_data["project_id"]
        assert call_args["session_id"] == message_data["session_id"]
        assert call_args["is_twin_interaction"] == message_data["is_twin_chat"]
        
        # Verify chunk_id is an string
        assert isinstance(call_args["chunk_id"], str)

    @pytest.mark.asyncio
    async def test_ingest_message_generates_message_id_if_not_provided(self, message_ingestion_service, mock_ingestion_service):
        """Test message ingestion generates message_id if not provided."""
        # Arrange
        message_data = {
            "text": "This is a test message",
            "source_type": "message",
            "user_id": str(uuid.uuid4()),
            "project_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "is_twin_chat": False,
        }
        
        mock_ingestion_service.ingest_chunk.return_value = True
        
        # Act
        result = await message_ingestion_service.ingest_message(message_data)
        
        # Assert
        assert result is True
        call_args = mock_ingestion_service.ingest_chunk.call_args[1]
        assert call_args["message_id"] is not None
        assert isinstance(call_args["message_id"], str)
        
        # Verify generated message_id is a valid UUID
        try:
            uuid.UUID(call_args["message_id"])
        except ValueError:
            pytest.fail(f"Generated message_id is not a valid UUID: {call_args['message_id']}")

    @pytest.mark.asyncio
    async def test_ingest_message_handles_ingestion_error(self, message_ingestion_service, mock_ingestion_service):
        """Test handling of ingestion service errors."""
        # Arrange
        message_data = {
            "text": "This is a test message",
            "source_type": "message",
            "user_id": str(uuid.uuid4()),
        }
        
        # Setup mock to raise an exception
        mock_ingestion_service.ingest_chunk.side_effect = IngestionServiceError("Test error")
        
        # Act & Assert
        with pytest.raises(IngestionServiceError):
            await message_ingestion_service.ingest_message(message_data)

    @pytest.mark.asyncio
    async def test_ingest_message_validates_required_fields(self, message_ingestion_service):
        """Test that message ingestion validates required fields."""
        # Arrange
        # Missing required field 'user_id'
        message_data = {
            "text": "This is a test message",
            "source_type": "message",
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="user_id"):
            await message_ingestion_service.ingest_message(message_data) 