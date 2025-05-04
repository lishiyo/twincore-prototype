"""End-to-end tests for retrieval endpoints.

This test module verifies the complete flow of the retrieval endpoints by:
1. Seeding test data into the test databases
2. Making real requests to the API endpoints
3. Verifying the expected results are returned
"""

import json
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
import asyncio

from services.data_seeder_service import DataSeederService
from services.ingestion_service import IngestionService
from services.embedding_service import EmbeddingService
from services.retrieval_service import RetrievalService
from ingestion.connectors.message_connector import MessageConnector
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from main import app


@pytest.mark.asyncio
async def test_context_retrieval_e2e(seed_test_data, async_client):
    """Test the complete context retrieval flow using the actual API endpoint."""
    # Extract the test data - this is created by the seed_test_data fixture
    # The fixture result is already awaited when injected by pytest_asyncio
    user_id = seed_test_data["user_id"]
    project_id = seed_test_data["project_id"]
    session_id = seed_test_data["session_id"]
    
    # Create a request payload
    payload = {
        "query_text": "meeting notes",  # Query relevant to our seeded test data
        "project_id": project_id,
        "session_id": session_id,
        "limit": 10
    }
    
    # Send a real API request using the fixture
    response = await async_client.post("/v1/retrieve/context", json=payload)
    
    # Verify the response
    assert response.status_code == 200
    data = response.json()
    
    # Check that we got results back
    assert "chunks" in data
    assert len(data["chunks"]) > 0
    assert data["total"] > 0
    
    # Verify the content of at least one chunk
    found_relevant = False
    for chunk in data["chunks"]:
        # Check that chunks contain the required fields
        assert "chunk_id" in chunk
        assert "text" in chunk
        assert "source_type" in chunk
        assert "user_id" in chunk
        assert "score" in chunk
        
        # Verify session/project context is preserved
        assert chunk["project_id"] == project_id
        assert chunk["session_id"] == session_id
        
        # Check if any of the chunks contain relevant content
        if "meeting" in chunk["text"].lower() or "notes" in chunk["text"].lower():
            found_relevant = True
    
    # We should have found at least one relevant chunk
    assert found_relevant, "No relevant chunks found in search results"


@pytest.mark.asyncio
async def test_private_memory_retrieval_e2e(seed_private_test_data, async_client):
    """Test the complete private memory retrieval flow using the actual API endpoint."""
    # Extract the test data
    # The fixture result is already awaited when injected by pytest_asyncio
    user_id = seed_private_test_data["user_id"]
    project_id = seed_private_test_data["project_id"]
    
    # Create a request payload
    payload = {
        "user_id": user_id,
        "query_text": "personal document",  # Query relevant to our seeded test data
        "project_id": project_id,
        "limit": 5
    }
    
    # Send a real API request using the fixture
    response = await async_client.post("/v1/retrieve/private_memory", json=payload)
    
    # Verify the response
    assert response.status_code == 200
    data = response.json()
    
    # Check that we got results back
    assert "chunks" in data
    assert len(data["chunks"]) > 0
    assert data["total"] > 0
    
    # Verify the content of at least one chunk
    for chunk in data["chunks"]:
        # Check that chunks contain the required fields
        assert "chunk_id" in chunk
        assert "text" in chunk
        assert "source_type" in chunk
        assert "user_id" in chunk
        assert "score" in chunk
        
        # Verify user context is preserved
        assert chunk["user_id"] == user_id


