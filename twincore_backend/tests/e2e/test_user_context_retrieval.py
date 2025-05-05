import pytest
import pytest_asyncio
import uuid
import asyncio
from unittest.mock import AsyncMock
import numpy as np
from httpx import AsyncClient
from datetime import datetime

from main import app
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from services.embedding_service import EmbeddingService
from tests.e2e.test_utils import get_test_async_qdrant_client, get_test_neo4j_driver

# Assuming relevant fixtures like async_client, use_test_databases, ensure_collection_exists 
# are defined in twincore_backend/tests/conftest.py or twincore_backend/tests/e2e/conftest.py

@pytest.mark.e2e
@pytest.mark.xdist_group("neo4j")
@pytest.mark.xdist_group("qdrant")
class TestUserContextRetrievalE2E:

    @pytest_asyncio.fixture
    async def seed_multi_user_context_data(self):
        """Seed test data directly using DALs."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        qdrant_client = await get_test_async_qdrant_client()
        neo4j_driver = await get_test_neo4j_driver()
        qdrant_dal = QdrantDAL(client=qdrant_client)
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        
        # Local mock embedding service for seeding Qdrant
        mock_embedding_service = AsyncMock(spec=EmbeddingService)
        async def mock_get_embedding(text):
            seed = sum(ord(c) for c in text) % 10000
            np.random.seed(seed)
            return np.random.randn(1536).astype(np.float32).tolist()
        mock_embedding_service.get_embedding = mock_get_embedding

        test_data = [
            # User 1 Data
            {"text": "User 1 private doc about project Alpha", "user_id": user1_id, "project_id": project_id, "session_id": session_id, "is_private": True, "source_type": "document", "is_twin_chat": False, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
            {"text": "User 1 twin query about project Alpha timeline", "user_id": user1_id, "project_id": project_id, "session_id": session_id, "is_private": False, "source_type": "query", "is_twin_chat": True, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
            {"text": "User 1 public message in session about project Alpha release", "user_id": user1_id, "project_id": project_id, "session_id": session_id, "is_private": False, "source_type": "message", "is_twin_chat": False, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
            # User 2 Data
            {"text": "User 2 public message about project Alpha features", "user_id": user2_id, "project_id": project_id, "session_id": session_id, "is_private": False, "source_type": "message", "is_twin_chat": False, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
            {"text": "User 2 private message about project Alpha concerns", "user_id": user2_id, "project_id": project_id, "session_id": session_id, "is_private": True, "source_type": "message", "is_twin_chat": False, "chunk_id": str(uuid.uuid4()), "timestamp": datetime.now().isoformat()},
        ]

        for item in test_data:
            # Create Neo4j Node
            node_properties = item.copy()
            node_properties["text_content"] = item["text"] # Align property name
            del node_properties["text"] # Remove original key
            
            await neo4j_dal.create_node_if_not_exists(
                label="Content", 
                properties=node_properties, 
                constraints={"chunk_id": item["chunk_id"]}
            )
            
            # Create Qdrant Vector
            vector = await mock_embedding_service.get_embedding(item["text"])
            await qdrant_dal.upsert_vector(
                chunk_id=item["chunk_id"],
                vector=vector,
                text_content=item["text"],
                user_id=item["user_id"],
                project_id=item.get("project_id"),
                session_id=item.get("session_id"),
                source_type=item["source_type"],
                timestamp=item["timestamp"],
                is_twin_interaction=item.get("is_twin_chat", False),
                is_private=item.get("is_private", False)
            )

        # Allow time for indexing
        await asyncio.sleep(2)

        return {
            "user1_id": user1_id,
            "user2_id": user2_id,
            "project_id": project_id,
            "session_id": session_id
        }

    @pytest.mark.asyncio
    async def test_user_context_retrieval(self, seed_multi_user_context_data, async_client, use_test_databases):
        """Test GET /v1/users/{user_id}/context endpoint with various filters."""
        data = seed_multi_user_context_data
        user1_id = data["user1_id"]
        user2_id = data["user2_id"]
        project_id = data["project_id"]
        session_id = data["session_id"]

        # Scenario 1: User 1 queries about project Alpha (default flags: include_private=True, include_twin=True)
        response1 = await async_client.get(
            f"/v1/users/{user1_id}/context",
            params={"query_text": "project Alpha", "project_id": project_id}
        )
        assert response1.status_code == 200
        results1 = response1.json()["chunks"]
        assert len(results1) > 0
        texts1 = [c["text"] for c in results1]
        assert any("User 1 private doc" in t for t in texts1), "User 1 should see own private doc"
        assert any("User 1 twin query" in t for t in texts1), "User 1 should see own twin query"
        assert any("User 1 public message" in t for t in texts1), "User 1 should see own public message"
        assert not any("User 2" in t for t in texts1), "User 1 should NOT see User 2 messages"

        # Scenario 2: User 1 queries, excluding private (include_private=False, include_twin=True)
        response2 = await async_client.get(
            f"/v1/users/{user1_id}/context",
            params={"query_text": "project Alpha", "project_id": project_id, "include_private": False}
        )
        assert response2.status_code == 200
        results2 = response2.json()["chunks"]
        assert len(results2) > 0
        texts2 = [c["text"] for c in results2]
        assert not any("User 1 private doc" in t for t in texts2), "User 1 should NOT see own private doc when include_private=False"
        assert any("User 1 twin query" in t for t in texts2), "User 1 should still see twin query (not private) when include_private=False"
        assert any("User 1 public message" in t for t in texts2), "User 1 should see own public message"
        assert not any("User 2" in t for t in texts2)

        # Scenario 3: User 1 queries, excluding twin interactions (include_private=True, include_twin=False)
        response3 = await async_client.get(
            f"/v1/users/{user1_id}/context",
            params={"query_text": "project Alpha", "project_id": project_id, "include_messages_to_twin": False}
        )
        assert response3.status_code == 200
        results3 = response3.json()["chunks"]
        assert len(results3) > 0
        texts3 = [c["text"] for c in results3]
        assert any("User 1 private doc" in t for t in texts3), "User 1 should see own private doc"
        assert not any("User 1 twin query" in t for t in texts3), "User 1 should NOT see own twin query when include_messages_to_twin=False"
        assert any("User 1 public message" in t for t in texts3), "User 1 should see own public message"
        assert not any("User 2" in t for t in texts3)

        # Scenario 4: User 1 queries, excluding both (include_private=False, include_twin=False)
        response4 = await async_client.get(
            f"/v1/users/{user1_id}/context",
            params={"query_text": "project Alpha", "project_id": project_id, "include_private": False, "include_messages_to_twin": False}
        )
        assert response4.status_code == 200
        results4 = response4.json()["chunks"]
        assert len(results4) > 0
        texts4 = [c["text"] for c in results4]
        assert not any("User 1 private doc" in t for t in texts4)
        assert not any("User 1 twin query" in t for t in texts4)
        assert any("User 1 public message" in t for t in texts4), "User 1 should only see public non-twin messages"
        assert not any("User 2" in t for t in texts4)

        # Scenario 5: User 2 queries about project Alpha (default flags)
        response5 = await async_client.get(
            f"/v1/users/{user2_id}/context",
            params={"query_text": "project Alpha", "project_id": project_id}
        )
        assert response5.status_code == 200
        results5 = response5.json()["chunks"]
        assert len(results5) > 0
        texts5 = [c["text"] for c in results5]
        assert any("User 2 public message" in t for t in texts5), "User 2 should see own public message"
        assert any("User 2 private message" in t for t in texts5), "User 2 should see own private message"
        assert not any("User 1" in t for t in texts5), "User 2 should NOT see User 1 messages" 