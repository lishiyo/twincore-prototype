"""End-to-end tests for the preferences endpoint."""

import pytest
import uuid
from datetime import datetime

import pytest_asyncio
import asyncio
from tests.e2e.test_utils import get_test_neo4j_driver
from dal.neo4j_dal import Neo4jDAL
import asyncio
from core.db_clients import get_async_qdrant_client
from qdrant_client import models as qdrant_models
from tests.e2e.test_utils import get_test_async_qdrant_client
        
@pytest.mark.e2e
@pytest.mark.xdist_group(name="qdrant")  # Group Qdrant-dependent tests
@pytest.mark.xdist_group(name="neo4j")   # Group Neo4j-dependent tests
class TestPreferenceEndpoint:
    """End-to-end tests for the user preferences API endpoint."""
    
    @pytest_asyncio.fixture
    async def ensure_collection_exists(self):
        """
        Fixture to ensure the Qdrant collection exists before tests.
        """
        
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
        
        # 3. Ingest a twin interaction message (marked with is_twin_chat=True)
        twin_message_data = {
            "text": f"I want all my applications to use {test_topic} as the default theme.",
            "user_id": test_user_id,
            "source_type": "message",
            "is_twin_chat": True,  # This marks it as a twin interaction
            "timestamp": datetime.now().isoformat()
        }
        
        twin_msg_response = await async_client.post(
            "/v1/ingest/message",
            json=twin_message_data
        )
        assert twin_msg_response.status_code == 202
        
        # Add a small delay to allow async ingestion to complete
        await asyncio.sleep(2) 
        
        # NEW: Create Topic node and relationships in Neo4j directly
        # This is needed because the Phase 9 Knowledge Extraction service
        # which would normally create topics is not implemented yet
        
        
        # Get Neo4j driver and DAL
        neo4j_driver = await get_test_neo4j_driver()
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        
        # 1. Create the Topic node
        topic_node = await neo4j_dal.create_node_if_not_exists(
            label="Topic",
            properties={"name": test_topic, "topic_id": str(uuid.uuid4())},
            constraints={"name": test_topic}
        )
        
        # 2. Now we need to find all Content nodes from this user to connect them to the Topic
        try:
            async with neo4j_driver.session() as session:
                # Find all the user's content nodes
                # We're deliberately using source_type=message for simplicity
                # In a real system, we would use proper chunk IDs
                query = """
                MATCH (u:User {user_id: $user_id})-[:CREATED]->(c:Content)
                RETURN c.chunk_id as chunk_id, c.text_content as text_content
                """
                
                result = await session.run(query, {"user_id": test_user_id})
                content_nodes = [{"chunk_id": record["chunk_id"], "text_content": record["text_content"]} 
                               async for record in result]
                
                # Create MENTIONS relationships between content and topic
                for content in content_nodes:
                    # Skip if no chunk_id
                    if not content.get("chunk_id"):
                        continue
                        
                    # Connect this content to the topic
                    await neo4j_dal.create_relationship_if_not_exists(
                        start_label="Content",
                        start_constraints={"chunk_id": content["chunk_id"]},
                        end_label="Topic",
                        end_constraints={"name": test_topic},
                        relationship_type="MENTIONS",
                        properties={"relevance": 0.9}  # Mock relevance score
                    )
                    
                    # For the first content (assuming it's a preference statement),
                    # also create a STATES_PREFERENCE relationship
                    if content == content_nodes[0]:
                        await neo4j_dal.create_relationship_if_not_exists(
                            start_label="Content",
                            start_constraints={"chunk_id": content["chunk_id"]},
                            end_label="Topic",
                            end_constraints={"name": test_topic},
                            relationship_type="STATES_PREFERENCE",
                            properties={"confidence": 0.95}  # Mock confidence score
                        )
                        
                print(f"Created Topic node and relationships for {len(content_nodes)} content nodes")
                
        except Exception as e:
            print(f"Error creating Topic relationships: {e}")
            
        # Add more delay to ensure Neo4j operations complete
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
            f"/v1/users/{test_data['user_id']}/preferences",
            params={
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
            f"/v1/users/{test_data['user_id']}/preferences",
            params={
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
        
    @pytest.mark.asyncio
    async def test_retrieve_preferences_with_include_messages_to_twin(self, async_client, test_data):
        """Test the preference endpoint with include_messages_to_twin parameter set to true."""
        # Query with include_messages_to_twin=true (explicitly)
        response_with_twin = await async_client.get(
            f"/v1/users/{test_data['user_id']}/preferences",
            params={
                "decision_topic": test_data["topic"],
                "limit": 5,
                "include_messages_to_twin": "true",  # Explicitly include twin interactions
                "score_threshold": 0.6
            }
        )
        
        # Verify response
        assert response_with_twin.status_code == 200
        data_with_twin = response_with_twin.json()
        
        # Basic validation
        assert data_with_twin["user_id"] == test_data["user_id"]
        assert data_with_twin["decision_topic"] == test_data["topic"]
        assert data_with_twin["has_preferences"] is True
        
        # Should include the twin interaction message
        twin_interaction_found = False
        for stmt in data_with_twin["preference_statements"]:
            # Check if we can find our twin interaction message
            if "want all my applications to use" in stmt.get("text_content", "").lower():
                twin_interaction_found = True
                break
                
        assert twin_interaction_found, "Twin interaction message not found when include_messages_to_twin=true"
        
    @pytest.mark.asyncio
    async def test_retrieve_preferences_without_include_messages_to_twin(self, async_client, test_data):
        """Test the preference endpoint with include_messages_to_twin parameter set to false."""
        # Query with include_messages_to_twin=false (explicitly)
        response_without_twin = await async_client.get(
            f"/v1/users/{test_data['user_id']}/preferences",
            params={
                "decision_topic": test_data["topic"],
                "limit": 5,
                "include_messages_to_twin": "false",  # Explicitly exclude twin interactions
                "score_threshold": 0.6
            }
        )
        
        # Verify response
        assert response_without_twin.status_code == 200
        data_without_twin = response_without_twin.json()
        
        # Basic validation
        assert data_without_twin["user_id"] == test_data["user_id"]
        assert data_without_twin["decision_topic"] == test_data["topic"]
        
        # Should not include the twin interaction message
        for stmt in data_without_twin["preference_statements"]:
            # Verify no statement contains our twin interaction text
            assert "want all my applications to use" not in stmt.get("text_content", "").lower(), \
                "Twin interaction message found when include_messages_to_twin=false"
    
    @pytest.mark.asyncio
    async def test_retrieve_preferences_default_include_messages_to_twin(self, async_client, test_data):
        """Test the preference endpoint with default include_messages_to_twin parameter (should be true)."""
        # Query without specifying include_messages_to_twin
        default_response = await async_client.get(
            f"/v1/users/{test_data['user_id']}/preferences",
            params={
                "decision_topic": test_data["topic"],
                "limit": 5,
                "score_threshold": 0.6
                # No include_messages_to_twin parameter - should use default (true)
            }
        )
        
        # Query with include_messages_to_twin=true for comparison
        explicit_response = await async_client.get(
            f"/v1/users/{test_data['user_id']}/preferences",
            params={
                "decision_topic": test_data["topic"],
                "limit": 5,
                "score_threshold": 0.6,
                "include_messages_to_twin": "true"
            }
        )
        
        # Verify responses
        assert default_response.status_code == 200
        assert explicit_response.status_code == 200
        
        default_data = default_response.json()
        explicit_data = explicit_response.json()
        
        # The default behavior should match the explicit include_messages_to_twin=true behavior
        # We check the statement count is the same (not exact content equality because timestamps might differ)
        assert len(default_data["preference_statements"]) == len(explicit_data["preference_statements"])
        
        # Check if twin interaction appears in both results
        default_has_twin = False
        explicit_has_twin = False
        
        for stmt in default_data["preference_statements"]:
            if "want all my applications to use" in stmt.get("text_content", "").lower():
                default_has_twin = True
                break
                
        for stmt in explicit_data["preference_statements"]:
            if "want all my applications to use" in stmt.get("text_content", "").lower():
                explicit_has_twin = True
                break
        
        assert default_has_twin == explicit_has_twin, \
            "Default behavior does not match explicit include_messages_to_twin=true" 