"""Tests for Qdrant Data Access Layer implementation.

This module contains integration tests for the QdrantDAL class, which requires
a running Qdrant database instance (test instance via Docker).
"""

import asyncio
import pytest
import uuid
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import logging

import pytest_asyncio
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from core.config import settings
from core.db_clients import clear_all_client_caches
from dal.qdrant_dal import QdrantDAL

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def test_qdrant_client():
    """Get a test Qdrant async client connected to the test instance."""
    client: Optional[AsyncQdrantClient] = None
    
    try:
        # Override settings to use test instance
        settings.qdrant_host = settings.qdrant_test_host
        settings.qdrant_port = settings.qdrant_test_port
        settings.qdrant_grpc_port = settings.qdrant_test_grpc_port
        settings.qdrant_api_key = settings.qdrant_test_api_key
        
        clear_all_client_caches()
        
        logger.info(f"Connecting to Qdrant test instance at {settings.qdrant_host}:{settings.qdrant_port} (GRPC: {settings.qdrant_grpc_port})")
        client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port, # REST port
            api_key=settings.qdrant_api_key,
            # Revert to default/True to try GRPC
            prefer_grpc=True, 
            grpc_port=settings.qdrant_grpc_port, # GRPC port
            https=False,
        )
        
        # Test connection
        logger.info("Testing connection to Qdrant test instance...")
        await client.get_collections()
        logger.info("Successfully connected to Qdrant test instance")
        
        yield client
        
    except Exception as e:
        logger.error(f"Error setting up Qdrant test client: {e}")
        pytest.fail(f"Qdrant connection failed: {e}")
        
    finally:
        # Reset settings
        settings.qdrant_host = "localhost"
        settings.qdrant_port = 6333
        settings.qdrant_grpc_port = 6334
        settings.qdrant_api_key = None
        
        clear_all_client_caches()


@pytest_asyncio.fixture
async def test_qdrant_dal(test_qdrant_client: AsyncQdrantClient):
    """Create a QdrantDAL instance for testing using the test client."""
    dal = QdrantDAL(client=test_qdrant_client)
    yield dal


@pytest_asyncio.fixture
async def clean_test_collection(test_qdrant_client: AsyncQdrantClient):
    """Ensure the test collection is clean before and after tests."""
    collection_name = settings.qdrant_collection_name
    
    # Clean up before test
    try:
        await test_qdrant_client.delete_collection(collection_name=collection_name)
        logger.info(f"Pre-test cleanup: Deleted collection '{collection_name}'")
    except (UnexpectedResponse, ValueError) as e:
        # Ignore if collection doesn't exist
        pass
    
    # Create collection for testing
    await test_qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=settings.embedding_dimension,
            distance=models.Distance.COSINE
        )
    )
    logger.info(f"Created test collection '{collection_name}'")
    
    yield
    
    # Clean up after test
    try:
        await test_qdrant_client.delete_collection(collection_name=collection_name)
        logger.info(f"Post-test cleanup: Deleted collection '{collection_name}'")
    except Exception as e:
        logger.error(f"Error during post-test cleanup: {e}")


def create_test_vector(dim: int = None) -> np.ndarray:
    """Create a random, normalized test vector of specified dimension."""
    dim = dim or settings.embedding_dimension
    vec = np.random.rand(dim).astype(np.float32)
    # Normalize the vector
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec  # Avoid division by zero for zero vector
    return vec / norm


@pytest.mark.asyncio
async def test_qdrant_dal_initialization(test_qdrant_client: AsyncQdrantClient):
    """Test QdrantDAL initialization with client."""
    # Act
    dal = QdrantDAL(client=test_qdrant_client)
    
    # Assert
    assert dal.client == test_qdrant_client
    assert dal._collection_name == settings.qdrant_collection_name


@pytest.mark.asyncio
async def test_qdrant_dal_initialization_fails_with_none_client():
    """Test QdrantDAL initialization fails with None client."""
    # Act & Assert
    with pytest.raises(ValueError, match="AsyncQdrantClient must be provided"):
        QdrantDAL(client=None)


