"""End-to-end tests for the ingestion API endpoints.

These tests verify that data is properly stored in databases when ingested
through the API endpoints.
"""

import pytest
import pytest_asyncio
import uuid
import os
from httpx import AsyncClient
import asyncio
from urllib.parse import urljoin

from main import app
from core.config import settings
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL


@pytest_asyncio.fixture(scope="module")
async def qdrant_client():
    """Create a Qdrant client for testing."""
    # Create a client directly instead of using the cached function
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=10
    )
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="module")
async def neo4j_driver():
    """Create a Neo4j driver for testing."""
    # Create a driver directly instead of using the cached function
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    yield driver
    await driver.close()


@pytest_asyncio.fixture(scope="module")
async def qdrant_dal(qdrant_client):
    """Create a QdrantDAL for testing."""
    return QdrantDAL(client=qdrant_client)


@pytest_asyncio.fixture(scope="module")
async def neo4j_dal(neo4j_driver):
    """Create a Neo4jDAL for testing."""
    return Neo4jDAL(driver=neo4j_driver)


@pytest_asyncio.fixture
async def api_client():
    """Create an async client for testing the API."""
    base_url = os.getenv("TEST_API_URL", "http://localhost:8000")
    async with AsyncClient(app=app, base_url=base_url) as client:
        yield client


@pytest.mark.asyncio
async def test_ingest_message_e2e(api_client, qdrant_dal, neo4j_dal):
    """Test the message ingestion API endpoint end-to-end.
    
    This test verifies that a message ingested through the API is properly
    stored in both Qdrant and Neo4j.
    """
    # Generate unique IDs for this test
    message_id = str(uuid.uuid4())
    user_id = "test-user-" + str(uuid.uuid4())[:8]
    session_id = "test-session-" + str(uuid.uuid4())[:8]
    
    # Test message data
    message_data = {
        "message_id": message_id,
        "content": "This is an E2E test message",
        "user_id": user_id,
        "session_id": session_id,
        "is_twin_interaction": True,
        "is_private": False
    }
    
    # Send request to the API
    response = await api_client.post("/v1/api/ingest/message", json=message_data)
    assert response.status_code == 200
    
    # Get the response data
    data = response.json()
    assert data["message_id"] == message_id
    chunk_id = data["chunk_id"]
    assert chunk_id == f"msg_{message_id}"
    assert data["success"] is True
    
    # Give it a small delay to ensure processing is complete
    await asyncio.sleep(1)
    
    # Verify data in Qdrant
    search_result = await qdrant_dal.search_vectors(
        query_text="This is an E2E test message",
        limit=10,
        filters={
            "message_id": message_id
        }
    )
    
    # Check that the message was found in Qdrant
    assert len(search_result) > 0
    found_in_qdrant = False
    for item in search_result:
        if item.metadata.get("message_id") == message_id:
            found_in_qdrant = True
            assert item.metadata.get("user_id") == user_id
            assert item.metadata.get("session_id") == session_id
            assert item.metadata.get("is_twin_interaction") is True
            assert item.metadata.get("is_private") is False
            assert item.metadata.get("text_content") == "This is an E2E test message"
            break
    
    assert found_in_qdrant, "Message not found in Qdrant"
    
    # Verify data in Neo4j
    # 1. Check Chunk node
    chunk_node = await neo4j_dal.get_node("Chunk", {"chunk_id": chunk_id})
    assert chunk_node is not None
    assert chunk_node["chunk_id"] == chunk_id
    assert chunk_node["is_twin_interaction"] is True
    assert chunk_node["is_private"] is False
    
    # 2. Check Message node
    message_node = await neo4j_dal.get_node("Message", {"message_id": message_id})
    assert message_node is not None
    assert message_node["message_id"] == message_id
    
    # 3. Check User node
    user_node = await neo4j_dal.get_node("User", {"user_id": user_id})
    assert user_node is not None
    assert user_node["user_id"] == user_id
    
    # 4. Check Session node
    session_node = await neo4j_dal.get_node("Session", {"session_id": session_id})
    assert session_node is not None
    assert session_node["session_id"] == session_id
    
    # 5. Check relationships
    # User-Message relationship
    user_message_rel = await neo4j_dal.get_relationship(
        "User", {"user_id": user_id},
        "Message", {"message_id": message_id},
        "AUTHORED"
    )
    assert user_message_rel is not None
    
    # User-Session relationship
    user_session_rel = await neo4j_dal.get_relationship(
        "User", {"user_id": user_id},
        "Session", {"session_id": session_id},
        "PARTICIPATED_IN"
    )
    assert user_session_rel is not None
    
    # Message-Session relationship
    message_session_rel = await neo4j_dal.get_relationship(
        "Message", {"message_id": message_id},
        "Session", {"session_id": session_id},
        "POSTED_IN"
    )
    assert message_session_rel is not None
    
    # Chunk-Message relationship
    chunk_message_rel = await neo4j_dal.get_relationship(
        "Chunk", {"chunk_id": chunk_id},
        "Message", {"message_id": message_id},
        "PART_OF"
    )
    assert chunk_message_rel is not None
    
    # Clean up after test
    await qdrant_dal.delete_vectors([chunk_id])
    
    # Clean up Neo4j nodes (order matters due to relationships)
    await neo4j_dal.delete_node("Chunk", {"chunk_id": chunk_id})
    await neo4j_dal.delete_node("Message", {"message_id": message_id})
    await neo4j_dal.delete_node("Session", {"session_id": session_id})
    await neo4j_dal.delete_node("User", {"user_id": user_id}) 