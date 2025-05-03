"""Tests for the MessageIngestionService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime

from services.message_ingestion_service import MessageIngestionService, MessageIngestionServiceError
from services.ingestion_service import IngestionService, IngestionServiceError


@pytest.fixture
def mock_ingestion_service():
    """Create a mock IngestionService."""
    mock = MagicMock(spec=IngestionService)
    mock.ingest_chunk = AsyncMock()
    return mock


@pytest.fixture
def message_ingestion_service(mock_ingestion_service):
    """Create a MessageIngestionService with mocked dependencies."""
    return MessageIngestionService(mock_ingestion_service)


class TestMessageIngestionService:
    """Tests for the MessageIngestionService."""

    async def test_ingest_message_with_provided_id(self, message_ingestion_service, mock_ingestion_service):
        """Test ingesting a message with a provided message ID."""
        # Setup
        message_id = "test-message-id"
        content = "This is a test message"
        user_id = "test-user"
        project_id = "test-project"
        session_id = "test-session"
        timestamp = "2023-01-01T12:00:00"
        is_twin_interaction = True
        is_private = False
        metadata = {"key": "value"}

        # Execute
        result = await message_ingestion_service.ingest_message(
            message_id=message_id,
            content=content,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            timestamp=timestamp,
            is_twin_interaction=is_twin_interaction,
            is_private=is_private,
            metadata=metadata
        )

        # Assert
        mock_ingestion_service.ingest_chunk.assert_called_once_with(
            chunk_id=f"msg_{message_id}",
            text_content=content,
            source_type="message",
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            message_id=message_id,
            timestamp=timestamp,
            is_twin_interaction=is_twin_interaction,
            is_private=is_private,
            metadata=metadata
        )
        
        assert result["message_id"] == message_id
        assert result["chunk_id"] == f"msg_{message_id}"
        assert result["timestamp"] == timestamp
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ingest_message_with_generated_id(self, message_ingestion_service, mock_ingestion_service):
        """Test ingesting a message with a generated message ID."""
        # Setup
        content = "This is a test message"
        user_id = "test-user"
        
        # Execute
        with patch('uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
            result = await message_ingestion_service.ingest_message(
                message_id=None,
                content=content,
                user_id=user_id
            )

        # Assert
        expected_message_id = '12345678-1234-5678-1234-567812345678'
        mock_ingestion_service.ingest_chunk.assert_called_once()
        call_args = mock_ingestion_service.ingest_chunk.call_args[1]
        assert call_args["message_id"] == expected_message_id
        assert call_args["text_content"] == content
        assert call_args["user_id"] == user_id
        assert call_args["source_type"] == "message"
        
        assert result["message_id"] == expected_message_id
        assert result["chunk_id"] == f"msg_{expected_message_id}"
        assert "timestamp" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_ingest_message_error_handling(self, message_ingestion_service, mock_ingestion_service):
        """Test error handling when ingesting a message."""
        # Setup
        mock_ingestion_service.ingest_chunk.side_effect = IngestionServiceError("Test error")
        
        # Execute and Assert
        with pytest.raises(MessageIngestionServiceError) as excinfo:
            await message_ingestion_service.ingest_message(
                message_id="test-message-id",
                content="Test content",
                user_id="test-user"
            )
        
        assert "Failed to ingest message: Test error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_initialization_error(self, mock_ingestion_service):
        """Test initialization error when ingestion service is not provided."""
        # Execute and Assert
        with pytest.raises(ValueError) as excinfo:
            MessageIngestionService(None)
        
        assert "IngestionService must be provided" in str(excinfo.value) 