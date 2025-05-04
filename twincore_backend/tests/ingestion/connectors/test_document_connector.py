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
from dal.interfaces import INeo4jDAL # Import Neo4j interface


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
def mock_neo4j_dal():
    """Mock Neo4jDAL for testing."""
    dal = AsyncMock(spec=INeo4jDAL)
    # Mock methods used by ingest_chunk
    dal.create_node_if_not_exists.return_value = {}
    dal.create_relationship_if_not_exists.return_value = True
    return dal


@pytest.fixture
def document_connector(mock_ingestion_service, mock_text_chunker, mock_neo4j_dal):
    """Create DocumentConnector with mocked dependencies."""
    return DocumentConnector(
        ingestion_service=mock_ingestion_service,
        text_chunker=mock_text_chunker,
        neo4j_dal=mock_neo4j_dal # Inject mock Neo4j DAL
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
    async def test_document_connector_init_validates_dependencies(self, mock_ingestion_service, mock_text_chunker, mock_neo4j_dal):
        """Test that DocumentConnector initialization validates dependencies."""
        # Valid initialization
        connector = DocumentConnector(
            ingestion_service=mock_ingestion_service,
            text_chunker=mock_text_chunker,
            neo4j_dal=mock_neo4j_dal
        )
        assert connector is not None
        
        # Missing ingestion_service
        with pytest.raises(ValueError, match="IngestionService must be provided"):
            DocumentConnector(
                ingestion_service=None,
                text_chunker=mock_text_chunker,
                neo4j_dal=mock_neo4j_dal
            )
        
        # Missing text_chunker
        with pytest.raises(ValueError, match="TextChunker must be provided"):
            DocumentConnector(
                ingestion_service=mock_ingestion_service,
                text_chunker=None,
                neo4j_dal=mock_neo4j_dal
            )
        
        # Missing neo4j_dal
        with pytest.raises(ValueError, match="Neo4jDAL must be provided"):
            DocumentConnector(
                ingestion_service=mock_ingestion_service,
                text_chunker=mock_text_chunker,
                neo4j_dal=None
            )

    # --- Tests for ingest_chunk --- 

    @pytest.mark.asyncio
    async def test_ingest_chunk_success(self, document_connector, mock_ingestion_service, mock_neo4j_dal):
        """Test successful chunk ingestion (e.g., transcript snippet)."""
        # Arrange
        chunk_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "text": "This is a transcript utterance.",
            "timestamp": datetime.now().isoformat(),
            "project_id": str(uuid.uuid4()),
            "chunk_id": str(uuid.uuid4()),
            "metadata": {"speaker_turn": 3}
        }
        mock_ingestion_service.ingest_chunk.return_value = True

        # Act
        result = await document_connector.ingest_chunk(chunk_data)

        # Assert
        assert result is True

        # Verify Neo4j DAL was called to ensure parent document exists
        mock_neo4j_dal.create_node_if_not_exists.assert_called_once_with(
            label="Document",
            properties=pytest.approx({ # Use approx for timestamp comparison if needed
                "document_id": chunk_data["doc_id"],
                "name": f"Transcript Document {chunk_data['doc_id']}",
                "source_type": "transcript",
                "timestamp": chunk_data["timestamp"],
                "uploader_id": chunk_data["user_id"],
            }),
            constraints={"document_id": chunk_data["doc_id"]}
        )
        
        # Verify Neo4j DAL was called to link Document and Session
        mock_neo4j_dal.create_relationship_if_not_exists.assert_called_once_with(
            start_label="Document", start_constraints={"document_id": chunk_data["doc_id"]},
            end_label="Session", end_constraints={"session_id": chunk_data["session_id"]},
            relationship_type="ATTACHED_TO"
        )

        # Verify IngestionService was called with correct parameters
        mock_ingestion_service.ingest_chunk.assert_called_once_with(
            chunk_id=chunk_data["chunk_id"],
            text_content=chunk_data["text"],
            source_type="transcript_snippet",
            user_id=chunk_data["user_id"],
            project_id=chunk_data["project_id"],
            session_id=chunk_data["session_id"],
            doc_id=chunk_data["doc_id"],
            doc_name=f"Transcript Document {chunk_data['doc_id']}",
            timestamp=chunk_data["timestamp"],
            is_twin_interaction=False,
            is_private=False,
            metadata=chunk_data["metadata"]
        )

    @pytest.mark.asyncio
    async def test_ingest_chunk_generates_chunk_id(self, document_connector, mock_ingestion_service, mock_neo4j_dal):
        """Test ingest_chunk generates a chunk_id if not provided."""
        # Arrange
        chunk_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "text": "Another utterance.",
            "timestamp": datetime.now().isoformat(),
            # chunk_id is omitted
        }
        mock_ingestion_service.ingest_chunk.return_value = True

        # Act
        await document_connector.ingest_chunk(chunk_data)

        # Assert
        # Check that ingest_chunk was called with a generated UUID
        call_kwargs = mock_ingestion_service.ingest_chunk.call_args[1]
        assert "chunk_id" in call_kwargs
        assert isinstance(call_kwargs["chunk_id"], str)
        try:
            uuid.UUID(call_kwargs["chunk_id"])
        except ValueError:
            pytest.fail(f"Generated chunk_id is not a valid UUID: {call_kwargs['chunk_id']}")

    @pytest.mark.asyncio
    async def test_ingest_chunk_validates_required_fields(self, document_connector):
        """Test that ingest_chunk validates required fields."""
        required_fields = ["user_id", "session_id", "doc_id", "text", "timestamp"]
        base_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "text": "Some text.",
            "timestamp": datetime.now().isoformat(),
        }

        for field_to_remove in required_fields:
            chunk_data = base_data.copy()
            del chunk_data[field_to_remove]
            with pytest.raises(ValueError, match=f"Missing required field.*{field_to_remove}"):
                await document_connector.ingest_chunk(chunk_data)

    @pytest.mark.asyncio
    async def test_ingest_chunk_handles_ingestion_error(self, document_connector, mock_ingestion_service, mock_neo4j_dal):
        """Test ingest_chunk propagates errors from ingestion service."""
        # Arrange
        chunk_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "text": "Error prone text.",
            "timestamp": datetime.now().isoformat(),
        }
        # Setup mock to raise an exception
        mock_ingestion_service.ingest_chunk.side_effect = IngestionServiceError("Ingest failed")

        # Act & Assert
        with pytest.raises(IngestionServiceError, match="Ingest failed"):
            await document_connector.ingest_chunk(chunk_data)

    @pytest.mark.asyncio
    async def test_ingest_chunk_handles_neo4j_error(self, document_connector, mock_ingestion_service, mock_neo4j_dal):
        """Test ingest_chunk propagates errors from neo4j dal."""
        # Arrange
        chunk_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "text": "More text.",
            "timestamp": datetime.now().isoformat(),
        }
        # Setup mock to raise an exception
        mock_neo4j_dal.create_node_if_not_exists.side_effect = Exception("Neo4j error")

        # Act & Assert
        with pytest.raises(Exception, match="Neo4j error"):
            await document_connector.ingest_chunk(chunk_data) 