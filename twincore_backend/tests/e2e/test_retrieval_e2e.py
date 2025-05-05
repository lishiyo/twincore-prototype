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
import asyncio
import logging
from datetime import datetime
from urllib.parse import urlencode

from services.ingestion_service import IngestionService
from services.embedding_service import EmbeddingService
from services.retrieval_service import RetrievalService
from ingestion.connectors.message_connector import MessageConnector
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from main import app

# Import shared fixtures
from .fixtures.retrieval_fixtures import (
    seed_test_data,
    seed_private_test_data,
    seed_related_content_data,
    seed_topic_data,
    seed_multi_user_private_data,
    seed_twin_interaction_data,
    seed_group_context_data
)

logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.xdist_group("neo4j")  # Group Neo4j tests
@pytest.mark.xdist_group("qdrant") # Group Qdrant tests
class TestRetrievalE2E:
    """End-to-end tests for retrieval functionality."""

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
    async def test_context_retrieval_include_messages_to_twin(self, seed_twin_interaction_data, async_client, use_test_databases):
        """Test context retrieval with the include_messages_to_twin parameter."""
        # Extract the test data
        user_id = seed_twin_interaction_data["user_id"]
        project_id = seed_twin_interaction_data["project_id"]
        session_id = seed_twin_interaction_data["session_id"]
        
        # 1. Test with include_messages_to_twin=true - should include twin interactions
        with_twin_params = {
            "query_text": "project timeline",  # Query relevant to our seeded test data
            "project_id": project_id,
            "session_id": session_id,
            "limit": 10,
            "include_messages_to_twin": "true",  # Explicitly include twin interactions
            "include_private": "true"            # Explicitly include private content
        }
        
        # Send API request
        with_twin_response = await async_client.get(
            "/v1/retrieve/context",
            params=with_twin_params
        )
        
        # Verify the response
        assert with_twin_response.status_code == 200
        with_twin_data = with_twin_response.json()
        
        # Check that we got results back
        assert "chunks" in with_twin_data
        assert with_twin_data["total"] > 0
        
        # Check if we found twin interaction message
        twin_interaction_found = False
        regular_message_found = False
        
        for chunk in with_twin_data["chunks"]:
            if "Twin interaction:" in chunk["text"]:
                twin_interaction_found = True
            if "Regular message:" in chunk["text"]:
                regular_message_found = True
        
        assert twin_interaction_found, "Twin interaction message not found when include_messages_to_twin=true"
        assert regular_message_found, "Regular message not found when include_messages_to_twin=true"
        
        # 2. Test with include_messages_to_twin=false - should exclude twin interactions
        without_twin_params = {
            "query_text": "project timeline",
            "project_id": project_id,
            "session_id": session_id,
            "limit": 10,
            "include_messages_to_twin": "false",  # Explicitly exclude twin interactions
            "include_private": "true"             # Explicitly include private content  
        }
        
        # Send API request
        without_twin_response = await async_client.get(
            "/v1/retrieve/context",
            params=without_twin_params
        )
        
        # Verify the response
        assert without_twin_response.status_code == 200
        without_twin_data = without_twin_response.json()
        
        # Check that we got results back
        assert "chunks" in without_twin_data
        assert without_twin_data["total"] > 0
        
        # Should only find regular message, not twin interaction
        for chunk in without_twin_data["chunks"]:
            assert "Twin interaction:" not in chunk["text"], "Twin interaction found when include_messages_to_twin=false"
            if "Regular message:" in chunk["text"]:
                regular_message_found = True
        
        assert regular_message_found, "Regular message not found when include_messages_to_twin=false"
        
        # 3. Test default behavior (include_messages_to_twin should default to false for context endpoint)
        default_params = {
            "query_text": "project timeline",
            "project_id": project_id,
            "session_id": session_id,
            "limit": 10,
            "include_private": "true"              # Explicitly include private content
            # No include_messages_to_twin parameter - should default to false
        }
        
        # Send API request
        default_response = await async_client.get(
            "/v1/retrieve/context",
            params=default_params
        )
        
        # Verify the response
        assert default_response.status_code == 200
        default_data = default_response.json()
        
        # Default behavior should match include_messages_to_twin=false
        assert default_data["total"] == without_twin_data["total"]
        
        # Should not find twin interaction
        for chunk in default_data["chunks"]:
            assert "Twin interaction:" not in chunk["text"], "Twin interaction found in default behavior"

    @pytest.mark.asyncio
    async def test_group_context_retrieval_e2e(
        self, seed_group_context_data, async_client, use_test_databases
    ):
        """Test the complete group context retrieval flow using the API endpoint."""
        # Extract test data IDs
        user_a_id = seed_group_context_data["user_a_id"]
        user_b_id = seed_group_context_data["user_b_id"]
        session_id = seed_group_context_data["session_id"]
        project_id = seed_group_context_data["project_id"]

        # 1. Test with session scope, including private
        session_params = {
            "query_text": "group project",
            "session_id": session_id,
            "limit_per_user": 5,
            "include_private": "true",
            "include_messages_to_twin": "true"
        }

        session_response = await async_client.get("/v1/retrieve/group", params=session_params)

        # Verify response
        assert session_response.status_code == 200
        session_data = session_response.json()
        assert "group_results" in session_data
        assert len(session_data["group_results"]) == 2 # Both users participated

        # Check results for User A (should include public and private)
        user_a_results = next((r for r in session_data["group_results"] if r["user_id"] == user_a_id), None)
        assert user_a_results is not None
        assert len(user_a_results["results"]) >= 2 # Public + Private message
        assert any("features" in res["text"] for res in user_a_results["results"])
        assert any("private thought" in res["text"] for res in user_a_results["results"])

        # Check results for User B (should include public only)
        user_b_results = next((r for r in session_data["group_results"] if r["user_id"] == user_b_id), None)
        assert user_b_results is not None
        assert len(user_b_results["results"]) >= 1
        assert any("timelines" in res["text"] for res in user_b_results["results"])

        # 2. Test with project scope, excluding private
        project_params = {
            "query_text": "group project",
            "project_id": project_id,
            "limit_per_user": 5,
            "include_private": "false", # Exclude private content
            "include_messages_to_twin": "true"
        }

        project_response = await async_client.get("/v1/retrieve/group", params=project_params)

        # Verify response
        assert project_response.status_code == 200
        project_data = project_response.json()
        assert "group_results" in project_data
        # Note: Depending on how Neo4j get_project_participants works, might still be 2 users
        assert len(project_data["group_results"]) >= 1 # At least one user should have public results

        # Check results for User A (should *not* include private)
        user_a_project_results = next((r for r in project_data["group_results"] if r["user_id"] == user_a_id), None)
        if user_a_project_results:
             assert len(user_a_project_results["results"]) >= 1
             assert any("features" in res["text"] for res in user_a_project_results["results"])
             assert not any("private thought" in res["text"] for res in user_a_project_results["results"])

        # User B results should be the same (only public)
        user_b_project_results = next((r for r in project_data["group_results"] if r["user_id"] == user_b_id), None)
        if user_b_project_results:
            assert len(user_b_project_results["results"]) >= 1
            assert any("timelines" in res["text"] for res in user_b_project_results["results"]) 