"""End-to-end tests for document ingestion."""

import pytest
import uuid
from datetime import datetime
from httpx import AsyncClient
import logging

from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from main import app, get_document_connector
from api.routers import ingest_router
from qdrant_client import models

logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.xdist_group("neo4j")  # Group Neo4j tests so they don't run concurrently
class TestDocumentIngestionE2E:
    """End-to-end tests for document ingestion functionality."""

    @pytest.fixture(autouse=True)
    def setup_dependencies(self):
        """Setup dependencies for the test and cleanup afterward."""
        # For E2E tests, we want to use the real services, not mocks
        # Make sure the default dependency setup from main.py is used
        app.dependency_overrides[ingest_router.get_document_connector] = get_document_connector
        
        yield
        
        # Clean up after the test
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_document_ingestion_end_to_end(self, async_client: AsyncClient):
        """Test the full document ingestion flow from API to databases."""
        # Generate unique IDs for this test
        user_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Create test document data
        doc_name = "End-to-End Test Document.pdf"
        document_text = """
        This is a test document for end-to-end testing of document ingestion.
        
        The document should be split into multiple chunks based on paragraphs.
        
        Each chunk should be stored in Qdrant and linked properly in Neo4j.
        
        The document should be available for retrieval with the proper metadata.
        
        This test verifies the complete ingestion pipeline works correctly.
        """
        
        document_data = {
            "text": document_text,
            "source_type": "document",
            "doc_name": doc_name,
            "user_id": user_id,
            "doc_id": doc_id,
            "project_id": project_id,
            "session_id": session_id,
            "is_private": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # 1. Call the API to ingest the document
        response = await async_client.post("/v1/ingest/document", json=document_data)
        
        # Verify the API response
        assert response.status_code == 202
        assert response.json() == {"status": "accepted", "message": "Document received and queued for ingestion."}
        
        # 2. Verify document chunks were stored in Qdrant
        qdrant_client = get_async_qdrant_client()
        scroll_result = await qdrant_client.scroll(
            collection_name="twin_memory",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id", 
                        match=models.MatchValue(value=doc_id)
                    )
                ]
            ),
            limit=10
        )
        
        # Verify Qdrant contains document chunks
        points = scroll_result[0]  # The first element contains the points
        assert len(points) > 0, "No document chunks found in Qdrant"
        
        # Verify at least one chunk has the correct properties
        qdrant_record = points[0].payload
        assert qdrant_record["source_type"] == "document_chunk"
        assert qdrant_record["doc_id"] == doc_id
        # Check for original_document which contains the document name
        assert qdrant_record["original_document"] == doc_name
        assert qdrant_record["user_id"] == user_id
        assert qdrant_record["project_id"] == project_id
        assert qdrant_record["session_id"] == session_id
        assert qdrant_record["is_private"] == True
        
        # Verify the chunk metadata is present
        assert "original_document" in qdrant_record
        assert "chunk_index" in qdrant_record
        assert "total_chunks" in qdrant_record
        
        # 3. Verify the document structure was created in Neo4j
        neo4j_driver = await get_neo4j_driver()
        try:
            async with neo4j_driver.session() as session:
                # Check for Document node
                doc_result = await session.run(
                    "MATCH (d:Document {document_id: $doc_id}) RETURN d",
                    doc_id=doc_id
                )
                doc_records = await doc_result.values()
                assert len(doc_records) > 0, "Document node not found in Neo4j"
                
                # Check for User node
                user_result = await session.run(
                    "MATCH (u:User {user_id: $user_id}) RETURN u",
                    user_id=user_id
                )
                user_records = await user_result.values()
                assert len(user_records) > 0, "User node not found in Neo4j"
                
                # Check for User->Document relationship
                upload_result = await session.run(
                    """
                    MATCH (u:User {user_id: $user_id})-[r:UPLOADED]->(d:Document {document_id: $doc_id})
                    RETURN r
                    """,
                    user_id=user_id,
                    doc_id=doc_id
                )
                upload_records = await upload_result.values()
                assert len(upload_records) > 0, "User->Document relationship not found in Neo4j"
                
                # Check for Chunk nodes - we don't know exact IDs, so find via Document relation
                chunk_result = await session.run(
                    """
                    MATCH (c:Chunk)-[:PART_OF]->(d:Document {document_id: $doc_id})
                    RETURN count(c) AS chunk_count
                    """,
                    doc_id=doc_id
                )
                chunk_records = await chunk_result.values()
                chunk_count = chunk_records[0][0]  # Extract count value
                assert chunk_count > 0, "No chunk nodes found for the document in Neo4j"
                
                # Verify document is private
                privacy_result = await session.run(
                    """
                    MATCH (d:Document {document_id: $doc_id})
                    RETURN d.is_private AS is_private
                    """,
                    doc_id=doc_id
                )
                privacy_records = await privacy_result.values()
                assert privacy_records[0][0] == True, "Document should be marked as private"
                
                # Verify chunks inherit document privacy setting
                chunks_privacy_result = await session.run(
                    """
                    MATCH (c:Chunk)-[:PART_OF]->(d:Document {document_id: $doc_id})
                    RETURN c.is_private AS is_private
                    """,
                    doc_id=doc_id
                )
                chunks_privacy_records = await chunks_privacy_result.fetch(10)  # Get up to 10 records
                
                # Verify all retrieved chunks are private
                for record in chunks_privacy_records:
                    assert record["is_private"] == True, "Document chunk should inherit private flag" 
        finally:
            # Always close the driver when done
            await neo4j_driver.close()
            logger.info("Neo4j driver closed in document test") 