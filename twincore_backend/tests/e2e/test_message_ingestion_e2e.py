"""End-to-end tests for message ingestion."""

import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient

from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from main import app, get_message_ingestion_service
from api.routers import ingest_router
from qdrant_client import models


@pytest.mark.e2e
class TestMessageIngestionE2E:
    """End-to-end tests for message ingestion functionality."""

    @pytest.fixture(autouse=True)
    def setup_dependencies(self):
        """Setup dependencies for the test and cleanup afterward."""
        # For E2E tests, we want to use the real services, not mocks
        # Make sure the default dependency setup from main.py is used
        app.dependency_overrides[ingest_router.get_message_ingestion_service] = get_message_ingestion_service
        
        yield
        
        # Clean up after the test
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_message_ingestion_end_to_end(self, async_client: AsyncClient):
        """Test the full message ingestion flow from API to databases."""
        # Generate unique IDs for this test (pure UUIDs)
        user_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Create test message data
        message_text = "This is a test message for end-to-end testing."
        message_data = {
            "text": message_text,
            "source_type": "message",
            "user_id": user_id,
            "message_id": message_id,
            "project_id": project_id,
            "session_id": session_id,
            "is_twin_chat": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # 1. Call the API to ingest the message
        response = await async_client.post("/v1/api/ingest/message", json=message_data)
        
        # Verify the API response
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Message ingested successfully"}
        
        # 2. Verify the data was stored in Qdrant
        qdrant_client = get_async_qdrant_client()
        scroll_result = await qdrant_client.scroll(
            collection_name="twin_memory",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id", 
                        match=models.MatchValue(value=user_id)
                    ),
                    models.FieldCondition(
                        key="message_id", 
                        match=models.MatchValue(value=message_id)
                    )
                ]
            ),
            limit=1
        )
        
        # Verify Qdrant contains our message
        points = scroll_result[0]  # The first element contains the points
        assert len(points) > 0, "Message not found in Qdrant"
        qdrant_record = points[0].payload
        assert qdrant_record["text_content"] == message_text
        assert qdrant_record["source_type"] == "message"
        assert qdrant_record["user_id"] == user_id
        assert qdrant_record["message_id"] == message_id
        assert qdrant_record["project_id"] == project_id
        assert qdrant_record["session_id"] == session_id
        
        # Verify the point ID - could be string or int now that we accept both
        point_id = points[0].id
        assert point_id is not None
        
        # 3. Verify the graph was updated in Neo4j
        neo4j_driver = await get_neo4j_driver()
        async with neo4j_driver.session() as session:
            # Check for User node
            user_result = await session.run(
                "MATCH (u:User {user_id: $user_id}) RETURN u",
                user_id=user_id
            )
            user_records = await user_result.values()
            assert len(user_records) > 0, "User node not found in Neo4j"
            
            # Check for Message node
            message_result = await session.run(
                "MATCH (m:Message {message_id: $message_id}) RETURN m",
                message_id=message_id
            )
            message_records = await message_result.values()
            assert len(message_records) > 0, "Message node not found in Neo4j"
            
            # Check for relationship between User and Message
            relationship_result = await session.run(
                """
                MATCH (u:User {user_id: $user_id})-[r:AUTHORED]->(m:Message {message_id: $message_id})
                RETURN r
                """,
                user_id=user_id,
                message_id=message_id
            )
            relationship_records = await relationship_result.values()
            assert len(relationship_records) > 0, "User->Message relationship not found in Neo4j"
            
            # Check for Chunk node - note that chunk_id is stored as a string in Neo4j
            # We don't know the exact chunk_id, so we find it via the relation to the Message
            chunk_result = await session.run(
                """
                MATCH (c:Chunk)-[:PART_OF]->(m:Message {message_id: $message_id})
                RETURN c
                """,
                message_id=message_id
            )
            chunk_records = await chunk_result.values()
            assert len(chunk_records) > 0, "Chunk node not found in Neo4j"
            
            # Check for Project and Session nodes if provided
            if project_id:
                project_result = await session.run(
                    "MATCH (p:Project {project_id: $project_id}) RETURN p",
                    project_id=project_id
                )
                project_records = await project_result.values()
                assert len(project_records) > 0, "Project node not found in Neo4j"
            
            if session_id:
                session_result = await session.run(
                    "MATCH (s:Session {session_id: $session_id}) RETURN s",
                    session_id=session_id
                )
                session_records = await session_result.values()
                assert len(session_records) > 0, "Session node not found in Neo4j" 