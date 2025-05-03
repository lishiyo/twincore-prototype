import os
import sys
import pytest
import asyncio
import pytest_asyncio
import numpy as np
from unittest.mock import AsyncMock
from httpx import AsyncClient

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import app after modifying path
from main import app
from api.routers import admin_router
from services.data_seeder_service import DataSeederService
from services.data_management_service import DataManagementService
from services.embedding_service import EmbeddingService
from services.ingestion_service import IngestionService
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from core.config import settings
from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from .test_utils import setup_test_databases, clear_test_databases, get_test_neo4j_driver, get_test_async_qdrant_client


# For E2E tests, we want to use the real dependencies and test databases

@pytest_asyncio.fixture
async def initialized_app():
    """Ensures the app is initialized with proper database setup."""
    # Initialize databases for E2E tests using test databases
    await setup_test_databases()
    
    # Clear any existing app dependency overrides from unit tests
    # This is crucial to ensure E2E tests use real services, not mocks
    app.dependency_overrides = {}
    
    # Set up real service dependencies for E2E tests with test database connections
    async def get_real_neo4j_dal():
        """Get Neo4j DAL with test database driver."""
        driver = await get_test_neo4j_driver()
        return Neo4jDAL(driver=driver)
    
    async def get_real_embedding_service():
        """
        Get a mock embedding service to avoid OpenAI API dependencies in tests.
        The mock will return random vectors of the correct dimensionality.
        """
        # Create a mock embedding service for testing
        mock_embedding_service = AsyncMock(spec=EmbeddingService)
        
        # Mock the get_embedding method to return a random vector of the correct dimensionality
        async def mock_get_embedding(text):
            # Create a random vector of the correct dimensionality (from settings)
            vector = np.random.randn(settings.embedding_dimension).astype(np.float32).tolist()
            return vector
        
        # Assign the mock method
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
    
    # Override dependencies to use real services with test databases
    app.dependency_overrides[admin_router.get_data_seeder_service] = get_real_data_seeder_service
    app.dependency_overrides[admin_router.get_data_management_service] = get_real_data_management_service
    
    return app

@pytest_asyncio.fixture(autouse=True)
async def clear_test_data():
    """Clear test data before and after each test."""
    # Clear before test
    await clear_test_databases()
    
    yield  # Run the test
    
    # Clear again after the test
    await clear_test_databases() 