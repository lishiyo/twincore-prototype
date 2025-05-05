import pytest
import pytest_asyncio
from httpx import AsyncClient
import asyncio
import logging
import numpy as np
from fastapi.testclient import TestClient

from core.mock_data import USERS, USER_ALICE_ID, USER_BOB_ID, USER_CHARLIE_ID, PROJECT_BOOK_GEN_ID
from core.config import settings
from main import app
from .test_utils import get_test_neo4j_driver, get_test_qdrant_client
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

@pytest.mark.xdist_group("qdrant")
@pytest.mark.xdist_group("neo4j")
class TestSeedDataE2E:
    """Test class for seed data endpoint E2E test."""
    
    @pytest.mark.asyncio
    async def test_seed_data_e2e(self, initialized_app):
        """
        End-to-end test that calls the seed_data endpoint and verifies data integrity
        in both Qdrant and Neo4j by directly querying the databases.
        """
        # Create a TestClient with the initialized app for synchronous calls
        client = TestClient(initialized_app)
        
        # Call the seed_data endpoint using the test client
        logger.info("Calling seed_data endpoint...")
        response = client.post("/v1/admin/api/seed_data")
        response_json = response.json()
        print(f"\n\nSEED DATA RESPONSE: {response.status_code}")
        print(f"Response content: {response_json}\n\n")
        logger.info(f"Seed data response: {response.status_code} - {response_json}")
        assert response.status_code == 202
        
        # Allow more time for async operations to complete
        logger.info("Waiting for async operations to complete...")
        await asyncio.sleep(3)
        
        # Verify Qdrant data directly using our test utility
        qdrant_client = get_test_qdrant_client()
        collection_name = settings.qdrant_collection_name
        
        # 1. Verify the collection exists and get point count
        logger.info(f"Checking Qdrant collection: {collection_name}")
        collection_info = qdrant_client.get_collection(collection_name)
        logger.info(f"Collection info: {collection_info}")
        assert collection_info is not None
        
        # Check if data was seeded - vectors_count should be > 0
        # If this fails, there may be an issue with how data is being ingested in the test environment
        vectors_count = collection_info.vectors_count
        logger.info(f"Vectors count: {vectors_count}")
        assert vectors_count > 0, "No vectors were added to the Qdrant collection"
        
        # Create a dummy query vector for search operations (Qdrant requires a query vector)
        dummy_query_vector = np.random.randn(settings.embedding_dimension).astype(np.float32).tolist()
        
        # 2. Query for specific data to verify integrity
        # Example: Check Alice's private document was properly ingested
        logger.info("Searching for Alice's private documents...")
        alice_private_docs = qdrant_client.search(
            collection_name=collection_name,
            query_vector=dummy_query_vector,  # Add required query vector
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=USER_ALICE_ID)
                    ),
                    FieldCondition(
                        key="is_private",
                        match=MatchValue(value=True)
                    )
                ]
            ),
            limit=5
        )
        logger.info(f"Found {len(alice_private_docs)} Alice private docs")
        assert len(alice_private_docs) > 0
        
        # Example: Check book project documents were properly ingested
        logger.info("Searching for book project documents...")
        book_project_docs = qdrant_client.search(
            collection_name=collection_name,
            query_vector=dummy_query_vector,  # Add required query vector
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="project_id",
                        match=MatchValue(value=PROJECT_BOOK_GEN_ID)
                    )
                ]
            ),
            limit=5
        )
        logger.info(f"Found {len(book_project_docs)} book project docs")
        assert len(book_project_docs) > 0
        
        # Verify Neo4j data directly using our test utility
        logger.info("Connecting to Neo4j test database...")
        neo4j_driver = await get_test_neo4j_driver()
        
        async with neo4j_driver.session() as session:
            # 1. Check User nodes were created
            logger.info("Checking Neo4j User nodes...")
            user_result = await session.run("MATCH (u:User) RETURN count(u) as count")
            user_count = await user_result.single()
            logger.info(f"User count: {user_count['count']}")
            assert user_count["count"] == len(USERS)
            
            # 2. Check Project nodes were created
            logger.info("Checking Neo4j Project nodes...")
            project_result = await session.run("MATCH (p:Project) RETURN count(p) as count")
            project_count = await project_result.single()
            logger.info(f"Project count: {project_count['count']}")
            assert project_count["count"] >= 1  # At least the book project
            
            # 3. Check Document nodes were created
            logger.info("Checking Neo4j Document nodes...")
            doc_result = await session.run("MATCH (d:Document) RETURN count(d) as count")
            doc_count = await doc_result.single()
            logger.info(f"Document count: {doc_count['count']}")
            assert doc_count["count"] > 0
            
            # 4. Check Message nodes were created
            logger.info("Checking Neo4j Message nodes...")
            msg_result = await session.run("MATCH (m:Message) RETURN count(m) as count")
            msg_count = await msg_result.single()
            logger.info(f"Message count: {msg_count['count']}")
            assert msg_count["count"] > 0
            
            # 5. Check relationships exist
            # Example: Users PARTICIPATED_IN Sessions
            logger.info("Checking Neo4j PARTICIPATED_IN relationships...")
            participant_result = await session.run(
                "MATCH (u:User)-[:PARTICIPATED_IN]->(s:Session) RETURN count(DISTINCT u) as count"
            )
            participant_count = await participant_result.single()
            logger.info(f"Participant count: {participant_count['count']}")
            assert participant_count["count"] > 0
            
            # Example: Users AUTHORED Messages
            logger.info("Checking Neo4j AUTHORED relationships...")
            author_result = await session.run(
                "MATCH (u:User)-[:AUTHORED]->(m:Message) RETURN count(DISTINCT u) as count"
            )
            author_count = await author_result.single()
            logger.info(f"Author count: {author_count['count']}")
            assert author_count["count"] > 0
            
            # 6. Check specific user data for Alice
            logger.info("Checking Alice's data in Neo4j...")
            alice_result = await session.run(
                "MATCH (u:User {user_id: $userId}) RETURN u.user_id as userId, u.name as name",
                userId=USER_ALICE_ID
            )
            alice_data = await alice_result.single()
            logger.info(f"Alice's data: {alice_data}")
            
            # Verify Alice's user ID and name
            assert alice_data["userId"] == USER_ALICE_ID
            assert alice_data["name"] is not None, "User name should not be None"
            assert alice_data["name"] == "Alice", "User name should be 'Alice'"
        
        # Close connections
        await neo4j_driver.close()
        logger.info("End-to-end test completed successfully!") 