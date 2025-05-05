import os
import sys
import pytest
import asyncio
import pytest_asyncio
import numpy as np
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import app after modifying path
from main import app
from api.routers import admin_router, ingest_router
from services.data_seeder_service import DataSeederService
from services.data_management_service import DataManagementService
from services.embedding_service import EmbeddingService
from services.ingestion_service import IngestionService
from services.retrieval_service import RetrievalService
from ingestion.connectors.message_connector import MessageConnector
from ingestion.connectors.document_connector import DocumentConnector
from ingestion.processors.text_chunker import TextChunker
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from core.config import settings
from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from .test_utils import setup_test_databases, clear_test_databases, get_test_neo4j_driver, get_test_async_qdrant_client
import logging

# Import Qdrant models for collection creation
from qdrant_client import models as qdrant_models

logger = logging.getLogger(__name__)

# For E2E tests, we want to use the real dependencies and test databases

@pytest_asyncio.fixture(scope="class", autouse=True)
async def ensure_collection_exists():
    """
    Fixture to ensure the Qdrant collection exists before tests.
    Runs automatically for all tests in this directory at the class level.
    """
    logger.info("==== E2E CONTEST: ENSURING QDRANT COLLECTION ====")
    
    try:
        # Get a fresh Qdrant client
        qdrant_client = await get_test_async_qdrant_client()
        
        # Always attempt to delete the collection first to ensure a clean state
        try:
            await qdrant_client.delete_collection(collection_name="twin_memory")
            logger.info("E2E CONTEST: Deleted existing twin_memory collection")
        except Exception as e:
            # Collection might not exist, ignore the error
            logger.info(f"E2E CONTEST: Couldn't delete collection: {e}")
        
        # Wait a moment after deletion
        await asyncio.sleep(1)
        
        # Create the collection with explicit vector parameters
        logger.info("E2E CONTEST: Creating fresh twin_memory collection")
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
        logger.info(f"E2E CONTEST: Collections after setup: {collection_names}")
        
        if "twin_memory" not in collection_names:
            raise RuntimeError("Failed to create twin_memory collection")
        
        # Create explicit index for metadata filtering
        await qdrant_client.create_payload_index(
            collection_name="twin_memory",
            field_name="is_twin_interaction",
            field_schema=qdrant_models.PayloadSchemaType.BOOL
        )
        
        await qdrant_client.create_payload_index(
            collection_name="twin_memory",
            field_name="is_private",
            field_schema=qdrant_models.PayloadSchemaType.BOOL
        )
        
        # Explicitly check if the collection exists again to be sure
        try:
            info = await qdrant_client.get_collection(collection_name="twin_memory")
            logger.info(f"E2E CONTEST: Collection twin_memory confirmed exists with {info.vectors_count} vectors")
        except Exception as e:
            logger.error(f"E2E CONTEST: Error checking collection: {e}")
            raise RuntimeError(f"Collection verification failed: {e}")
        
        # Wait to ensure collection is ready
        await asyncio.sleep(2)
        logger.info("E2E CONTEST: Collection twin_memory is ready for test")
        
    except Exception as e:
        logger.error(f"E2E CONTEST: Critical error in collection setup: {e}")
        raise
    
    # Yield control back to the test
    yield
    
    # Optional: Add cleanup if needed, though clear_test_data might handle it
    logger.info("==== E2E CONTEST: COLLECTION FIXTURE TEARDOWN (if needed) ====")

@pytest_asyncio.fixture
async def initialized_app():
    """Ensures test databases are initialized and sets up proper test dependencies."""
    # Initialize databases for E2E tests
    await setup_test_databases()
    
    # Set up real service dependencies for E2E tests with test database connections
    async def get_real_neo4j_dal():
        """Get Neo4j DAL with test database driver."""
        driver = await get_test_neo4j_driver()
        return Neo4jDAL(driver=driver)
    
    async def get_real_embedding_service():
        """Get a mock embedding service for testing."""
        mock_embedding_service = AsyncMock(spec=EmbeddingService)
        
        # Mock the get_embedding method to return a random vector
        async def mock_get_embedding(text):
            vector = np.random.randn(settings.embedding_dimension).astype(np.float32).tolist()
            return vector
        
        mock_embedding_service.get_embedding = mock_get_embedding
        return mock_embedding_service
    
    async def get_real_qdrant_dal():
        """Get Qdrant DAL with test database client."""
        client = await get_test_async_qdrant_client()
        return QdrantDAL(client=client)
    
    async def get_real_ingestion_service():
        """Get Ingestion Service with test dependencies."""
        embedding_service = await get_real_embedding_service()
        qdrant_dal = await get_real_qdrant_dal()
        neo4j_dal = await get_real_neo4j_dal()
        return IngestionService(
            embedding_service=embedding_service,
            qdrant_dal=qdrant_dal,
            neo4j_dal=neo4j_dal
        )
    
    async def get_real_data_seeder_service():
        """Get Data Seeder Service with test ingestion service."""
        ingestion_service = await get_real_ingestion_service()
        return DataSeederService(ingestion_service=ingestion_service)
    
    async def get_real_data_management_service():
        """Get Data Management Service with test DALs."""
        qdrant_dal = await get_real_qdrant_dal()
        neo4j_dal = await get_real_neo4j_dal()
        return DataManagementService(
            qdrant_dal=qdrant_dal, 
            neo4j_dal=neo4j_dal
        )
    
    # Override admin router dependencies to use real services with test databases
    # This is crucial for the seed_data test to work
    app.dependency_overrides[admin_router.get_data_seeder_service] = get_real_data_seeder_service
    app.dependency_overrides[admin_router.get_data_management_service] = get_real_data_management_service
    
    return app