@pytest.mark.asyncio
async def test_query_ingestion_in_private_memory_e2e(seed_private_test_data, async_client):
    """Test that queries to private memory are properly ingested as twin interactions."""
    # Extract the test data
    # The fixture result is already awaited when injected by pytest_asyncio
    user_id = seed_private_test_data["user_id"]
    project_id = seed_private_test_data["project_id"]
    
    # Generate a unique query text so we can verify it was ingested
    unique_query = f"find my personal document {uuid.uuid4()}"
    
    # Create a request payload
    payload = {
        "user_id": user_id,
        "query_text": unique_query,
        "project_id": project_id,
        "limit": 5
    }
    
    # Send a real API request using the fixture
    response = await async_client.post("/v1/retrieve/private_memory", json=payload)
    
    # Verify the response is successful
    assert response.status_code == 200
    
    # Add a small delay to allow Qdrant to index the content
    await asyncio.sleep(2)  # Increase delay to 2 seconds
    
    # Now verify the query was actually ingested
    # Initialize DALs and services
    qdrant_client = get_async_qdrant_client()  # No await needed
    neo4j_driver = await get_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    embedding_service = EmbeddingService()
    
    # Get a proper embedding for our query to improve search results
    query_embedding = await embedding_service.get_embedding(unique_query)
    
    # Search for our unique query in Qdrant with proper vector
    search_results = await qdrant_dal.search_vectors(
        query_vector=query_embedding,
        limit=100,
        user_id=user_id,
        include_private=True,
        exclude_twin_interactions=False  # Include twin interactions to find our query
    )
    
    # Debug: Print search results to see what we actually got
    print(f"\nSearching for: {unique_query}")
    print(f"Number of results: {len(search_results)}")
    for i, result in enumerate(search_results):
        print(f"\nResult {i+1}:")
        print(f"  text_content: {result.get('text_content', 'None')}")
        print(f"  is_twin_interaction: {result.get('is_twin_interaction', 'None')}")
        print(f"  source_type: {result.get('source_type', 'None')}")
        print(f"  score: {result.get('score', 'None')}")
    
    # Check if our unique query was ingested by checking each result directly
    found = False
    for result in search_results:
        text_content = result.get("text_content", "")
        # Try partial matching - uuid might be different in stored format
        if unique_query[:30] in text_content:
            found = True
            # Verify it was marked as a twin interaction
            assert result.get("is_twin_interaction") is True
            break
    
    # As an alternative check, try direct substring search
    if not found:
        # Try with exactly "find my personal document" and see if we get any containing that
        for result in search_results:
            if "find my personal document" in result.get("text_content", ""):
                found = True
                print(f"Found using partial match: {result.get('text_content')}")
                assert result.get("is_twin_interaction") is True
                break
    
    assert found, f"The query text '{unique_query}' was not found in the database, suggesting it wasn't ingested"


# Fixtures for Test Data

@pytest_asyncio.fixture
async def seed_test_data():
    """Seed test data for retrieval tests into the test databases.
    
    Returns a dict with the key IDs (user_id, project_id, session_id) for the test data.
    """
    # Generate unique IDs for our test data
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    # Initialize services
    qdrant_client = get_async_qdrant_client()  # No await needed
    neo4j_driver = await get_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    ingestion_service = IngestionService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service
    )
    
    # Create MessageConnector to handle message ingestion
    message_connector = MessageConnector(ingestion_service=ingestion_service)
    
    # Create test data for retrieval tests
    await message_connector.ingest_message({
        "text": "Today's meeting notes: We discussed the roadmap for Q3.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message"
    })
    
    await message_connector.ingest_message({
        "text": "Key action item from the meeting: Improve the search algorithm.",
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id,
        "source_type": "message"
    })
    
    # Return the key IDs for use in the tests
    return {
        "user_id": user_id,
        "project_id": project_id,
        "session_id": session_id
    }


@pytest_asyncio.fixture
async def seed_private_test_data():
    """Seed private test data for retrieval tests into the test databases.
    
    Returns a dict with the key IDs (user_id, project_id) for the test data.
    """
    # Generate unique IDs for our test data
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    
    # Initialize services
    qdrant_client = get_async_qdrant_client()  # No await needed
    neo4j_driver = await get_neo4j_driver()
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    ingestion_service = IngestionService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service
    )
    
    # Create MessageConnector to handle message ingestion
    message_connector = MessageConnector(ingestion_service=ingestion_service)
    
    # Create test data with both private and public content
    # Private content
    await message_connector.ingest_message({
        "text": "This is my personal document with private information.",
        "user_id": user_id,
        "project_id": project_id,
        "is_twin_chat": True,  # Mark as private
        "source_type": "message"
    })
    
    # Public content
    await message_connector.ingest_message({
        "text": "This is a public message everyone can see.",
        "user_id": user_id,
        "project_id": project_id,
        "is_twin_chat": False,  # Not private
        "source_type": "message"
    })
    
    # Return the key IDs for use in the tests
    return {
        "user_id": user_id,
        "project_id": project_id
    } 