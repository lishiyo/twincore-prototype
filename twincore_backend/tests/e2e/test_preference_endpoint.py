"""End-to-end tests for the preferences endpoint."""

import pytest
import uuid
from datetime import datetime

import pytest_asyncio
import asyncio

@pytest.mark.e2e
@pytest.mark.xdist_group(name="qdrant")  # Group Qdrant-dependent tests
@pytest.mark.xdist_group(name="neo4j")   # Group Neo4j-dependent tests
class TestPreferenceEndpoint:
    """End-to-end tests for the preferences API endpoint."""
    
    @pytest_asyncio.fixture
    async def ensure_collection_exists(self):
        """
        Fixture to ensure the Qdrant collection exists before tests.
        """
        import asyncio
        from core.db_clients import get_async_qdrant_client
        from qdrant_client import models as qdrant_models
        from tests.e2e.test_utils import get_test_async_qdrant_client
        
        print("==== PREFERENCE TEST: CREATING QDRANT COLLECTION BEFORE TEST ====")
        
        qdrant_client = await get_test_async_qdrant_client()
        
        # Always attempt to delete the collection first to ensure a clean state
        try:
            await qdrant_client.delete_collection(collection_name="twin_memory")
            print("PREFERENCE TEST: Deleted existing twin_memory collection")
        except Exception as e:
            # Collection might not exist, ignore the error
            print(f"PREFERENCE TEST: Couldn't delete collection: {e}")
        
        # Wait a moment after deletion
        await asyncio.sleep(1)
        
        # Create the collection
        try:
            print("PREFERENCE TEST: Creating fresh twin_memory collection")
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
            print(f"PREFERENCE TEST: Collections after setup: {collection_names}")
            assert "twin_memory" in collection_names, "Failed to create twin_memory collection"
            
            # Wait to ensure collection is ready
            await asyncio.sleep(2)
            print("PREFERENCE TEST: Collection twin_memory is ready for test")
        except Exception as e:
            print(f"PREFERENCE TEST: Error creating collection: {e}")
            raise
        
        # Yield control back to the test
        yield
        
        # No cleanup after - let the fixture system handle it
    
    @pytest_asyncio.fixture
    async def test_data(self, async_client, use_test_databases, ensure_collection_exists):
        """Set up test data and return it to the test."""
        test_user_id = f"{uuid.uuid4()}"
        test_topic = "dark mode"
        
        # Create test user and preferences data
        # 1. Ingest a message about preferences
        message_data = {
            "text": f"I really prefer {test_topic} for all my apps as it's easier on my eyes.",
            "user_id": test_user_id,
            "source_type": "message",
            "is_twin_chat": False,
            "timestamp": datetime.now().isoformat()
        }
        
        message_response = await async_client.post(
            "/v1/ingest/message",
            json=message_data
        )
        assert message_response.status_code == 202
        
        # 2. Ingest a document mentioning the topic
        document_data = {
            "text": f"When it comes to user interfaces, {test_topic} is often preferred by users who work at night or in low-light environments.",
            "doc_name": "UI Design Preferences",
            "user_id": test_user_id,
            "source_type": "document",
            "project_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "is_private": False,
            # doc_id is optional in the model, let the service generate it
        }
        
        doc_response = await async_client.post(
            "/v1/ingest/document",
            json=document_data
        )
        assert doc_response.status_code == 202  # API returns 202 Accepted for async operations
        
        # Add a small delay to allow async ingestion to complete
        await asyncio.sleep(2) 
        
        # Return test data for use in tests
        return {
            "user_id": test_user_id,
            "topic": test_topic
        }
    
    @pytest.mark.asyncio
    async def test_retrieve_preferences_for_user(self, async_client, test_data):
        """Test retrieving preferences for a specific user on a topic."""
        # Query the preference endpoint
        response = await async_client.get(
            "/v1/retrieve/preferences",
            params={
                "user_id": test_data["user_id"],
                "decision_topic": test_data["topic"],
                "limit": 5,
                "score_threshold": 0.6,
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Basic validation
        assert data["user_id"] == test_data["user_id"]
        assert data["decision_topic"] == test_data["topic"]
        assert data["has_preferences"] is True
        
        # Should have at least one preference statement (our message)
        assert len(data["preference_statements"]) > 0
        
        # Check content
        statements_text = [stmt["text_content"] for stmt in data["preference_statements"]]
        found_preference = False
        for text in statements_text:
            if test_data["topic"] in text.lower():
                found_preference = True
                break
                
        assert found_preference, f"No statements found containing the topic '{test_data['topic']}'"
        
        # Check source indicators
        sources = [stmt.get("source") for stmt in data["preference_statements"]]
        assert "vector" in sources or "graph" in sources
    
    @pytest.mark.asyncio
    async def test_retrieve_preferences_with_no_results(self, async_client, test_data):
        """Test the preference endpoint with a topic the user has no preferences about."""
        # Query with a topic that shouldn't have preferences
        response = await async_client.get(
            "/v1/retrieve/preferences",
            params={
                "user_id": test_data["user_id"],
                "decision_topic": "non_existent_topic_12345",
                "limit": 5,
                "score_threshold": 0.8  # Use a higher threshold for this specific test
            }
        )
        
        # Verify response for no results case
        assert response.status_code == 200
        data = response.json()
        
        # Should indicate no preferences found
        assert data["user_id"] == test_data["user_id"]
        assert data["decision_topic"] == "non_existent_topic_12345"
        assert data["has_preferences"] is False
        assert len(data["preference_statements"]) == 0 