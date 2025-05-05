"""End-to-end tests for document ingestion."""

import pytest
import uuid
import asyncio
from datetime import datetime
from httpx import AsyncClient
import logging
from qdrant_client import models as qdrant_models

from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from main import app, get_document_connector
from qdrant_client import models
from fastapi import status

logger = logging.getLogger(__name__)

@pytest.mark.e2e
@pytest.mark.xdist_group("neo4j")  # Group Neo4j tests so they don't run concurrently
@pytest.mark.xdist_group("qdrant")  # Group Qdrant tests so they don't run concurrently
class TestDocumentIngestionE2E:
    """End-to-end tests for document ingestion functionality."""

    @pytest.fixture(autouse=True)
    async def ensure_collection_exists(self):
        """
        Fixture to ensure the Qdrant collection exists before EVERY test.
        
        This runs before each test method in the class due to autouse=True.
        Some tests in the test suite delete the collection as part of their cleanup.
        This fixture ensures the collection is recreated before our tests run.
        """
        # Use ERROR level for better visibility during debugging
        logger.error("==== DOCUMENT TEST: CREATING QDRANT COLLECTION BEFORE TEST ====")
        print("==== DOCUMENT TEST: CREATING QDRANT COLLECTION BEFORE TEST ====")
        
        qdrant_client = get_async_qdrant_client()
        
        # Always attempt to delete the collection first to ensure a clean state
        try:
            await qdrant_client.delete_collection(collection_name="twin_memory")
            logger.error("Deleted existing twin_memory collection")
            print("DOCUMENT TEST: Deleted existing twin_memory collection")
        except Exception as e:
            # Collection might not exist, ignore the error
            logger.error(f"Note: Couldn't delete collection (might not exist): {e}")
            print(f"DOCUMENT TEST: Couldn't delete collection: {e}")
        
        # Wait a moment after deletion
        await asyncio.sleep(1)
        
        # Create the collection
        try:
            logger.error("Creating fresh twin_memory collection")
            print("DOCUMENT TEST: Creating fresh twin_memory collection")
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
            print(f"DOCUMENT TEST: Collections after setup: {collection_names}")
            assert "twin_memory" in collection_names, "Failed to create twin_memory collection"
            
            # Wait to ensure collection is ready
            await asyncio.sleep(2)
            logger.error("Collection twin_memory is ready for test")
            print("DOCUMENT TEST: Collection twin_memory is ready for test")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            print(f"DOCUMENT TEST: Error creating collection: {e}")
            raise
        
        # Yield control back to the test
        yield
        
        # No cleanup after - let the test complete normally
    
    @pytest.mark.asyncio
    async def test_document_ingestion_end_to_end(self, async_client: AsyncClient):
        """Test the full document ingestion flow using direct connector access instead of API."""
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
        
        # Log test parameters
        logger.info(f"Running document ingestion test with doc_id: {doc_id}")
        
        # BYPASS THE API: Use the document connector directly
        document_connector = await get_document_connector()
        await document_connector.ingest_document(document_data)
        logger.info("Document ingested using connector directly")
        
        # Add a small delay to allow processing to complete
        await asyncio.sleep(1)
        
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
            
    @pytest.mark.asyncio 
    async def test_document_api_with_existing_collection(self, async_client: AsyncClient):
        """Test the document API endpoint after ensuring the collection exists."""
        # Generate unique IDs for this test
        user_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Create test document data
        doc_name = "API Test Document.pdf"
        document_text = "This is a short test document for the API endpoint."
        
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
        
        # Log test parameters
        logger.info(f"Running API document ingestion test with doc_id: {doc_id}")
        
        # Now call the API
        response = await async_client.post("/v1/ingest/document", json=document_data)
        
        # Log response details
        logger.info(f"Document ingestion response status: {response.status_code}")
        if response.status_code != 202:
            logger.error(f"Error response body: {response.text}")
        
        # Now this should work as the collection exists
        assert response.status_code == 202
        assert response.json() == {"status": "accepted", "message": "Document received and queued for ingestion."} 

    @pytest.mark.asyncio
    async def test_chunk_ingestion_end_to_end(self, async_client: AsyncClient):
        """Test the full chunk ingestion flow via the API."""
        # Generate unique IDs for this test
        user_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4()) # Parent document ID
        session_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        
        # Chunk data to ingest
        chunks_to_ingest = [
            {
                "user_id": user_id,
                "session_id": session_id,
                "doc_id": doc_id,
                "text": "This is the first transcript chunk.",
                "timestamp": datetime.now().isoformat(),
                "project_id": project_id,
                "chunk_id": str(uuid.uuid4()),
                "metadata": {"turn": 1}
            },
            {
                "user_id": str(uuid.uuid4()), # Different user for second chunk
                "session_id": session_id,
                "doc_id": doc_id,
                "text": "This is the second utterance.",
                "timestamp": datetime.now().isoformat(),
                "project_id": project_id,
                "chunk_id": str(uuid.uuid4()),
                "metadata": {"turn": 2}
            }
        ]

        logger.info(f"Running chunk ingestion test for document {doc_id}")

        # Ingest each chunk via the API
        for chunk_data in chunks_to_ingest:
            response = await async_client.post("/v1/ingest/chunk", json=chunk_data)
            assert response.status_code == status.HTTP_202_ACCEPTED, f"Failed to ingest chunk: {response.text}"
        
        logger.info(f"Ingested {len(chunks_to_ingest)} chunks via API")
        
        # Add a delay to allow asynchronous processing
        await asyncio.sleep(2)

        # Verify chunks in Qdrant
        qdrant_client = get_async_qdrant_client()
        scroll_result = await qdrant_client.scroll(
            collection_name="twin_memory",
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id)),
                    models.FieldCondition(key="source_type", match=models.MatchValue(value="transcript_snippet"))
                ]
            ),
            limit=10
        )
        points = scroll_result[0]
        assert len(points) == len(chunks_to_ingest), "Incorrect number of chunks found in Qdrant"

        # Verify payloads match ingested data
        qdrant_chunk_ids = {p.id for p in points}
        original_chunk_ids = {c["chunk_id"] for c in chunks_to_ingest}
        assert qdrant_chunk_ids == original_chunk_ids

        for point in points:
            payload = point.payload
            original_chunk = next(c for c in chunks_to_ingest if c["chunk_id"] == point.id)
            assert payload["text_content"] == original_chunk["text"]
            assert payload["user_id"] == original_chunk["user_id"]
            assert payload["session_id"] == original_chunk["session_id"]
            assert payload["doc_id"] == doc_id
            assert payload["source_type"] == "transcript_snippet"
            assert payload["turn"] == original_chunk["metadata"]["turn"]
        
        # Verify parent document and relationships in Neo4j
        neo4j_driver = await get_neo4j_driver()
        try:
            async with neo4j_driver.session() as session:
                # Check for Document node
                doc_result = await session.run(
                    "MATCH (d:Document {document_id: $doc_id}) RETURN d.name as name, d.source_type as type",
                    doc_id=doc_id
                )
                doc_record = await doc_result.single()
                assert doc_record is not None, "Parent Document node not found in Neo4j"
                assert doc_record["type"] == "transcript"
                # Check name was set correctly based on first chunk logic
                assert doc_record["name"] == f"Transcript Document {doc_id}"
                
                # Check Document -> Session relationship
                rel_result = await session.run(
                    "MATCH (d:Document {document_id: $doc_id})-[:ATTACHED_TO]->(s:Session {session_id: $session_id}) RETURN count(s)",
                    doc_id=doc_id, session_id=session_id
                )
                rel_count = await rel_result.single()
                assert rel_count[0] == 1, "Document -> Session relationship not found"
                
                # Check that Chunk nodes exist (created by IngestionService)
                chunk_count_result = await session.run(
                    "MATCH (c:Chunk)-[:PART_OF]->(d:Document {document_id: $doc_id}) RETURN count(c)",
                    doc_id=doc_id
                )
                chunk_count_record = await chunk_count_result.single()
                assert chunk_count_record[0] == len(chunks_to_ingest), "Incorrect number of Chunk nodes found in Neo4j"

        finally:
            await neo4j_driver.close()
            logger.info("Neo4j driver closed in chunk ingestion test") 