@pytest_asyncio.fixture
async def async_client(initialized_app):
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=initialized_app),
        base_url="http://test"
    ) as client:
        yield client

@pytest_asyncio.fixture(autouse=True) # Revert to autouse=True
async def clear_test_data():
    """
    Clear test data before and after each test. 
    Runs automatically for all tests in this directory.
    """
    logger.info("Clearing test databases before test (autouse=True)")
    
    # Clear before test
    await clear_test_databases()
    
    yield  # Run the test
    
    # Clear again after the test  
    logger.info("Clearing test databases after test (autouse=True)")
    await clear_test_databases()

@pytest_asyncio.fixture
async def use_test_databases():
    """Override FastAPI dependencies to use test databases for E2E tests.
    
    This fixture ensures that all endpoints in the API use the test databases
    during E2E tests rather than the default production databases.
    """
    # Import the test database utilities
    from .test_utils import get_test_neo4j_driver, get_test_async_qdrant_client, get_test_qdrant_client
    
    # Store original functions
    from core.db_clients import get_neo4j_driver as original_get_neo4j_driver
    from core.db_clients import get_async_qdrant_client as original_get_async_qdrant_client
    from api.routers.retrieve_router import get_retrieval_service as original_get_retrieval_service
    from api.routers.retrieve_router import get_retrieval_service_with_message_connector as original_get_retrieval_service_with_connector
    from api.routers.ingest_router import get_message_connector as original_get_message_connector
    from api.routers.ingest_router import get_document_connector as original_get_document_connector
    
    # Import preference service dependency if it exists
    try:
        from api.routers.retrieve_router import get_preference_service as original_get_preference_service
    except ImportError:
        original_get_preference_service = None
    
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
    
    # Create custom connector functions that use the test databases
    async def test_get_message_connector():
        qdrant_client = await test_get_async_qdrant_client()
        neo4j_driver = await test_get_neo4j_driver()
        qdrant_dal = QdrantDAL(client=qdrant_client)
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        embedding_service = EmbeddingService()
        ingestion_service = IngestionService(embedding_service=embedding_service, qdrant_dal=qdrant_dal, neo4j_dal=neo4j_dal)
        return MessageConnector(ingestion_service=ingestion_service)

    async def test_get_document_connector():
        qdrant_client = await test_get_async_qdrant_client()
        neo4j_driver = await test_get_neo4j_driver()
        qdrant_dal = QdrantDAL(client=qdrant_client)
        neo4j_dal = Neo4jDAL(driver=neo4j_driver)
        embedding_service = EmbeddingService()
        ingestion_service = IngestionService(embedding_service=embedding_service, qdrant_dal=qdrant_dal, neo4j_dal=neo4j_dal)
        text_chunker = TextChunker()
        return DocumentConnector(ingestion_service=ingestion_service, text_chunker=text_chunker)
    
    # Apply the overrides
    app.dependency_overrides[original_get_retrieval_service] = test_get_retrieval_service
    app.dependency_overrides[original_get_retrieval_service_with_connector] = test_get_retrieval_service_with_connector
    app.dependency_overrides[original_get_message_connector] = test_get_message_connector
    app.dependency_overrides[original_get_document_connector] = test_get_document_connector
    
    # Apply preference service override if it exists
    if original_get_preference_service:
        async def test_get_preference_service():
            from services.preference_service import PreferenceService
            
            qdrant_client = await test_get_async_qdrant_client()
            neo4j_driver = await test_get_neo4j_driver()
            
            qdrant_dal = QdrantDAL(client=qdrant_client)
            neo4j_dal = Neo4jDAL(driver=neo4j_driver)
            embedding_service = EmbeddingService()
            
            return PreferenceService(
                qdrant_dal=qdrant_dal,
                neo4j_dal=neo4j_dal,
                embedding_service=embedding_service
            )
        app.dependency_overrides[original_get_preference_service] = test_get_preference_service
    
    # Yield control back to the test
    yield
    
    # Cleanup: Restore the original dependencies
    if original_get_retrieval_service in app.dependency_overrides:
        del app.dependency_overrides[original_get_retrieval_service]
    if original_get_retrieval_service_with_connector in app.dependency_overrides:
        del app.dependency_overrides[original_get_retrieval_service_with_connector]
    if original_get_preference_service and original_get_preference_service in app.dependency_overrides:
        del app.dependency_overrides[original_get_preference_service]
    # --- Add cleanup for ingest connectors ---
    if original_get_message_connector in app.dependency_overrides:
        del app.dependency_overrides[original_get_message_connector]
    if original_get_document_connector in app.dependency_overrides:
        del app.dependency_overrides[original_get_document_connector] 