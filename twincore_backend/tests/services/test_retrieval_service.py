"""Unit tests for RetrievalService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
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
    mock.get_project_context = AsyncMock()
    mock.get_related_content = AsyncMock()
    mock.get_content_by_topic = AsyncMock()
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
    assert call_args["include_twin_interactions"] is False
    
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
    assert search_args["include_twin_interactions"] is True
    
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


@pytest.mark.asyncio
async def test_retrieve_enriched_context(
    retrieval_service, mock_qdrant_dal, mock_neo4j_dal, mock_embedding_service
):
    """Test retrieve_enriched_context method that combines vector search with graph data."""
    # Arrange
    query_text = "test query"
    project_id = "project-1"
    session_id = "session-1"
    
    # Mock Qdrant search results
    search_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "test content 1",
            "source_type": "message",
            "user_id": "user-1",
            "project_id": project_id,
            "session_id": session_id,
            "score": 0.95,
        }
    ]
    mock_qdrant_dal.search_vectors.return_value = search_results
    
    # Mock Neo4j project context results
    project_context = {
        "sessions": [{"session_id": "session-1", "name": "Test Session"}],
        "documents": [{"doc_id": "doc-1", "name": "Test Document"}],
        "users": [{"user_id": "user-1", "name": "Test User"}]
    }
    mock_neo4j_dal.get_project_context.return_value = project_context
    
    # Mock Neo4j session participants results
    participants = [
        {"user_id": "user-1", "name": "Test User"},
        {"user_id": "user-2", "name": "Another User"}
    ]
    mock_neo4j_dal.get_session_participants.return_value = participants
    
    # Act
    results = await retrieval_service.retrieve_enriched_context(
        query_text=query_text,
        limit=10,
        project_id=project_id,
        session_id=session_id
    )
    
    # Assert
    # Verify standard context retrieval was called
    mock_embedding_service.get_embedding.assert_called_once_with(query_text)
    mock_qdrant_dal.search_vectors.assert_called_once()
    
    # Verify graph enrichment was called
    mock_neo4j_dal.get_project_context.assert_called_once_with(project_id)
    # get_session_participants is called twice - once in retrieve_context and once in retrieve_enriched_context
    assert mock_neo4j_dal.get_session_participants.call_count == 2
    assert mock_neo4j_dal.get_session_participants.call_args_list == [call(session_id), call(session_id)]
    
    # Verify results are enriched with graph data
    assert len(results) == 1
    assert "project_context" in results[0]
    assert results[0]["project_context"]["session_count"] == 1
    assert results[0]["project_context"]["document_count"] == 1
    assert results[0]["project_context"]["user_count"] == 1
    
    assert "session_participants" in results[0]
    assert len(results[0]["session_participants"]) == 2


@pytest.mark.asyncio
async def test_retrieve_enriched_context_with_error_handling(
    retrieval_service, mock_qdrant_dal, mock_neo4j_dal, mock_embedding_service
):
    """Test retrieve_enriched_context handles Neo4j errors gracefully."""
    # Arrange
    query_text = "test query"
    project_id = "project-1"
    session_id = "session-1"
    
    # Mock Qdrant search results
    search_results = [
        {
            "chunk_id": "test-id-1",
            "text_content": "test content 1",
            "source_type": "message",
            "user_id": "user-1",
            "project_id": project_id,
            "session_id": session_id,
            "score": 0.95,
        }
    ]
    mock_qdrant_dal.search_vectors.return_value = search_results
    
    # Make Neo4j methods raise exceptions to test error handling
    mock_neo4j_dal.get_project_context.side_effect = Exception("Neo4j get_project_context error")
    mock_neo4j_dal.get_session_participants.side_effect = Exception("Neo4j get_session_participants error")
    
    # Act
    results = await retrieval_service.retrieve_enriched_context(
        query_text=query_text,
        limit=10,
        project_id=project_id,
        session_id=session_id
    )
    
    # Assert
    # Should still have results from vector search even if graph enrichment fails
    assert len(results) == 1
    assert results[0]["chunk_id"] == "test-id-1"
    
    # But graph enrichments should not be present due to errors
    assert "project_context" not in results[0]
    assert "session_participants" not in results[0]


@pytest.mark.asyncio
async def test_retrieve_related_content(
    retrieval_service, mock_neo4j_dal
):
    """Test retrieve_related_content method."""
    # Arrange
    chunk_id = "test-chunk-id"
    relationship_types = ["MENTIONS", "SIMILAR_TO"]
    
    # Mock Neo4j related content results
    related_content = [
        {
            "chunk_id": "related-id-1",
            "text_content": "related content 1",
            "source_type": "message",
            "user_id": "user-1",
            "outgoing_relationships": [
                {"type": "MENTIONS", "target_id": "topic-1", "target_type": "Topic"}
            ],
            "incoming_relationships": []
        }
    ]
    mock_neo4j_dal.get_related_content.return_value = related_content
    
    # Act
    results = await retrieval_service.retrieve_related_content(
        chunk_id=chunk_id,
        relationship_types=relationship_types,
        limit=10,
        include_private=True,
        max_depth=2
    )
    
    # Assert
    mock_neo4j_dal.get_related_content.assert_called_once_with(
        chunk_id=chunk_id,
        relationship_types=relationship_types,
        limit=10,
        include_private=True,
        max_depth=2
    )
    
    assert results == related_content


@pytest.mark.asyncio
async def test_retrieve_related_content_error_handling(
    retrieval_service, mock_neo4j_dal
):
    """Test retrieve_related_content handles errors gracefully."""
    # Arrange
    chunk_id = "test-chunk-id"
    
    # Make Neo4j method raise an exception
    mock_neo4j_dal.get_related_content.side_effect = Exception("Neo4j error")
    
    # Act
    results = await retrieval_service.retrieve_related_content(
        chunk_id=chunk_id
    )
    
    # Assert - should return empty list on error
    assert isinstance(results, list)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_retrieve_by_topic_with_graph_results(
    retrieval_service, mock_neo4j_dal, mock_embedding_service, mock_qdrant_dal
):
    """Test retrieve_by_topic method when graph results are found."""
    # Arrange
    topic_name = "test topic"
    user_id = "user-1"
    
    # Mock Neo4j topic content results
    topic_content = [
        {
            "chunk_id": "topic-id-1",
            "text_content": "content about test topic",
            "source_type": "message",
            "user_id": user_id,
            "topic": {"name": topic_name, "description": "A test topic"}
        }
    ]
    mock_neo4j_dal.get_content_by_topic.return_value = topic_content
    
    # Act
    results = await retrieval_service.retrieve_by_topic(
        topic_name=topic_name,
        user_id=user_id
    )
    
    # Assert
    mock_neo4j_dal.get_content_by_topic.assert_called_once()
    # Embedding service and Qdrant should not be called since graph results were found
    mock_embedding_service.get_embedding.assert_not_called()
    mock_qdrant_dal.search_vectors.assert_not_called()
    
    assert results == topic_content


@pytest.mark.asyncio
async def test_retrieve_by_topic_falling_back_to_vector_search(
    retrieval_service, mock_neo4j_dal, mock_embedding_service, mock_qdrant_dal
):
    """Test retrieve_by_topic falls back to vector search when no graph results are found."""
    # Arrange
    topic_name = "test topic"
    user_id = "user-1"
    
    # Mock Neo4j to return empty results
    mock_neo4j_dal.get_content_by_topic.return_value = []
    
    # Mock vector search results
    vector_results = [
        {
            "chunk_id": "vector-id-1",
            "text_content": "content about test topic via vector search",
            "source_type": "message",
            "user_id": user_id,
            "score": 0.88
        }
    ]
    mock_qdrant_dal.search_vectors.return_value = vector_results
    
    # Act
    results = await retrieval_service.retrieve_by_topic(
        topic_name=topic_name,
        user_id=user_id
    )
    
    # Assert
    mock_neo4j_dal.get_content_by_topic.assert_called_once()
    # Since graph returned no results, embedding and vector search should be called
    mock_embedding_service.get_embedding.assert_called_once_with(topic_name)
    mock_qdrant_dal.search_vectors.assert_called_once()
    # Verify the flag is passed (False by default for topic search)
    assert mock_qdrant_dal.search_vectors.call_args[1]["include_twin_interactions"] is False
    
    assert results == vector_results


@pytest.mark.asyncio
async def test_retrieve_by_topic_falling_back_to_vector_search_on_error(
    retrieval_service, mock_neo4j_dal, mock_embedding_service, mock_qdrant_dal
):
    """Test retrieve_by_topic falls back to vector search when graph search fails."""
    # Arrange
    topic_name = "test topic"
    user_id = "user-1"
    
    # Mock Neo4j to raise an exception
    mock_neo4j_dal.get_content_by_topic.side_effect = Exception("Neo4j error")
    
    # Mock vector search results
    vector_results = [
        {
            "chunk_id": "vector-id-1",
            "text_content": "content about test topic via vector search",
            "source_type": "message",
            "user_id": user_id,
            "score": 0.88
        }
    ]
    mock_qdrant_dal.search_vectors.return_value = vector_results
    
    # Act
    results = await retrieval_service.retrieve_by_topic(
        topic_name=topic_name,
        user_id=user_id
    )
    
    # Assert
    mock_neo4j_dal.get_content_by_topic.assert_called_once()
    # Since graph search failed, embedding and vector search should be called
    mock_embedding_service.get_embedding.assert_called_once_with(topic_name)
    mock_qdrant_dal.search_vectors.assert_called_once()
    # Verify the flag is passed (False by default for topic search)
    assert mock_qdrant_dal.search_vectors.call_args[1]["include_twin_interactions"] is False
    
    assert results == vector_results


@pytest.mark.asyncio
async def test_retrieve_by_topic_handles_all_errors(
    retrieval_service, mock_neo4j_dal, mock_embedding_service, mock_qdrant_dal
):
    """Test retrieve_by_topic handles both graph and vector search errors."""
    # Arrange
    topic_name = "test topic"
    
    # Mock Neo4j to raise an exception
    mock_neo4j_dal.get_content_by_topic.side_effect = Exception("Neo4j error")
    
    # Mock embedding service to also raise an exception
    mock_embedding_service.get_embedding.side_effect = Exception("Embedding error")
    
    # Act
    results = await retrieval_service.retrieve_by_topic(
        topic_name=topic_name
    )
    
    # Assert
    # Both methods should be called
    mock_neo4j_dal.get_content_by_topic.assert_called_once()
    mock_embedding_service.get_embedding.assert_called_once_with(topic_name)
    
    # Vector search should not be called due to embedding error
    mock_qdrant_dal.search_vectors.assert_not_called()
    
    # Should return empty list when all attempts fail
    assert isinstance(results, list)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_retrieve_user_context(
    retrieval_service: RetrievalService, 
    mock_qdrant_dal: MagicMock, 
    mock_neo4j_dal: MagicMock,
    mock_embedding_service: MagicMock,
):
    """Test retrieving context specific to a user."""
    # Use hardcoded test values instead of fixtures
    test_user_id = "user-test-123"
    test_project_id = "project-test-123"
    test_session_id = "session-test-123"
    
    mock_qdrant_dal.search_vectors.return_value = [{"chunk_id": "chunk1", "text": "user stuff"}]
    mock_embedding_service.get_embedding.return_value = [0.1, 0.2, 0.3]
    query = "find my things"
    limit = 5
    
    # Test default flags (include_private=True, include_messages_to_twin=True)
    await retrieval_service.retrieve_user_context(
        user_id=test_user_id,
        query_text=query,
        project_id=test_project_id,
        session_id=test_session_id,
        limit=limit
    )
    
    mock_embedding_service.get_embedding.assert_called_once_with(query)
    mock_qdrant_dal.search_vectors.assert_called_once_with(
        query_vector=[0.1, 0.2, 0.3],
        limit=limit,
        user_id=test_user_id, # Crucially, user_id is passed
        project_id=test_project_id,
        session_id=test_session_id,
        include_private=True, # Default for this method
        include_twin_interactions=True # Default for this method
    )
    mock_qdrant_dal.reset_mock()
    mock_embedding_service.reset_mock()
    
    # Test with explicit flags set to False
    await retrieval_service.retrieve_user_context(
        user_id=test_user_id,
        query_text=query,
        project_id=test_project_id,
        session_id=test_session_id,
        limit=limit,
        include_private=False,
        include_messages_to_twin=False
    )
    
    mock_embedding_service.get_embedding.assert_called_once_with(query)
    mock_qdrant_dal.search_vectors.assert_called_once_with(
        query_vector=[0.1, 0.2, 0.3],
        limit=limit,
        user_id=test_user_id,
        project_id=test_project_id,
        session_id=test_session_id,
        include_private=False, # Explicitly False
        include_twin_interactions=False # Explicitly False
    ) 