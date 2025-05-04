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
import logging
from datetime import datetime
from urllib.parse import urlencode

from services.data_seeder_service import DataSeederService
from services.ingestion_service import IngestionService
from services.embedding_service import EmbeddingService
from services.retrieval_service import RetrievalService
from ingestion.connectors.message_connector import MessageConnector
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from main import app
from core.db_setup.qdrant_setup import setup_qdrant_collection
from qdrant_client import models as qdrant_models

logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.xdist_group("neo4j")  # Group Neo4j tests
@pytest.mark.xdist_group("qdrant") # Group Qdrant tests
class TestRetrievalE2E:
    """End-to-end tests for retrieval functionality."""

    @pytest.fixture(autouse=True)
    async def ensure_collection_exists(self):
        """
        Fixture to ensure the Qdrant collection exists before EVERY test.
        
        This runs before each test method in the class due to autouse=True.
        Some tests in the test suite delete the collection as part of their cleanup.
        This fixture ensures the collection is recreated before our tests run.
        """
        logger.error("==== RETRIEVAL TEST: CREATING QDRANT COLLECTION BEFORE TEST ====")
        print("==== RETRIEVAL TEST: CREATING QDRANT COLLECTION BEFORE TEST ====")
        
        qdrant_client = get_async_qdrant_client()
        
        # Always attempt to delete the collection first to ensure a clean state
        try:
            await qdrant_client.delete_collection(collection_name="twin_memory")
            logger.error("Deleted existing twin_memory collection")
            print("RETRIEVAL TEST: Deleted existing twin_memory collection")
        except Exception as e:
            # Collection might not exist, ignore the error
            logger.error(f"Note: Couldn't delete collection (might not exist): {e}")
            print(f"RETRIEVAL TEST: Couldn't delete collection: {e}")
        
        # Wait a moment after deletion
        await asyncio.sleep(1)
        
        # Create the collection
        try:
            logger.error("Creating fresh twin_memory collection")
            print("RETRIEVAL TEST: Creating fresh twin_memory collection")
            await qdrant_client.create_collection(
                collection_name="twin_memory",
                vectors_config=qdrant_models.VectorParams(
                    size=1536,  # OpenAI embedding size
                    distance=qdrant_models.Distance.COSINE
                )
            )
            
            # Verify the collection was created
            collections = await qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]
            logger.error(f"Collections after setup: {collection_names}")
            print(f"RETRIEVAL TEST: Collections after setup: {collection_names}")
            assert "twin_memory" in collection_names, "Failed to create twin_memory collection"
            
            # Wait to ensure collection is ready
            await asyncio.sleep(2)
            logger.error("Collection twin_memory is ready for retrieval test")
            print("RETRIEVAL TEST: Collection twin_memory is ready for test")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            print(f"RETRIEVAL TEST: Error creating collection: {e}")
            raise
        
        # Yield control back to the test
        yield
        
        # No cleanup after - let the test complete normally

    @pytest_asyncio.fixture
    async def seed_test_data(self):
        """Seed test data for retrieval tests into the test databases.
        
        Returns a dict with the key IDs (user_id, project_id, session_id) for the test data.
        """
        # Generate unique IDs for our test data
        user_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Initialize services with TEST database connections
        from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
        
        qdrant_client = await get_test_async_qdrant_client()
        neo4j_driver = await get_test_neo4j_driver()
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
    async def seed_private_test_data(self):
        """Seed private test data for retrieval tests into the test databases.
        
        Returns a dict with the key IDs (user_id, project_id) for the test data.
        """
        # Generate unique IDs for our test data
        user_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        
        # Initialize services with TEST database connections
        from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
        
        qdrant_client = await get_test_async_qdrant_client()
        neo4j_driver = await get_test_neo4j_driver()
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

    @pytest_asyncio.fixture
    async def use_test_databases(self):
        """Override FastAPI dependencies to use test databases for E2E tests.
        
        This fixture ensures that all endpoints in the API use the test databases
        during E2E tests rather than the default production databases.
        """
        # Import the test database utilities
        from tests.e2e.test_utils import get_test_neo4j_driver, get_test_async_qdrant_client, get_test_qdrant_client
        
        # Store original functions
        from core.db_clients import get_neo4j_driver as original_get_neo4j_driver
        from core.db_clients import get_async_qdrant_client as original_get_async_qdrant_client
        from api.routers.retrieve_router import get_retrieval_service as original_get_retrieval_service
        from api.routers.retrieve_router import get_retrieval_service_with_message_connector as original_get_retrieval_service_with_connector
        
        # Override the Neo4j driver function to use the test database
        async def test_get_neo4j_driver():
            return await get_test_neo4j_driver()
            
        # Override the Qdrant client function to use the test database
        # Important: We need to await the async client creation
        async def test_get_async_qdrant_client():
            client = await get_test_async_qdrant_client()
            return client
        
        # Create a custom retrieval service function that uses the test databases
        async def test_get_retrieval_service():
            qdrant_client = await test_get_async_qdrant_client()
            neo4j_driver = await test_get_neo4j_driver()
            
            qdrant_dal = QdrantDAL(client=qdrant_client)
            neo4j_dal = Neo4jDAL(driver=neo4j_driver)
            embedding_service = EmbeddingService()
            
            return RetrievalService(
                qdrant_dal=qdrant_dal,
                neo4j_dal=neo4j_dal,
                embedding_service=embedding_service,
            )
        
        # Create a custom retrieval service with message connector that uses test databases
        async def test_get_retrieval_service_with_connector():
            qdrant_client = await test_get_async_qdrant_client()
            neo4j_driver = await test_get_neo4j_driver()
            
            qdrant_dal = QdrantDAL(client=qdrant_client)
            neo4j_dal = Neo4jDAL(driver=neo4j_driver)
            embedding_service = EmbeddingService()
            
            # Create IngestionService for the connector
            ingestion_service = IngestionService(
                qdrant_dal=qdrant_dal,
                neo4j_dal=neo4j_dal,
                embedding_service=embedding_service,
            )
            
            # Create MessageConnector using IngestionService
            message_connector = MessageConnector(ingestion_service=ingestion_service)
            
            return RetrievalService(
                qdrant_dal=qdrant_dal,
                neo4j_dal=neo4j_dal,
                embedding_service=embedding_service,
                message_connector=message_connector,
            )
        
        # Apply the overrides
        app.dependency_overrides[original_get_retrieval_service] = test_get_retrieval_service
        app.dependency_overrides[original_get_retrieval_service_with_connector] = test_get_retrieval_service_with_connector
        
        # Yield control back to the test
        yield
        
        # Cleanup: Restore the original dependencies
        if original_get_retrieval_service in app.dependency_overrides:
            del app.dependency_overrides[original_get_retrieval_service]
        if original_get_retrieval_service_with_connector in app.dependency_overrides:
            del app.dependency_overrides[original_get_retrieval_service_with_connector]

    @pytest.mark.asyncio
    async def test_context_retrieval_e2e(self, seed_test_data, async_client, use_test_databases):
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
        response = await async_client.get(
            "/v1/retrieve/context",
            params=payload
        )
        
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
    async def test_private_memory_retrieval_e2e(self, seed_private_test_data, async_client, use_test_databases):
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
    async def test_query_ingestion_in_private_memory_e2e(self, seed_private_test_data, async_client, use_test_databases):
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
        # Initialize DALs and services with TEST database connections
        from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
        
        qdrant_client = await get_test_async_qdrant_client()
        neo4j_driver = await get_test_neo4j_driver()
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

    @pytest_asyncio.fixture
    async def seed_related_content_data(self):
        """Seed test data with related content and relationships for testing related content retrieval.
        
        Returns key IDs for the test data.
        """
        # Generate unique IDs for our test data
        user_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Initialize services with TEST database connections
        from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
        
        qdrant_client = await get_test_async_qdrant_client()
        neo4j_driver = await get_test_neo4j_driver()
        qdrant_dal = QdrantDAL(client=qdrant_client)
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        embedding_service = EmbeddingService()
        
        print("Using TEST database connections for data setup")
        
        # Create unique content IDs for our nodes - use exact UUIDs
        source_chunk_id = str(uuid.uuid4())
        related_chunk_id1 = str(uuid.uuid4())
        related_chunk_id2 = str(uuid.uuid4())
        
        print(f"Created source chunk ID: {source_chunk_id}")
        print(f"Created related chunk ID 1: {related_chunk_id1}")
        print(f"Created related chunk ID 2: {related_chunk_id2}")
        
        # Directly create Content nodes in Neo4j with known IDs
        source_props = {
            "chunk_id": source_chunk_id,  # Use chunk_id as the constraint property
            "text_content": "We need to discuss the UI design for the new feature.",
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "source_type": "message",
            "timestamp": datetime.now().isoformat(),
            "is_private": False  # Explicitly set as public
        }
        
        related_props1 = {
            "chunk_id": related_chunk_id1,
            "text_content": "I think we should use a card-based layout for the UI design.",
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "source_type": "message",
            "timestamp": datetime.now().isoformat(),
            "is_private": False  # Explicitly set as public
        }
        
        related_props2 = {
            "chunk_id": related_chunk_id2,
            "text_content": "The color scheme should match our brand guidelines.",
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "source_type": "message",
            "timestamp": datetime.now().isoformat(),
            "is_private": False  # Explicitly set as public
        }
        
        # Create the Content nodes directly in Neo4j
        await neo4j_dal.create_node_if_not_exists(
            label="Content",
            properties=source_props,
            constraints={"chunk_id": source_chunk_id}
        )
        
        await neo4j_dal.create_node_if_not_exists(
            label="Content",
            properties=related_props1,
            constraints={"chunk_id": related_chunk_id1}
        )
        
        await neo4j_dal.create_node_if_not_exists(
            label="Content",
            properties=related_props2,
            constraints={"chunk_id": related_chunk_id2}
        )
        
        # Add a small delay to ensure nodes are indexed before creating relationships
        await asyncio.sleep(1)
        
        # Create vector embeddings for these nodes in Qdrant
        source_embedding = await embedding_service.get_embedding(source_props["text_content"])
        related_embedding1 = await embedding_service.get_embedding(related_props1["text_content"])
        related_embedding2 = await embedding_service.get_embedding(related_props2["text_content"])
        
        await qdrant_dal.upsert_vector(
            chunk_id=source_chunk_id,
            vector=source_embedding,
            text_content=source_props["text_content"],
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            source_type="message",
            timestamp=source_props["timestamp"]
        )
        
        await qdrant_dal.upsert_vector(
            chunk_id=related_chunk_id1,
            vector=related_embedding1,
            text_content=related_props1["text_content"],
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            source_type="message",
            timestamp=related_props1["timestamp"]
        )
        
        await qdrant_dal.upsert_vector(
            chunk_id=related_chunk_id2,
            vector=related_embedding2,
            text_content=related_props2["text_content"],
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            source_type="message",
            timestamp=related_props2["timestamp"]
        )
        
        # Create relationships between source and related chunks
        result1 = await neo4j_dal.create_relationship_if_not_exists(
            start_label="Content",
            start_constraints={"chunk_id": source_chunk_id},
            end_label="Content",
            end_constraints={"chunk_id": related_chunk_id1},
            relationship_type="RELATED_TO",
            properties={"strength": 0.9}
        )
        
        result2 = await neo4j_dal.create_relationship_if_not_exists(
            start_label="Content",
            start_constraints={"chunk_id": source_chunk_id},
            end_label="Content",
            end_constraints={"chunk_id": related_chunk_id2},
            relationship_type="RELATED_TO",
            properties={"strength": 0.8}
        )
        
        print(f"Created relationship 1: {result1}")
        print(f"Created relationship 2: {result2}")
        
        # Verify the nodes exist and are connected by running a query
        async with neo4j_driver.session() as session:
            # First check if nodes exist
            node_query = """
            MATCH (c:Content)
            WHERE c.chunk_id IN [$source_id, $related_id1, $related_id2]
            RETURN c.chunk_id as id
            """
            node_result = await session.run(
                node_query, 
                {
                    "source_id": source_chunk_id,
                    "related_id1": related_chunk_id1,
                    "related_id2": related_chunk_id2
                }
            )
            node_rows = await node_result.data()
            
            print(f"Found {len(node_rows)} Content nodes in Neo4j:")
            for row in node_rows:
                print(f"  Node ID: {row['id']}")
            assert len(node_rows) == 3, "Failed to find all created Content nodes"
            
            # Check relationships AFTER creation attempts
            rel_query = """
            MATCH (src:Content {chunk_id: $source_id})-[r:RELATED_TO]->(dest:Content)
            RETURN src.chunk_id as source, dest.chunk_id as destination, type(r) as relationship_type
            """
            rel_result = await session.run(rel_query, {"source_id": source_chunk_id})
            rel_rows = await rel_result.data()
            
            # Log the relationship results for debugging
            print(f"Found {len(rel_rows)} relationships from source {source_chunk_id}:")
            for row in rel_rows:
                print(f"  {row['source']} -> {row['relationship_type']} -> {row['destination']}")
            
            # Assertion to catch issues early - we should have exactly 2 relationships now
            assert len(rel_rows) == 2, f"Expected exactly 2 relationships for source node {source_chunk_id}, but found {len(rel_rows)}"

            # Log the exact Cypher query that would be used by the get_related_content method
            debug_query = f"""
            MATCH (c1:Content {{chunk_id: "{source_chunk_id}"}})
            MATCH (c1)-[*1..2]-(c2:Content)
            WHERE NOT c2.is_private
            RETURN c2, 
                [(c2)-[r]->(n) | {{type: type(r), target_id: n.chunk_id, target_type: labels(n)[0]}}] as outgoing_rels,
                [(n)-[r]->(c2) | {{type: type(r), source_id: n.chunk_id, source_type: labels(n)[0]}}] as incoming_rels
            LIMIT 10
            """
            print(f"Debug query that would be executed:\n{debug_query}")
            
            # Try running our own simplified query
            simple_query = """
            MATCH (c1:Content {chunk_id: $source_id})-[r]-(c2:Content)
            RETURN c2.chunk_id as related_id
            """
            simple_result = await session.run(simple_query, {"source_id": source_chunk_id})
            simple_rows = await simple_result.data()
            
            print(f"Simple query found {len(simple_rows)} related Content nodes:")
            for row in simple_rows:
                print(f"  Related ID: {row['related_id']}")
            
            # Assertion to catch issues early - we should have at least 2 relationships
            assert len(simple_rows) >= 2, f"Simple query expected at least 2 relationships for source node {source_chunk_id}, but found {len(simple_rows)}"
        
        return {
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "source_chunk_id": source_chunk_id,
            "related_chunk_ids": [related_chunk_id1, related_chunk_id2]
        }

    @pytest.mark.asyncio
    async def test_related_content_retrieval_e2e(self, seed_related_content_data, async_client, use_test_databases):
        """Test the complete related content retrieval flow using graph traversal."""
        # Extract the test data
        source_chunk_id = seed_related_content_data["source_chunk_id"]
        related_chunk_ids = seed_related_content_data["related_chunk_ids"]
        
        # Print the source chunk ID for debugging
        print(f"\nQuerying for related content with source chunk ID: {source_chunk_id}")
        print(f"Expected related chunk IDs: {related_chunk_ids}")
        
        # Create request parameters
        params = {
            "chunk_id": source_chunk_id,
            "limit": 10,
            "max_depth": 2,
            "relationship_types": ["RELATED_TO"]  # This is already a list, but we'll make sure it's used correctly
        }
        
        # Debug: Print params before constructing URL
        print(f"Parameters before URL construction: {params}")
        print(f"Relationship types type: {type(params['relationship_types'])}, value: {params['relationship_types']}")
        
        # Build the URL with query parameters, repeating relationship_types if necessary
        url_params = {
            "chunk_id": params['chunk_id'],
            "limit": params['limit'],
            "max_depth": params['max_depth'],
        }
        url = f"/v1/retrieve/related_content?{urlencode(url_params)}"
        
        # Add relationship types individually - FastAPI can handle repeated query params for list types
        # We need to ensure we pass multiple relationship_types parameters, one for each value
        if "relationship_types" in params and params["relationship_types"]:
            for rel_type in params["relationship_types"]:
                url += f"&relationship_types={rel_type}"
                print(f"Added relationship type to URL: {rel_type}")
        
        print(f"Final API request URL: {url}")
        
        # Before calling the API, use the Neo4jDAL directly to verify the data exists
        from tests.e2e.test_utils import get_test_neo4j_driver
        
        neo4j_driver = await get_test_neo4j_driver()
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        
        # Direct check using the Neo4jDAL method
        related_content = await neo4j_dal.get_related_content(
            chunk_id=source_chunk_id,
            relationship_types=["RELATED_TO"],
            limit=10,
            include_private=False,
            max_depth=2
        )
        
        print(f"Direct Neo4jDAL call found {len(related_content)} related items")
        for item in related_content:
            print(f"  Related item: {item.get('chunk_id')}")
        
        # Send a real API request
        response = await async_client.get(url)
        
        # Verify the response
        print(f"API response status: {response.status_code}")
        data = response.json()
        
        # Debug the response data
        print(f"Response data: {data}")
        
        # Check that we got results back
        assert "chunks" in data
        assert data["total"] > 0, f"Expected results but got 0. Make sure the related content retrieval is working properly."
        
        # Verify that the related chunks are present in the results
        retrieved_chunk_ids = [chunk["chunk_id"] for chunk in data["chunks"]]
        
        # Ensure at least one of our related chunks is in the results
        # (We may not get all due to limits or filtering)
        found_related_content = any(chunk_id in retrieved_chunk_ids for chunk_id in related_chunk_ids)
        assert found_related_content, "None of the expected related chunks were found in the results"
        
        # Verify that relationship metadata is included
        for chunk in data["chunks"]:
            # Check for basic fields
            assert "text" in chunk
            assert "source_type" in chunk
            
            # Check for metadata - at least one chunk should have relationship data
            if "metadata" in chunk and "outgoing_relationships" in chunk["metadata"]:
                # Verify the relationship type matches what we created
                relationships = chunk["metadata"]["outgoing_relationships"]
                if relationships:
                    assert any(rel["type"] == "RELATED_TO" for rel in relationships)

    @pytest_asyncio.fixture
    async def seed_topic_data(self):
        """Seed test data for topic retrieval tests.
        
        Creates content with topic relationships for testing the topic endpoint.
        """
        # Generate unique IDs for our test data
        user_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Create a unique topic name for this test run
        topic_name = f"test-topic-{uuid.uuid4()}"
        
        # Initialize services with TEST database connections
        from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
        
        qdrant_client = await get_test_async_qdrant_client()
        neo4j_driver = await get_test_neo4j_driver()
        qdrant_dal = QdrantDAL(client=qdrant_client)
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        embedding_service = EmbeddingService()
        
        print("Using TEST database connections for data setup")
        
        # Create unique content IDs for our messages - use exact UUIDs
        chunk_id1 = str(uuid.uuid4())
        chunk_id2 = str(uuid.uuid4())
        topic_id = str(uuid.uuid4())
        
        print(f"Created topic ID: {topic_id}")
        print(f"Created chunk ID 1: {chunk_id1}")
        print(f"Created chunk ID 2: {chunk_id2}")
        
        # First, create a Topic node in Neo4j
        topic_props = {
            "id": topic_id,
            "name": topic_name,
            "description": "A test topic for e2e tests"
        }
        
        await neo4j_dal.create_node_if_not_exists(
            label="Topic",
            properties=topic_props,
            constraints={"id": topic_id}
        )
        
        # Create Content nodes directly in Neo4j
        content_props1 = {
            "chunk_id": chunk_id1,
            "text_content": f"This message discusses the {topic_name} in detail.",
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "source_type": "message",
            "timestamp": datetime.now().isoformat()
        }
        
        content_props2 = {
            "chunk_id": chunk_id2,
            "text_content": f"Here's another message mentioning {topic_name}.",
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "source_type": "message",
            "timestamp": datetime.now().isoformat()
        }
        
        await neo4j_dal.create_node_if_not_exists(
            label="Content",
            properties=content_props1,
            constraints={"chunk_id": chunk_id1}
        )
        
        await neo4j_dal.create_node_if_not_exists(
            label="Content",
            properties=content_props2,
            constraints={"chunk_id": chunk_id2}
        )
        
        # Create vector embeddings for these nodes in Qdrant
        content_embedding1 = await embedding_service.get_embedding(content_props1["text_content"])
        content_embedding2 = await embedding_service.get_embedding(content_props2["text_content"])
        
        await qdrant_dal.upsert_vector(
            chunk_id=chunk_id1,
            vector=content_embedding1,
            text_content=content_props1["text_content"],
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            source_type="message",
            timestamp=content_props1["timestamp"]
        )
        
        await qdrant_dal.upsert_vector(
            chunk_id=chunk_id2,
            vector=content_embedding2,
            text_content=content_props2["text_content"],
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            source_type="message",
            timestamp=content_props2["timestamp"]
        )
        
        # Create MENTIONS relationships between content and topic
        result1 = await neo4j_dal.create_relationship_if_not_exists(
            start_label="Content",
            start_constraints={"chunk_id": chunk_id1},
            end_label="Topic",
            end_constraints={"id": topic_id},
            relationship_type="MENTIONS",
            properties={"confidence": 0.95}
        )
        
        result2 = await neo4j_dal.create_relationship_if_not_exists(
            start_label="Content",
            start_constraints={"chunk_id": chunk_id2},
            end_label="Topic",
            end_constraints={"id": topic_id},
            relationship_type="MENTIONS",
            properties={"confidence": 0.9}
        )
        
        print(f"Created relationship 1: {result1}")
        print(f"Created relationship 2: {result2}")
        
        # Verify the relationships were created
        async with neo4j_driver.session() as session:
            # First check if nodes exist
            node_query = """
            MATCH (c:Content), (t:Topic {name: $topic_name})
            WHERE c.chunk_id IN [$chunk_id1, $chunk_id2]
            RETURN c.chunk_id as chunk_id, t.name as topic_name
            """
            node_result = await session.run(
                node_query, 
                {
                    "topic_name": topic_name,
                    "chunk_id1": chunk_id1,
                    "chunk_id2": chunk_id2
                }
            )
            node_rows = await node_result.data()
            
            print(f"Found {len(node_rows)} Content nodes and topic in Neo4j:")
            for row in node_rows:
                print(f"  Content: {row.get('chunk_id', 'N/A')}, Topic: {row.get('topic_name', 'N/A')}")
            
            query = """
            MATCH (c:Content)-[r:MENTIONS]->(t:Topic {name: $topic_name})
            RETURN c.chunk_id as source, t.name as topic, type(r) as relationship_type
            """
            result = await session.run(query, {"topic_name": topic_name})
            rows = await result.data()
            
            # Log the results for debugging
            print(f"Found {len(rows)} content chunks mentioning topic '{topic_name}':")
            for row in rows:
                print(f"  {row['source']} -> {row['relationship_type']} -> {row['topic']}")
            
            # Try a simpler query to check relationships
            simple_query = """
            MATCH (c:Content)-[r:MENTIONS]->(t:Topic)
            WHERE t.name = $topic_name
            RETURN c.chunk_id as chunk_id
            """
            simple_result = await session.run(simple_query, {"topic_name": topic_name})
            simple_rows = await simple_result.data()
            
            print(f"Simple query found {len(simple_rows)} relationships:")
            for row in simple_rows:
                print(f"  Content chunk: {row['chunk_id']}")
            
            # Assertion to catch issues early
            assert len(rows) >= 2, f"Expected at least 2 relationships for topic '{topic_name}', but found {len(rows)}"
        
        return {
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "topic_name": topic_name,
            "topic_id": topic_id,
            "chunk_ids": [chunk_id1, chunk_id2]
        }

    @pytest_asyncio.fixture
    async def seed_multi_user_private_data(self):
        """Seed test data for multiple users with private and public content.
        
        Creates content for two users with mixed private/public permissions to test
        cross-user privacy filtering.
        """
        # Generate unique IDs for two test users
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())  # Shared project
        
        # Initialize services with TEST database connections
        from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver
        
        qdrant_client = await get_test_async_qdrant_client()
        neo4j_driver = await get_test_neo4j_driver()
        qdrant_dal = QdrantDAL(client=qdrant_client)
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        embedding_service = EmbeddingService()
        
        ingestion_service = IngestionService(
            qdrant_dal=qdrant_dal,
            neo4j_dal=neo4j_dal,
            embedding_service=embedding_service
        )
        
        message_connector = MessageConnector(ingestion_service=ingestion_service)
        
        # Create test data for both users with varying privacy settings
        
        # User 1 private content (only visible to user 1)
        await message_connector.ingest_message({
            "text": "User 1's private notes about project planning.",
            "user_id": user1_id,
            "project_id": project_id,
            "is_private": True,
            "is_twin_chat": True,
            "source_type": "message"
        })
        
        # User 1 public content (visible to all)
        await message_connector.ingest_message({
            "text": "User 1's public message in team discussion.",
            "user_id": user1_id,
            "project_id": project_id,
            "is_private": False,
            "source_type": "message"
        })
        
        # User 2 private content (only visible to user 2)
        await message_connector.ingest_message({
            "text": "User 2's confidential meeting notes.",
            "user_id": user2_id,
            "project_id": project_id,
            "is_private": True,
            "is_twin_chat": True,
            "source_type": "message"
        })
        
        # User 2 public content (visible to all)
        await message_connector.ingest_message({
            "text": "User 2's shared project update.",
            "user_id": user2_id,
            "project_id": project_id,
            "is_private": False,
            "source_type": "message"
        })
        
        return {
            "user1_id": user1_id,
            "user2_id": user2_id,
            "project_id": project_id
        }

    @pytest.mark.asyncio
    async def test_topic_retrieval_e2e(self, seed_topic_data, async_client, use_test_databases):
        """Test the topic retrieval endpoint to find content related to a specific topic."""
        # Extract the test data
        user_id = seed_topic_data["user_id"]
        project_id = seed_topic_data["project_id"]
        topic_name = seed_topic_data["topic_name"]
        topic_id = seed_topic_data["topic_id"]
        expected_chunk_ids = seed_topic_data["chunk_ids"]
        
        # Print debug information
        print(f"\nQuerying for content related to topic: '{topic_name}' (ID: {topic_id})")
        print(f"Expected chunk IDs: {expected_chunk_ids}")
        
        # Create request parameters
        params = {
            "topic_name": topic_name,
            "user_id": user_id,
            "project_id": project_id,
            "limit": 10
        }
        
        # Build the URL
        url = "/v1/retrieve/topic"
        url += f"?topic_name={params['topic_name']}&user_id={params['user_id']}"
        url += f"&project_id={params['project_id']}&limit={params['limit']}"
        
        print(f"API request URL: {url}")
        
        # Before calling the API, use the Neo4jDAL directly to verify the data exists
        # Use test database connections
        from tests.e2e.test_utils import get_test_neo4j_driver
        
        neo4j_driver = await get_test_neo4j_driver()
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        
        # Direct check using the Neo4jDAL method
        topic_content = await neo4j_dal.get_content_by_topic(
            topic_name=topic_name,
            limit=10,
            user_id=user_id,
            project_id=project_id,
            include_private=False
        )
        
        print(f"Direct Neo4jDAL call found {len(topic_content)} content items for topic")
        for item in topic_content:
            print(f"  Topic-related content: {item.get('chunk_id')}")
        
        # Send a real API request
        response = await async_client.get(
            "/v1/retrieve/topic",
            params=params
        )
        
        # Verify the response
        print(f"API response status: {response.status_code}")
        data = response.json()
        
        # Debug the response data
        print(f"Response data: {data}")
        
        # Check that we got results back
        assert "chunks" in data
        assert data["total"] > 0, f"Expected results but got 0. Make sure the topic retrieval is working properly."
        
        # Verify that the expected chunks are present in the results
        retrieved_chunk_ids = [chunk["chunk_id"] for chunk in data["chunks"]]
        
        print(f"Retrieved chunk IDs: {retrieved_chunk_ids}")
        print(f"Expected chunk IDs: {expected_chunk_ids}")
        
        # At least one of our chunks should be in the results
        found_topic_chunks = any(chunk_id in retrieved_chunk_ids for chunk_id in expected_chunk_ids)
        assert found_topic_chunks, "None of the expected topic-related chunks were found in the results"
        
        # Verify the topic metadata is included
        for chunk in data["chunks"]:
            if "metadata" in chunk and "topic" in chunk["metadata"]:
                topic_data = chunk["metadata"]["topic"]
                assert "name" in topic_data
                assert topic_data["name"] == topic_name

    @pytest.mark.asyncio
    async def test_cross_user_privacy_filtering_e2e(self, seed_multi_user_private_data, async_client, use_test_databases):
        """Test that privacy filtering correctly works across different users."""
        # Extract the test data
        user1_id = seed_multi_user_private_data["user1_id"]
        user2_id = seed_multi_user_private_data["user2_id"]
        project_id = seed_multi_user_private_data["project_id"]
        
        # Wait for indexing
        await asyncio.sleep(2)
        
        # Test 1: User 1 queries private memory - should see own private content, not user 2's
        user1_query = {
            "user_id": user1_id,
            "query_text": "private notes confidential",  # Query matching both users' private content
            "project_id": project_id,
            "limit": 10
        }
        
        user1_response = await async_client.post("/v1/retrieve/private_memory", json=user1_query)
        
        # Verify response
        assert user1_response.status_code == 200
        user1_data = user1_response.json()
        
        # User 1 should only see their own private content, not user 2's
        user1_sees_own_private = False
        user1_sees_user2_private = False
        
        for chunk in user1_data["chunks"]:
            if "private" in chunk["text"].lower() and "user 1" in chunk["text"].lower():
                user1_sees_own_private = True
            if "confidential" in chunk["text"].lower() and "user 2" in chunk["text"].lower():
                user1_sees_user2_private = True
        
        assert user1_sees_own_private, "User 1 should see their own private content"
        assert not user1_sees_user2_private, "User 1 should not see User 2's private content"
        
        # Test 2: User 2 queries private memory - should see own private content, not user 1's
        user2_query = {
            "user_id": user2_id,
            "query_text": "private notes confidential",  # Same query
            "project_id": project_id,
            "limit": 10
        }
        
        user2_response = await async_client.post("/v1/retrieve/private_memory", json=user2_query)
        
        # Verify response
        assert user2_response.status_code == 200
        user2_data = user2_response.json()
        
        # User 2 should only see their own private content, not user 1's
        user2_sees_own_private = False
        user2_sees_user1_private = False
        
        for chunk in user2_data["chunks"]:
            if "confidential" in chunk["text"].lower() and "user 2" in chunk["text"].lower():
                user2_sees_own_private = True
            if "private notes" in chunk["text"].lower() and "user 1" in chunk["text"].lower():
                user2_sees_user1_private = True
        
        assert user2_sees_own_private, "User 2 should see their own private content"
        assert not user2_sees_user1_private, "User 2 should not see User 1's private content"
        
        # Test 3: Both users should see public content in context retrieval
        public_query_params = {
            "query_text": "public shared team discussion update",  # Query matching public content
            "project_id": project_id,
            "limit": 10
        }
        
        public_response = await async_client.get(
            "/v1/retrieve/context",
            params=public_query_params
        )
        
        # Verify response
        assert public_response.status_code == 200
        public_data = public_response.json()
        
        # Should find public content from both users
        found_user1_public = False
        found_user2_public = False
        
        for chunk in public_data["chunks"]:
            if "public" in chunk["text"].lower() and "user 1" in chunk["text"].lower():
                found_user1_public = True
            if "shared" in chunk["text"].lower() and "user 2" in chunk["text"].lower():
                found_user2_public = True
        
        assert found_user1_public, "Public query should return User 1's public content"
        assert found_user2_public, "Public query should return User 2's public content" 