@pytest.mark.asyncio
async def test_upsert_vector_creates_new_point(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test upserting a new vector creates a point in Qdrant."""
    # Arrange
    chunk_id = str(uuid.uuid4())
    vector = create_test_vector()
    text = "Test text content for semantic search"
    source_type = "test_message"
    user_id = str(uuid.uuid4())
    
    # Act
    result = await test_qdrant_dal.upsert_vector(
        chunk_id=chunk_id,
        vector=vector,
        text_content=text,
        source_type=source_type,
        user_id=user_id,
        is_private=True
    )
    
    # Assert
    assert result is True
    
    # Verify point exists in Qdrant
    client = test_qdrant_dal.client
    response = await client.retrieve(
        collection_name=settings.qdrant_collection_name,
        ids=[chunk_id],
        with_vectors=True  # Request vectors to be returned
    )
    
    assert len(response) == 1
    point = response[0]
    assert point.id == chunk_id
    
    # Check if vector is returned and verify it's as expected
    if hasattr(point, 'vector') and point.vector is not None:
        # Convert both to numpy arrays of the same type
        stored_vector = np.array(point.vector).astype(np.float32)
        original_vector = np.array(vector).astype(np.float32)
        
        logger.info(f"Comparing vectors: Original shape={original_vector.shape}, dtype={original_vector.dtype}; Stored shape={stored_vector.shape}, dtype={stored_vector.dtype}")
        
        # Safely normalize to prevent division by zero
        stored_norm = np.linalg.norm(stored_vector)
        original_norm = np.linalg.norm(original_vector)
        
        if stored_norm > 0 and original_norm > 0:
            stored_vector = stored_vector / stored_norm
            original_vector = original_vector / original_norm
        else:
            logger.warning("Vector with zero norm detected, skipping normalization")
        
        assert stored_vector.shape == original_vector.shape
        # Check using cosine similarity (much more tolerant of scale differences)
        cosine_similarity = np.dot(stored_vector, original_vector)
        assert cosine_similarity > 0.98, f"Vectors not similar enough: cosine_similarity={cosine_similarity}"
    else:
        # Fail the test explicitly if vector is missing when expected
        pytest.fail("Vector was expected but not found in the retrieved point.")
    
    assert point.payload["text_content"] == text
    assert point.payload["source_type"] == source_type
    assert point.payload["user_id"] == user_id
    assert point.payload["is_private"] is True
    assert point.payload["is_twin_interaction"] is False
    assert "timestamp" in point.payload


@pytest.mark.asyncio
async def test_upsert_vector_updates_existing_point(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test upserting with existing ID updates the point."""
    # Arrange
    chunk_id = str(uuid.uuid4())
    vector = create_test_vector()
    text = "Original text content"
    source_type = "test_message"
    user_id = str(uuid.uuid4())
    
    # Create initial point
    await test_qdrant_dal.upsert_vector(
        chunk_id=chunk_id,
        vector=vector,
        text_content=text,
        source_type=source_type,
        user_id=user_id
    )
    
    # Act - Update with new vector and content
    new_vector = create_test_vector()
    new_text = "Updated text content"
    
    result = await test_qdrant_dal.upsert_vector(
        chunk_id=chunk_id,
        vector=new_vector,
        text_content=new_text,
        source_type=source_type,
        user_id=user_id
    )
    
    # Assert
    assert result is True
    
    # Verify point was updated
    client = test_qdrant_dal.client
    response = await client.retrieve(
        collection_name=settings.qdrant_collection_name,
        ids=[chunk_id],
        with_vectors=True  # Request vectors to be returned
    )
    
    assert len(response) == 1
    point = response[0]
    assert point.payload["text_content"] == new_text
    
    # Check if vector is returned and verify it's updated
    if hasattr(point, 'vector') and point.vector is not None:
        stored_vector = np.array(point.vector).astype(np.float32)
        original_vector = np.array(new_vector).astype(np.float32)
        
        logger.info(f"Comparing vectors: Original shape={original_vector.shape}, dtype={original_vector.dtype}; Stored shape={stored_vector.shape}, dtype={stored_vector.dtype}")
        
        # Safely normalize to prevent division by zero
        stored_norm = np.linalg.norm(stored_vector)
        original_norm = np.linalg.norm(original_vector)
        
        if stored_norm > 0 and original_norm > 0:
            stored_vector = stored_vector / stored_norm
            original_vector = original_vector / original_norm
        else:
            logger.warning("Vector with zero norm detected, skipping normalization")
        
        assert stored_vector.shape == original_vector.shape
        # Check using cosine similarity (much more tolerant of scale differences)
        cosine_similarity = np.dot(stored_vector, original_vector)
        assert cosine_similarity > 0.98, f"Vectors not similar enough: cosine_similarity={cosine_similarity}"
    else:
        # Fail the test explicitly if vector is missing when expected
        pytest.fail("Vector was expected but not found in the retrieved point.")


@pytest.mark.asyncio
async def test_upsert_vector_with_optional_fields(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test upserting a vector with all optional fields."""
    # Arrange
    chunk_id = str(uuid.uuid4())
    vector = create_test_vector()
    text = "Test text content with optional fields"
    source_type = "test_document"
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    # Use timezone.utc for compatibility
    original_dt = datetime.now(timezone.utc)
    timestamp_iso = original_dt.isoformat()
    custom_metadata = {
        "priority": "high",
        "tags": ["test", "document"],
        "version": 1.0
    }
    
    # Act
    result = await test_qdrant_dal.upsert_vector(
        chunk_id=chunk_id,
        vector=vector,
        text_content=text,
        source_type=source_type,
        user_id=user_id,
        project_id=project_id,
        session_id=session_id,
        doc_id=doc_id,
        message_id=message_id,
        timestamp=timestamp_iso, # Pass ISO string
        is_twin_interaction=True,
        is_private=True,
        metadata=custom_metadata
    )
    
    # Assert
    assert result is True
    
    # Verify all fields were stored correctly
    client = test_qdrant_dal.client
    response = await client.retrieve(
        collection_name=settings.qdrant_collection_name,
        ids=[chunk_id]
    )
    
    assert len(response) == 1
    payload = response[0].payload
    
    # Check all fields
    assert payload["text_content"] == text
    assert payload["source_type"] == source_type
    assert payload["user_id"] == user_id
    assert payload["project_id"] == project_id
    assert payload["session_id"] == session_id
    assert payload["doc_id"] == doc_id
    assert payload["message_id"] == message_id
    # Compare the stored float timestamp with the original datetime's timestamp
    assert payload["timestamp"] == pytest.approx(original_dt.timestamp())
    assert payload["is_twin_interaction"] is True
    assert payload["is_private"] is True
    assert payload["priority"] == "high"
    assert payload["tags"] == ["test", "document"]
    assert payload["version"] == 1.0


@pytest.mark.asyncio
async def test_upsert_vector_generates_chunk_id_if_not_provided(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test that an empty chunk_id gets auto-generated."""
    # Arrange
    vector = create_test_vector()
    text = "Text with auto-generated ID"
    source_type = "test_message"
    user_id = str(uuid.uuid4())
    
    # Act
    result = await test_qdrant_dal.upsert_vector(
        chunk_id="",  # Empty ID should trigger auto-generation
        vector=vector,
        text_content=text,
        source_type=source_type,
        user_id=user_id
    )
    
    # Assert
    assert result is True
    
    # Verify a point was created (can't check ID)
    client = test_qdrant_dal.client
    response = await client.search(
        collection_name=settings.qdrant_collection_name,
        query_vector=vector.tolist(),
        limit=1
    )
    
    assert len(response) == 1
    assert response[0].payload["text_content"] == text


@pytest.mark.asyncio
async def test_search_vectors_with_no_filters(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test searching vectors without any filters."""
    # Arrange - Insert test points
    vectors = [create_test_vector() for _ in range(5)]
    texts = [f"Test text {i}" for i in range(5)]
    chunk_ids = [str(uuid.uuid4()) for _ in range(5)]
    
    for i, (chunk_id, vector, text) in enumerate(zip(chunk_ids, vectors, texts)):
        await test_qdrant_dal.upsert_vector(
            chunk_id=chunk_id,
            vector=vector,
            text_content=text,
            source_type="test",
            user_id="user-1"
        )
    
    # Act - Search with first vector
    results = await test_qdrant_dal.search_vectors(
        query_vector=vectors[0],
        limit=3
    )
    
    # Assert
    assert len(results) == 3
    assert results[0]["text_content"] == texts[0]  # First result should be exact match
    assert results[0]["chunk_id"] == chunk_ids[0]
    assert "score" in results[0]
    assert results[0]["score"] > 0.9  # Cosine similarity should be high for exact match


@pytest.mark.asyncio
async def test_search_vectors_with_user_filter(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test searching vectors with user filter."""
    # Arrange - Insert test points with different users
    user1_id = "user-1"
    user2_id = "user-2"
    chunk_ids = [str(uuid.uuid4()) for _ in range(5)]
    
    for i in range(5):
        user_id = user1_id if i % 2 == 0 else user2_id
        await test_qdrant_dal.upsert_vector(
            chunk_id=chunk_ids[i],
            vector=create_test_vector(),
            text_content=f"Test text {i}",
            source_type="test",
            user_id=user_id
        )
    
    # Create query vector (random for this test)
    query_vector = create_test_vector()
    
    # Act - Search with user filter
    results = await test_qdrant_dal.search_vectors(
        query_vector=query_vector,
        user_id=user1_id
    )
    
    # Assert
    assert len(results) > 0
    for result in results:
        assert result["user_id"] == user1_id


@pytest.mark.asyncio
async def test_search_vectors_with_privacy_filter(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test searching vectors with privacy filter."""
    # Arrange - Insert mix of private and public vectors
    chunk_ids = [str(uuid.uuid4()) for _ in range(10)]
    for i in range(10):
        is_private = i % 2 == 0
        await test_qdrant_dal.upsert_vector(
            chunk_id=chunk_ids[i],
            vector=create_test_vector(),
            text_content=f"Test text {i} ({'private' if is_private else 'public'})",
            source_type="test",
            user_id="user-1",
            is_private=is_private
        )
    
    # Act - Search excluding private by default
    results_public = await test_qdrant_dal.search_vectors(
        query_vector=create_test_vector(),
        limit=10
    )
    
    # Search including private
    results_all = await test_qdrant_dal.search_vectors(
        query_vector=create_test_vector(),
        limit=10,
        include_private=True
    )
    
    # Assert
    assert len(results_public) > 0
    assert len(results_all) > len(results_public)
    
    # Public results should all be non-private
    for result in results_public:
        assert result["is_private"] is False


@pytest.mark.asyncio
async def test_search_vectors_with_multiple_filters(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test searching vectors with multiple filters combined."""
    # Arrange - Insert diverse test data
    user1_id = "user-1"
    user2_id = "user-2"
    project1_id = "project-1"
    project2_id = "project-2"
    session1_id = "session-1"
    session2_id = "session-2"
    
    # Create a variety of points with different combinations
    test_data = [
        {"user": user1_id, "project": project1_id, "session": session1_id, "is_twin": False, "source": "document"},
        {"user": user1_id, "project": project1_id, "session": session2_id, "is_twin": True, "source": "message"},
        {"user": user1_id, "project": project2_id, "session": None, "is_twin": False, "source": "document"},
        {"user": user2_id, "project": project1_id, "session": session1_id, "is_twin": True, "source": "message"},
        {"user": user2_id, "project": project2_id, "session": session2_id, "is_twin": False, "source": "document"},
    ]
    
    chunk_ids = [str(uuid.uuid4()) for _ in test_data]
    
    for i, data in enumerate(test_data):
        await test_qdrant_dal.upsert_vector(
            chunk_id=chunk_ids[i],
            vector=create_test_vector(),
            text_content=f"Test text {i}",
            source_type=data["source"],
            user_id=data["user"],
            project_id=data["project"],
            session_id=data["session"],
            is_twin_interaction=data["is_twin"]
        )
    
    # Act - Search excluding twin interactions (default)
    results_exclude = await test_qdrant_dal.search_vectors(
        query_vector=create_test_vector(),
        user_id=user1_id,
        project_id=project1_id,
        # include_twin_interactions defaults to False
    )
    
    # Act - Search including twin interactions
    results_include = await test_qdrant_dal.search_vectors(
        query_vector=create_test_vector(),
        user_id=user1_id,
        project_id=project1_id,
        include_twin_interactions=True
    )
    
    # Assert
    assert len(results_exclude) > 0
    for result in results_exclude:
        assert result["user_id"] == user1_id
        assert result["project_id"] == project1_id
        assert result["is_twin_interaction"] is False
        
    assert len(results_include) > len(results_exclude)
    found_twin_interaction = any(r["is_twin_interaction"] for r in results_include if r["user_id"] == user1_id and r["project_id"] == project1_id)
    assert found_twin_interaction, "Expected to find twin interaction when include_twin_interactions=True"


@pytest.mark.asyncio
async def test_search_vectors_with_timestamp_range(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test searching vectors with timestamp range filters."""
    # Arrange - Insert points with different timestamps
    now = datetime.utcnow()
    timestamps = [
        (now - timedelta(days=5)).isoformat(),
        (now - timedelta(days=3)).isoformat(),
        (now - timedelta(days=1)).isoformat(),
        now.isoformat(),
        (now + timedelta(days=1)).isoformat()
    ]
    
    chunk_ids = [str(uuid.uuid4()) for _ in timestamps]
    
    for i, timestamp in enumerate(timestamps):
        await test_qdrant_dal.upsert_vector(
            chunk_id=chunk_ids[i],
            vector=create_test_vector(),
            text_content=f"Test text {i} at {timestamp}",
            source_type="test",
            user_id="user-1",
            timestamp=timestamp
        )
    
    # Act - Search with start timestamp only
    start_time = (now - timedelta(days=2)).isoformat()
    results_start = await test_qdrant_dal.search_vectors(
        query_vector=create_test_vector(),
        limit=10,
        timestamp_start=start_time
    )
    
    # Search with end timestamp only
    end_time = (now - timedelta(days=2)).isoformat()
    results_end = await test_qdrant_dal.search_vectors(
        query_vector=create_test_vector(),
        limit=10,
        timestamp_end=end_time
    )
    
    # Search with both start and end timestamps
    range_start = (now - timedelta(days=4)).isoformat()
    range_end = (now - timedelta(days=2)).isoformat()
    results_range = await test_qdrant_dal.search_vectors(
        query_vector=create_test_vector(),
        limit=10,
        timestamp_start=range_start,
        timestamp_end=range_end
    )
    
    # Assert
    assert len(results_start) >= 3  # Should include items from last 2 days and future
    assert len(results_end) >= 2    # Should include items older than 2 days
    assert len(results_range) >= 1  # Should include items in the 2-4 day range


@pytest.mark.asyncio
async def test_delete_vectors_by_chunk_ids(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test deleting vectors by chunk IDs."""
    # Arrange - Insert test points
    chunk_ids = [str(uuid.uuid4()) for _ in range(5)]
    
    for i, chunk_id in enumerate(chunk_ids):
        await test_qdrant_dal.upsert_vector(
            chunk_id=chunk_id,
            vector=create_test_vector(),
            text_content=f"Test text {i}",
            source_type="test",
            user_id="user-1"
        )
    
    # Act - Delete specific IDs
    delete_ids = chunk_ids[1:3]  # Delete 2 of the 5 points
    deleted_count = await test_qdrant_dal.delete_vectors(
        chunk_ids=delete_ids
    )
    
    # Verify the points were deleted
    client = test_qdrant_dal.client
    
    # Check remaining points
    remaining_ids = [chunk_ids[0]] + chunk_ids[3:]
    for chunk_id in remaining_ids:
        response = await client.retrieve(
            collection_name=settings.qdrant_collection_name,
            ids=[chunk_id]
        )
        assert len(response) == 1, f"Expected chunk {chunk_id} to remain"
    
    # Check if the points were actually deleted
    for chunk_id in delete_ids:
        response = await client.retrieve(
            collection_name=settings.qdrant_collection_name,
            ids=[chunk_id]
        )
        assert len(response) == 0, f"Expected chunk {chunk_id} to be deleted"


@pytest.mark.asyncio
async def test_delete_vectors_by_user_id(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test deleting vectors by user ID."""
    # Arrange - Insert test points for different users
    user1_id = "user-1"
    user2_id = "user-2"
    chunk_ids = [str(uuid.uuid4()) for _ in range(5)]
    
    # Create 3 points for user1 and 2 for user2
    for i in range(5):
        user_id = user1_id if i < 3 else user2_id
        await test_qdrant_dal.upsert_vector(
            chunk_id=chunk_ids[i],
            vector=create_test_vector(),
            text_content=f"Test text {i}",
            source_type="test",
            user_id=user_id
        )
    
    # Act - Delete all points for user1
    deleted_count = await test_qdrant_dal.delete_vectors(
        user_id=user1_id
    )
    
    # Verify only user2 points remain
    results = await test_qdrant_dal.search_vectors(
        query_vector=create_test_vector(),
        limit=10
    )
    
    assert len(results) == 2
    for result in results:
        assert result["user_id"] == user2_id


@pytest.mark.asyncio
async def test_delete_vectors_with_multiple_filters(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test deleting vectors with multiple filter criteria."""
    # Arrange - Insert diverse test data
    chunk_ids = [str(uuid.uuid4()) for _ in range(10)]
    for i in range(10):
        project_id = "project-1" if i % 2 == 0 else "project-2"
        session_id = "session-1" if i % 3 == 0 else "session-2"
        doc_id = "doc-1" if i % 2 == 0 else "doc-2"
        
        await test_qdrant_dal.upsert_vector(
            chunk_id=chunk_ids[i],
            vector=create_test_vector(),
            text_content=f"Test text {i}",
            source_type="test",
            user_id="user-1",
            project_id=project_id,
            session_id=session_id,
            doc_id=doc_id
        )
    
    # Act - Delete with combined filters (project_id AND session_id)
    deleted_count = await test_qdrant_dal.delete_vectors(
        project_id="project-1",
        session_id="session-1"
    )
    
    # Assert - Should only delete points matching both criteria
    expected_deleted = 0
    for i in range(10):
        if i % 2 == 0 and i % 3 == 0:  # Both project-1 and session-1
            expected_deleted += 1
    
    assert deleted_count == expected_deleted


@pytest.mark.asyncio
async def test_delete_vectors_without_filters_raises_error(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test that calling delete_vectors without filters raises an error."""
    # Act & Assert
    with pytest.raises(ValueError, match=r"At least one filter parameter \(chunk_ids or metadata field\) must be provided"):
        await test_qdrant_dal.delete_vectors()


@pytest.mark.asyncio
async def test_search_user_preferences(
    test_qdrant_dal: QdrantDAL, 
    clean_test_collection
):
    """Test searching for user preferences in Qdrant."""
    # Setup: Insert a test vector with user preferences
    test_user_id = str(uuid.uuid4())
    test_project_id = str(uuid.uuid4())
    test_chunk_id = str(uuid.uuid4())
    test_content = "I really prefer dark mode interfaces, especially at night."
    test_vector = create_test_vector()  # Use the helper function for consistency
    
    # Insert the vector
    await test_qdrant_dal.upsert_vector(
        chunk_id=test_chunk_id,
        vector=test_vector,
        text_content=test_content,
        source_type="message",
        user_id=test_user_id,
        project_id=test_project_id,
        is_twin_interaction=False
    )
    
    # Insert a twin interaction for the same user/topic
    twin_chunk_id = str(uuid.uuid4())
    await test_qdrant_dal.upsert_vector(
        chunk_id=twin_chunk_id,
        vector=test_vector * 0.9, # Slightly different vector
        text_content="User asked twin: What are my preferences for dark mode?",
        source_type="query",
        user_id=test_user_id,
        project_id=test_project_id,
        is_twin_interaction=True
    )
    
    # Generate a similar query vector (slightly perturbed version of test_vector)
    query_vector = test_vector.copy()
    # Add small random noise while keeping vector normalized
    noise = np.random.rand(len(query_vector)).astype(np.float32) * 0.1
    query_vector = query_vector + noise
    # Renormalize
    query_vector = query_vector / np.linalg.norm(query_vector)
    
    # Execute: Search excluding twin interactions
    results_exclude_twin = await test_qdrant_dal.search_user_preferences(
        query_vector=query_vector,
        user_id=test_user_id,
        decision_topic="dark mode",
        project_id=test_project_id,
        include_twin_interactions=False
    )
    
    # Verify: Results should include our test data
    assert results_exclude_twin, "No results found when excluding twin interactions"
    assert len(results_exclude_twin) > 0, "Empty results list when excluding twin interactions"
    found_original_exclude = any(r["chunk_id"] == test_chunk_id for r in results_exclude_twin)
    found_twin_exclude = any(r["chunk_id"] == twin_chunk_id for r in results_exclude_twin)
    assert found_original_exclude, "Original message chunk not found when excluding twin interactions"
    assert not found_twin_exclude, "Twin interaction chunk SHOULD NOT be found when excluding twin interactions" 