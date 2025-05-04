"""Tests for DocumentConnector."""

import asyncio
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from ingestion.connectors.document_connector import DocumentConnector
from ingestion.processors.text_chunker import TextChunker
from services.ingestion_service import IngestionService, IngestionServiceError


@pytest.fixture
def mock_ingestion_service():
    """Mock IngestionService for testing."""
    service = AsyncMock(spec=IngestionService)
    return service


@pytest.fixture
def mock_text_chunker():
    """Mock TextChunker for testing."""
    chunker = MagicMock(spec=TextChunker)
    # Default behavior: split text into 3 chunks
    chunker.chunk_text.return_value = [
        "This is the first chunk of the document.",
        "This is the second chunk with some more text.",
        "This is the final chunk of the document."
    ]
    return chunker


@pytest.fixture
def document_connector(mock_ingestion_service, mock_text_chunker):
    """Create DocumentConnector with mocked dependencies."""
    return DocumentConnector(
        ingestion_service=mock_ingestion_service,
        text_chunker=mock_text_chunker
    )


class TestDocumentConnector:
    """Tests for DocumentConnector."""

    @pytest.mark.asyncio
    async def test_ingest_document_success(self, document_connector, mock_ingestion_service, mock_text_chunker):
        """Test successful document ingestion."""
        # Arrange
        document_data = {
            "text": "This is a test document with multiple paragraphs.\n\nIt should be chunked appropriately.",
            "source_type": "document",
            "doc_name": "Test Document.pdf",
            "user_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "project_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "is_private": True,
            "timestamp": datetime.now()
        }
        
        mock_ingestion_service.ingest_chunk.return_value = True
        
        # Act
        result = await document_connector.ingest_document(document_data)
        
        # Assert
        assert result is True
        
        # Verify text chunker was called with correct parameters
        mock_text_chunker.chunk_text.assert_called_once_with(
            text=document_data["text"],
            chunk_size=1000,
            overlap=200,
            respect_paragraphs=True
        )
        
        # Verify ingest_chunk was called once for each chunk
        assert mock_ingestion_service.ingest_chunk.call_count == 3
        
        # Check parameters for one of the calls
        call_kwargs = mock_ingestion_service.ingest_chunk.call_args_list[0][1]
        assert call_kwargs["source_type"] == "document_chunk"
        assert call_kwargs["doc_id"] == document_data["doc_id"]
        assert call_kwargs["doc_name"] == document_data["doc_name"]
        assert call_kwargs["user_id"] == document_data["user_id"]
        assert call_kwargs["project_id"] == document_data["project_id"]
        assert call_kwargs["session_id"] == document_data["session_id"]
        assert call_kwargs["is_private"] == document_data["is_private"]
        assert call_kwargs["is_twin_interaction"] is False
        
        # Verify metadata was properly set
        assert call_kwargs["metadata"]["original_document"] == document_data["doc_name"]
        assert call_kwargs["metadata"]["chunk_index"] == 0
        assert call_kwargs["metadata"]["total_chunks"] == 3

    @pytest.mark.asyncio
    async def test_ingest_document_generates_doc_id_if_not_provided(self, document_connector, mock_ingestion_service, mock_text_chunker):
        """Test document ingestion generates doc_id if not provided."""
        # Arrange
        document_data = {
            "text": "This is a test document.",
            "source_type": "document",
            "doc_name": "Test Document.pdf",
            "user_id": str(uuid.uuid4()),
        }
        
        mock_ingestion_service.ingest_chunk.return_value = True
        
        # Act
        result = await document_connector.ingest_document(document_data)
        
        # Assert
        assert result is True
        
        # Check doc_id in first call
        call_kwargs = mock_ingestion_service.ingest_chunk.call_args_list[0][1]
        assert call_kwargs["doc_id"] is not None
        assert isinstance(call_kwargs["doc_id"], str)
        
        # Verify generated doc_id is a valid UUID
        try:
            uuid.UUID(call_kwargs["doc_id"])
        except ValueError:
            pytest.fail(f"Generated doc_id is not a valid UUID: {call_kwargs['doc_id']}")

    @pytest.mark.asyncio
    async def test_ingest_document_empty_chunks(self, document_connector, mock_ingestion_service, mock_text_chunker):
        """Test document ingestion with empty chunks result."""
        # Arrange
        document_data = {
            "text": "Empty document",
            "source_type": "document",
            "doc_name": "Empty.txt",
        }
        
        # Mock empty chunks result
        mock_text_chunker.chunk_text.return_value = []
        mock_ingestion_service.ingest_chunk.return_value = True
        
        # Act
        result = await document_connector.ingest_document(document_data)
        
        # Assert
        assert result is True
        
        # Should fall back to using the original text as a single chunk
        mock_ingestion_service.ingest_chunk.assert_called_once()
        call_kwargs = mock_ingestion_service.ingest_chunk.call_args[1]
        assert call_kwargs["text_content"] == document_data["text"]

    @pytest.mark.asyncio
    async def test_ingest_document_handles_ingestion_error(self, document_connector, mock_ingestion_service, mock_text_chunker):
        """Test handling of ingestion service errors."""
        # Arrange
        document_data = {
            "text": "This is a test document.",
            "source_type": "document",
            "doc_name": "Test Document.pdf",
        }
        
        # Setup mock to raise an exception
        mock_ingestion_service.ingest_chunk.side_effect = IngestionServiceError("Test error")
        
        # Act & Assert
        with pytest.raises(IngestionServiceError):
            await document_connector.ingest_document(document_data)

    @pytest.mark.asyncio
    async def test_ingest_document_validates_required_fields(self, document_connector):
        """Test that document ingestion validates required fields."""
        # Arrange - Missing required field 'doc_name'
        document_data = {
            "text": "This is a test document.",
            "source_type": "document",
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="doc_name"):
            await document_connector.ingest_document(document_data)
        
        # Arrange - Missing required field 'text'
        document_data = {
            "doc_name": "Test Document.pdf",
            "source_type": "document",
        }
        
        # Act & Assert
        with pytest.raises(ValueError, match="text"):
            await document_connector.ingest_document(document_data)

    @pytest.mark.asyncio
    async def test_document_connector_init_validates_dependencies(self, mock_ingestion_service, mock_text_chunker):
        """Test that DocumentConnector initialization validates dependencies."""
        # Valid initialization
        connector = DocumentConnector(
            ingestion_service=mock_ingestion_service,
            text_chunker=mock_text_chunker
        )
        assert connector is not None
        
        # Missing ingestion_service
        with pytest.raises(ValueError, match="IngestionService must be provided"):
            DocumentConnector(
                ingestion_service=None,
                text_chunker=mock_text_chunker
            )
        
        # Missing text_chunker
        with pytest.raises(ValueError, match="TextChunker must be provided"):
            DocumentConnector(
                ingestion_service=mock_ingestion_service,
                text_chunker=None
            ) 