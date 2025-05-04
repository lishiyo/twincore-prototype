"""Tests for the PreferenceService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from services.preference_service import PreferenceService


@pytest.fixture
def mock_qdrant_dal():
    """Mock QdrantDAL for testing."""
    mock = AsyncMock()
    mock.search_user_preferences.return_value = [
        {
            "chunk_id": "test_chunk_1",
            "score": 0.95,
            "text_content": "I prefer dark mode for all my apps.",
            "source_type": "message",
            "user_id": "test_user_123",
            "project_id": "test_project_456",
            "timestamp": 1620000000.0,
            "is_twin_interaction": False
        }
    ]
    return mock


@pytest.fixture
def mock_neo4j_dal():
    """Mock Neo4jDAL for testing."""
    mock = AsyncMock()
    mock.get_user_preference_statements.return_value = [
        {
            "chunk_id": "test_chunk_2",
            "text_content": "Dark mode is easier on my eyes at night.",
            "source_type": "message",
            "user_id": "test_user_123",
            "project_id": "test_project_456",
            "is_twin_interaction": False
        }
    ]
    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for testing."""
    mock = AsyncMock()
    mock.get_embedding.return_value = np.random.rand(1536).astype(np.float32)
    return mock


@pytest.fixture
def preference_service(mock_qdrant_dal, mock_neo4j_dal, mock_embedding_service):
    """Create a PreferenceService with mock dependencies."""
    return PreferenceService(
        qdrant_dal=mock_qdrant_dal,
        neo4j_dal=mock_neo4j_dal,
        embedding_service=mock_embedding_service
    )


@pytest.mark.asyncio
async def test_query_user_preference_success(preference_service, mock_qdrant_dal, mock_neo4j_dal, mock_embedding_service):
    """Test successful preference querying."""
    # Setup
    user_id = "test_user_123"
    decision_topic = "dark mode"
    project_id = "test_project_456"
    
    # Execute
    result = await preference_service.query_user_preference(
        user_id=user_id,
        decision_topic=decision_topic,
        project_id=project_id,
        limit=5
    )
    
    # Verify
    assert mock_embedding_service.get_embedding.called
    assert mock_embedding_service.get_embedding.call_args[0][0] == decision_topic
    
    assert mock_neo4j_dal.get_user_preference_statements.called
    assert mock_neo4j_dal.get_user_preference_statements.call_args[1]["user_id"] == user_id
    assert mock_neo4j_dal.get_user_preference_statements.call_args[1]["topic"] == decision_topic
    
    assert mock_qdrant_dal.search_user_preferences.called
    assert mock_qdrant_dal.search_user_preferences.call_args[1]["user_id"] == user_id
    assert mock_qdrant_dal.search_user_preferences.call_args[1]["decision_topic"] == decision_topic
    
    assert result["user_id"] == user_id
    assert result["decision_topic"] == decision_topic
    assert result["has_preferences"]
    assert len(result["preference_statements"]) == 2  # Combined from both sources
    assert result["graph_results_count"] == 1
    assert result["vector_results_count"] == 1
    
    # Verify sources are marked correctly
    sources = [item["source"] for item in result["preference_statements"]]
    assert "graph" in sources
    assert "vector" in sources


@pytest.mark.asyncio
async def test_query_user_preference_no_results(preference_service, mock_qdrant_dal, mock_neo4j_dal):
    """Test preference querying with no results."""
    # Setup
    mock_qdrant_dal.search_user_preferences.return_value = []
    mock_neo4j_dal.get_user_preference_statements.return_value = []
    
    # Execute
    result = await preference_service.query_user_preference(
        user_id="test_user_empty",
        decision_topic="nonexistent topic",
        limit=5
    )
    
    # Verify
    assert result["has_preferences"] is False
    assert len(result["preference_statements"]) == 0
    assert result["graph_results_count"] == 0
    assert result["vector_results_count"] == 0


@pytest.mark.asyncio
async def test_query_user_preference_graph_error(preference_service, mock_qdrant_dal, mock_neo4j_dal):
    """Test handling graph errors gracefully."""
    # Setup
    mock_neo4j_dal.get_user_preference_statements.side_effect = Exception("Graph error")
    
    # Execute - should not raise the graph error
    result = await preference_service.query_user_preference(
        user_id="test_user_123",
        decision_topic="dark mode",
        limit=5
    )
    
    # Verify - still has results from vector search
    assert result["has_preferences"]  # We still get results from Qdrant
    assert len(result["preference_statements"]) == 1
    assert result["graph_results_count"] == 0
    assert result["vector_results_count"] == 1


@pytest.mark.asyncio
async def test_query_user_preference_vector_error(preference_service, mock_qdrant_dal, mock_neo4j_dal):
    """Test handling vector errors gracefully."""
    # Setup
    mock_qdrant_dal.search_user_preferences.side_effect = Exception("Vector error")
    
    # Execute - should not raise the vector error
    result = await preference_service.query_user_preference(
        user_id="test_user_123",
        decision_topic="dark mode",
        limit=5
    )
    
    # Verify - still has results from graph
    assert result["has_preferences"]  # We still get results from Neo4j
    assert len(result["preference_statements"]) == 1
    assert result["graph_results_count"] == 1
    assert result["vector_results_count"] == 0 