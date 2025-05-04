"""Unit tests for RetrievalService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from services.retrieval_service import RetrievalService


@pytest.fixture
def mock_qdrant_dal():
    """Create a mock QdrantDAL with async methods."""
    mock = AsyncMock()
    mock.search_vectors = AsyncMock()
    return mock


@pytest.fixture
def mock_neo4j_dal():
    """Create a mock Neo4jDAL with async methods."""
    mock = AsyncMock()
    mock.get_session_participants = AsyncMock()
    return mock


@pytest.fixture
def mock_embedding_service():
    """Create a mock EmbeddingService."""
    mock = AsyncMock()
    mock.get_embedding = AsyncMock(return_value=np.zeros(1536))  # Mock embedding vector
    return mock


@pytest.fixture
def mock_message_connector():
    """Create a mock MessageConnector."""
    mock = AsyncMock()
    mock.ingest_message = AsyncMock()
    return mock


@pytest.fixture
def retrieval_service(mock_qdrant_dal, mock_neo4j_dal, mock_embedding_service):
    """Create a RetrievalService with mock dependencies."""
    return RetrievalService(
        qdrant_dal=mock_qdrant_dal,
        neo4j_dal=mock_neo4j_dal,
        embedding_service=mock_embedding_service,
    )


@pytest.fixture
def retrieval_service_with_message_connector(
    mock_qdrant_dal, mock_neo4j_dal, mock_embedding_service, mock_message_connector
):
    """Create a RetrievalService with mock dependencies including MessageConnector."""
    return RetrievalService(
        qdrant_dal=mock_qdrant_dal,
        neo4j_dal=mock_neo4j_dal,
        embedding_service=mock_embedding_service,
        message_connector=mock_message_connector,
    )


@pytest.mark.asyncio
async def test_retrieve_context(retrieval_service, mock_qdrant_dal, mock_embedding_service):
    """Test retrieve_context method."""
    # Arrange
    query_text = "test query"
    test_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "test content 1",
            "source_type": "message",
            "user_id": "user-1",
            "score": 0.95,
        }
    ]
    mock_qdrant_dal.search_vectors.return_value = test_results
    
    # Act
    results = await retrieval_service.retrieve_context(
        query_text=query_text,
        limit=10,
        project_id="project-1",
        session_id="session-1",
    )
    
    # Assert
    mock_embedding_service.get_embedding.assert_called_once_with(query_text)
    mock_qdrant_dal.search_vectors.assert_called_once()
    
    # Verify the search_vectors call included the right parameters
    call_args = mock_qdrant_dal.search_vectors.call_args[1]
    assert call_args["query_vector"] is not None
    assert call_args["limit"] == 10
    assert call_args["project_id"] == "project-1"
    assert call_args["session_id"] == "session-1"
    assert call_args["exclude_twin_interactions"] is True
    
    # Verify results are returned correctly
    assert results == test_results


@pytest.mark.asyncio
async def test_retrieve_private_memory(
    retrieval_service_with_message_connector, 
    mock_qdrant_dal, 
    mock_embedding_service,
    mock_message_connector
):
    """Test retrieve_private_memory method."""
    # Arrange
    query_text = "test private query"
    user_id = "user-1"
    test_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "private content 1",
            "source_type": "document",
            "user_id": user_id,
            "is_private": True,
            "score": 0.92,
        }
    ]
    mock_qdrant_dal.search_vectors.return_value = test_results
    
    # Act
    results = await retrieval_service_with_message_connector.retrieve_private_memory(
        query_text=query_text,
        user_id=user_id,
        limit=5,
        project_id="project-1",
    )
    
    # Assert
    # Verify the query was ingested as a twin interaction
    mock_message_connector.ingest_message.assert_called_once()
    # Verify it was called with a dict containing the expected fields
    call_args = mock_message_connector.ingest_message.call_args[0][0]
    assert call_args["text"] == query_text
    assert call_args["user_id"] == user_id
    assert call_args["is_twin_chat"] is True
    assert call_args["source_type"] == "query"
    
    # Verify embedding was generated
    mock_embedding_service.get_embedding.assert_called_once_with(query_text)
    
    # Verify search was performed with correct params
    mock_qdrant_dal.search_vectors.assert_called_once()
    search_args = mock_qdrant_dal.search_vectors.call_args[1]
    assert search_args["user_id"] == user_id
    assert search_args["limit"] == 5
    assert search_args["include_private"] is True
    assert search_args["exclude_twin_interactions"] is True
    
    # Verify results are returned correctly
    assert results == test_results


@pytest.mark.asyncio
async def test_retrieve_context_with_session_participants(
    retrieval_service,
    mock_qdrant_dal,
    mock_neo4j_dal,
    mock_embedding_service
):
    """Test retrieve_context method with session participants retrieval."""
    # Arrange
    query_text = "test query with participants"
    session_id = "session-with-participants"
    mock_participants = [
        {"user_id": "user-1", "name": "Test User 1"},
        {"user_id": "user-2", "name": "Test User 2"},
    ]
    mock_neo4j_dal.get_session_participants.return_value = mock_participants
    mock_qdrant_dal.search_vectors.return_value = []
    
    # Act
    results = await retrieval_service.retrieve_context(
        query_text=query_text,
        session_id=session_id,
    )
    
    # Assert
    mock_neo4j_dal.get_session_participants.assert_called_once_with(session_id)
    mock_embedding_service.get_embedding.assert_called_once_with(query_text)
    mock_qdrant_dal.search_vectors.assert_called_once()
    assert results == []


@pytest.mark.asyncio
async def test_retrieve_private_memory_without_message_connector(
    retrieval_service,  # Without message connector
    mock_qdrant_dal,
    mock_embedding_service
):
    """Test retrieve_private_memory when MessageConnector is not provided."""
    # Arrange
    query_text = "test private query"
    user_id = "user-1"
    mock_qdrant_dal.search_vectors.return_value = []
    
    # Act
    results = await retrieval_service.retrieve_private_memory(
        query_text=query_text,
        user_id=user_id,
    )
    
    # Assert - search should still work but no ingestion should happen
    mock_embedding_service.get_embedding.assert_called_once_with(query_text)
    mock_qdrant_dal.search_vectors.assert_called_once()
    assert results == [] 