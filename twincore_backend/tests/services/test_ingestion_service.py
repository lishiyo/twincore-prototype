"""Tests for Ingestion Service implementation.

This module contains tests for the IngestionService class, with mocked dependencies
to verify that the service correctly coordinates the embedding and storage process.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

import numpy as np

from services.ingestion_service import IngestionService, IngestionServiceError
from services.embedding_service import EmbeddingService


@pytest.fixture
def mock_embedding_service():
    """Create a mock EmbeddingService."""
    service = MagicMock(spec=EmbeddingService)
    # Convert get_embedding to AsyncMock to make it awaitable
    service.get_embedding = AsyncMock()
    service.get_embedding.return_value = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    return service


@pytest.fixture
def mock_qdrant_dal():
    """Create a mock QdrantDAL."""
    dal = MagicMock()
    dal.upsert_vector = AsyncMock()
    dal.upsert_vector.return_value = True
    dal.search_vectors = AsyncMock()
    dal.search_vectors.return_value = []
    dal.delete_vectors = AsyncMock()
    dal.delete_vectors.return_value = 0
    return dal


@pytest.fixture
def mock_neo4j_dal():
    """Create a mock Neo4jDAL."""
    dal = MagicMock()
    dal.create_node_if_not_exists = AsyncMock()
    dal.create_node_if_not_exists.return_value = {"id": "test-id"}
    dal.create_relationship_if_not_exists = AsyncMock()
    dal.create_relationship_if_not_exists.return_value = True
    dal.get_session_participants = AsyncMock()
    dal.get_session_participants.return_value = []
    dal.get_project_context = AsyncMock()
    dal.get_project_context.return_value = {"sessions": [], "documents": [], "users": []}
    return dal


@pytest.fixture
def ingestion_service(mock_embedding_service, mock_qdrant_dal, mock_neo4j_dal):
    """Create an IngestionService with mocked dependencies."""
    return IngestionService(
        embedding_service=mock_embedding_service,
        qdrant_dal=mock_qdrant_dal,
        neo4j_dal=mock_neo4j_dal
    )


class TestIngestionService:
    """Tests for the IngestionService class."""

    def test_init_missing_dependencies(self, mock_embedding_service, mock_qdrant_dal, mock_neo4j_dal):
        """Test initialization with missing dependencies raises errors."""
        
        with pytest.raises(ValueError, match="EmbeddingService must be provided"):
            IngestionService(None, mock_qdrant_dal, mock_neo4j_dal)
        
        with pytest.raises(ValueError, match="QdrantDAL must be provided"):
            IngestionService(mock_embedding_service, None, mock_neo4j_dal)
        
        with pytest.raises(ValueError, match="Neo4jDAL must be provided"):
            IngestionService(mock_embedding_service, mock_qdrant_dal, None)

    @pytest.mark.asyncio
    async def test_prepare_qdrant_point(self, ingestion_service, mock_embedding_service):
        """Test preparation of Qdrant point with embedding generation."""
        
        # Arrange
        chunk_id = str(uuid.uuid4())
        text_content = "Test text content"
        source_type = "message"
        user_id = str(uuid.uuid4())
        
        # Act
        result = await ingestion_service._prepare_qdrant_point(
            chunk_id=chunk_id,
            text_content=text_content,
            source_type=source_type,
            user_id=user_id
        )
        
        # Assert
        assert mock_embedding_service.get_embedding.called
        assert mock_embedding_service.get_embedding.call_args[0][0] == text_content
        assert result["chunk_id"] == chunk_id
        assert "vector" in result
        assert result["metadata"]["chunk_id"] == chunk_id
        assert result["metadata"]["text_content"] == text_content
        assert result["metadata"]["source_type"] == source_type
        assert result["metadata"]["user_id"] == user_id
        assert "timestamp" in result["metadata"]
        assert result["metadata"]["is_twin_interaction"] is False
        assert result["metadata"]["is_private"] is False

    @pytest.mark.asyncio
    async def test_update_neo4j_graph_message(self, ingestion_service, mock_neo4j_dal):
        """Test updating Neo4j graph for a message."""
        
        # Arrange
        chunk_id = str(uuid.uuid4())
        source_type = "message"
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Act
        result = await ingestion_service._update_neo4j_graph(
            source_type=source_type,
            chunk_id=chunk_id,
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            message_id=message_id,
            timestamp=timestamp
        )
        
        # Assert
        assert result is True
        
        # Check Chunk node creation
        chunk_call = [call for call in mock_neo4j_dal.create_node_if_not_exists.call_args_list 
                     if call[0][0] == "Chunk"][0]
        assert chunk_call[0][1]["chunk_id"] == chunk_id
        assert chunk_call[0][1]["timestamp"] == timestamp
        
        # Check User node creation
        user_call = [call for call in mock_neo4j_dal.create_node_if_not_exists.call_args_list 
                    if call[0][0] == "User"][0]
        assert user_call[0][1]["user_id"] == user_id
        
        # Check Message node creation
        message_call = [call for call in mock_neo4j_dal.create_node_if_not_exists.call_args_list 
                       if call[0][0] == "Message"][0]
        assert message_call[0][1]["message_id"] == message_id
        
        # Check relationships
        relationship_calls = mock_neo4j_dal.create_relationship_if_not_exists.call_args_list
        
        # User-Message AUTHORED relationship
        user_message_rel = [call for call in relationship_calls 
                           if call[0][0] == "User" and call[0][2] == "Message" and call[0][4] == "AUTHORED"]
        assert len(user_message_rel) == 1
        
        # Message-Session POSTED_IN relationship
        message_session_rel = [call for call in relationship_calls 
                              if call[0][0] == "Message" and call[0][2] == "Session" and call[0][4] == "POSTED_IN"]
        assert len(message_session_rel) == 1

    @pytest.mark.asyncio
    async def test_update_neo4j_graph_document(self, ingestion_service, mock_neo4j_dal):
        """Test updating Neo4j graph for a document."""
        
        # Arrange
        chunk_id = str(uuid.uuid4())
        source_type = "document"
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        doc_name = "Test Document.pdf"
        timestamp = datetime.utcnow().isoformat()
        is_private = True
        
        # Act
        result = await ingestion_service._update_neo4j_graph(
            source_type=source_type,
            chunk_id=chunk_id,
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            doc_id=doc_id,
            doc_name=doc_name,
            timestamp=timestamp,
            is_private=is_private
        )
        
        # Assert
        assert result is True
        
        # Check Document node creation
        doc_call = [call for call in mock_neo4j_dal.create_node_if_not_exists.call_args_list 
                   if call[0][0] == "Document"][0]
        assert doc_call[0][1]["document_id"] == doc_id
        assert doc_call[0][1]["name"] == doc_name
        assert doc_call[0][1]["is_private"] is True
        
        # Check relationships
        relationship_calls = mock_neo4j_dal.create_relationship_if_not_exists.call_args_list
        
        # User-Document UPLOADED relationship
        user_doc_rel = [call for call in relationship_calls 
                       if call[0][0] == "User" and call[0][2] == "Document" and call[0][4] == "UPLOADED"]
        assert len(user_doc_rel) == 1
        
        # Document-Session UPLOADED_IN relationship
        doc_session_rel = [call for call in relationship_calls 
                          if call[0][0] == "Document" and call[0][2] == "Session" and call[0][4] == "UPLOADED_IN"]
        assert len(doc_session_rel) == 1
        
        # User-Chunk OWNS relationship (since is_private=True)
        user_chunk_rel = [call for call in relationship_calls 
                         if call[0][0] == "User" and call[0][2] == "Chunk" and call[0][4] == "OWNS"]
        assert len(user_chunk_rel) == 1

    @pytest.mark.asyncio
    async def test_ingest_chunk(self, ingestion_service, mock_embedding_service, mock_qdrant_dal, mock_neo4j_dal):
        """Test the main ingest_chunk method."""
        
        # Arrange
        chunk_id = str(uuid.uuid4())
        text_content = "Test chunk content"
        source_type = "message"
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        
        # Act
        result = await ingestion_service.ingest_chunk(
            chunk_id=chunk_id,
            text_content=text_content,
            source_type=source_type,
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            message_id=message_id
        )
        
        # Assert
        assert result is True
        
        # Check embedding service call
        assert mock_embedding_service.get_embedding.called
        assert mock_embedding_service.get_embedding.call_args[0][0] == text_content
        
        # Check Qdrant DAL call
        assert mock_qdrant_dal.upsert_vector.called
        qdrant_call = mock_qdrant_dal.upsert_vector.call_args[1]
        assert qdrant_call["chunk_id"] == chunk_id
        assert qdrant_call["text_content"] == text_content
        assert qdrant_call["source_type"] == source_type
        assert qdrant_call["user_id"] == user_id
        assert qdrant_call["session_id"] == session_id
        assert qdrant_call["project_id"] == project_id
        assert qdrant_call["message_id"] == message_id
        
        # Check Neo4j DAL calls
        assert mock_neo4j_dal.create_node_if_not_exists.called
        assert mock_neo4j_dal.create_relationship_if_not_exists.called
        
        # Check that Chunk node was created
        chunk_call = [call for call in mock_neo4j_dal.create_node_if_not_exists.call_args_list 
                     if call[0][0] == "Chunk"][0]
        assert chunk_call[0][1]["chunk_id"] == chunk_id

    @pytest.mark.asyncio
    async def test_ingestion_error_handling(self, ingestion_service, mock_embedding_service):
        """Test error handling in ingest_chunk method."""
        
        # Arrange
        chunk_id = str(uuid.uuid4())
        text_content = "Test chunk content"
        source_type = "message"
        
        # Make embedding service raise an exception
        mock_embedding_service.get_embedding.side_effect = Exception("Test error")
        
        # Act & Assert
        with pytest.raises(IngestionServiceError, match="Failed to ingest chunk"):
            await ingestion_service.ingest_chunk(
                chunk_id=chunk_id,
                text_content=text_content,
                source_type=source_type
            ) 