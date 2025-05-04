"""
Unit tests for database client initialization.
These tests mock the external dependencies to focus on testing the initialization logic.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from core.db_clients import get_async_qdrant_client, get_neo4j_driver, clear_all_client_caches


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear client caches before each test to ensure clean state."""
    clear_all_client_caches()
    yield


@pytest.fixture
def mock_settings():
    """Fixture to mock settings for testing."""
    with patch('core.db_clients.settings') as mock_settings:
        # Configure mock settings with test values
        mock_settings.qdrant_host = "test-qdrant-host"
        mock_settings.qdrant_port = 9999
        mock_settings.qdrant_api_key = None
        mock_settings.qdrant_prefer_grpc = False
        mock_settings.qdrant_grpc_port = 6334
        mock_settings.neo4j_uri = "bolt://test-neo4j-host:9999"
        mock_settings.neo4j_user = "test-user"
        mock_settings.neo4j_password = "test-password"
        yield mock_settings


class TestAsyncQdrantClient:
    
    @patch('core.db_clients.AsyncQdrantClient')
    def test_get_async_qdrant_client_success(self, mock_qdrant_client, mock_settings):
        """Test successful Async Qdrant client initialization."""
        # Configure the mock
        mock_client_instance = MagicMock()
        mock_qdrant_client.return_value = mock_client_instance
        
        # Call the function
        client = get_async_qdrant_client()
        
        # Verify correct parameters were used
        mock_qdrant_client.assert_called_once_with(
            host=mock_settings.qdrant_host,
            port=mock_settings.qdrant_port,
            api_key=mock_settings.qdrant_api_key,
            prefer_grpc=mock_settings.qdrant_prefer_grpc,
            grpc_port=mock_settings.qdrant_grpc_port,
            https=False
        )
        
        # No health check for async client - would require await
        
        # Verify the return value
        assert client == mock_client_instance
    
    @patch('core.db_clients.AsyncQdrantClient')
    def test_get_async_qdrant_client_connection_error(self, mock_qdrant_client, mock_settings):
        """Test Async Qdrant client initialization with connection error."""
        # Configure the mock to raise an error
        mock_qdrant_client.side_effect = Exception("Connection error")
        
        # Call the function and verify it raises the expected error
        with pytest.raises(Exception):
            get_async_qdrant_client()


class TestNeo4jDriver:
    
    @pytest.mark.asyncio
    @patch('core.db_clients.AsyncGraphDatabase')
    async def test_get_neo4j_driver_success(self, mock_graph_db, mock_settings):
        """Test successful Neo4j driver initialization."""
        # Create session mock that will be used inside the context manager
        mock_session = AsyncMock()
        mock_session.run = AsyncMock()
        
        # Create a mock session context manager
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        
        # Create driver mock
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session_ctx)
        
        # Configure the mock driver factory
        mock_graph_db.driver.return_value = mock_driver
        
        # Call the function
        driver = await get_neo4j_driver()
        
        # Verify correct parameters were used
        mock_graph_db.driver.assert_called_once_with(
            mock_settings.neo4j_uri, 
            auth=(mock_settings.neo4j_user, mock_settings.neo4j_password)
        )
        
        # Verify session was created and query executed
        mock_driver.session.assert_called_once()
        mock_session.run.assert_called_once_with("RETURN 1")
        
        # Verify the return value
        assert driver == mock_driver
    
    @pytest.mark.asyncio
    @patch('core.db_clients.AsyncGraphDatabase')
    async def test_get_neo4j_driver_connection_error(self, mock_graph_db, mock_settings):
        """Test Neo4j driver initialization with connection error."""
        # Create session mock that will be used inside the context manager
        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Connection error"))
        
        # Create a mock session context manager
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        
        # Create driver mock
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session_ctx)
        
        # Configure the mock driver factory
        mock_graph_db.driver.return_value = mock_driver
        
        # Call the function and verify it raises the expected error
        with pytest.raises(Exception):
            await get_neo4j_driver()


class TestDatabaseClients:
    
    @pytest.mark.asyncio
    @patch('core.db_clients.AsyncQdrantClient')
    @patch('core.db_clients.AsyncGraphDatabase')
    async def test_get_database_clients(self, mock_graph_db, mock_async_qdrant):
        """Test that both client initialization functions work independently."""
        # Configure Qdrant mock
        mock_async_client = MagicMock()
        mock_async_qdrant.return_value = mock_async_client
        
        # Create Neo4j session mock
        mock_session = AsyncMock()
        mock_session.run = AsyncMock()
        
        # Create a mock session context manager
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        
        # Create Neo4j driver mock
        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session_ctx)
        
        # Configure the mock driver factory
        mock_graph_db.driver.return_value = mock_driver
        
        # Call the functions directly
        qdrant = get_async_qdrant_client()
        neo4j = await get_neo4j_driver()
        
        # Verify both clients are initialized correctly
        assert qdrant is not None
        assert neo4j is not None
        mock_async_qdrant.assert_called_once()
        mock_graph_db.driver.assert_called_once() 