"""
Unit tests for database client initialization.
These tests mock the external dependencies to focus on testing the initialization logic.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.db_clients import get_qdrant_client, get_neo4j_driver, get_database_clients


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear LRU cache before each test to ensure clean state."""
    get_qdrant_client.cache_clear()
    get_neo4j_driver.cache_clear()
    get_database_clients.cache_clear()
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


class TestQdrantClient:
    
    @patch('core.db_clients.QdrantClient')
    def test_get_qdrant_client_success(self, mock_qdrant_client, mock_settings):
        """Test successful Qdrant client initialization."""
        # Configure the mock
        mock_client_instance = MagicMock()
        mock_qdrant_client.return_value = mock_client_instance
        
        # Call the function
        client = get_qdrant_client()
        
        # Verify correct parameters were used
        mock_qdrant_client.assert_called_once_with(
            host=mock_settings.qdrant_host,
            port=mock_settings.qdrant_port,
            api_key=mock_settings.qdrant_api_key,
            prefer_grpc=mock_settings.qdrant_prefer_grpc,
            grpc_port=mock_settings.qdrant_grpc_port,
            https=False
        )
        
        # Verify health check was performed
        mock_client_instance.get_collections.assert_called_once()
        
        # Verify the return value
        assert client == mock_client_instance
    
    @patch('core.db_clients.QdrantClient')
    def test_get_qdrant_client_connection_error(self, mock_qdrant_client, mock_settings):
        """Test Qdrant client initialization with connection error."""
        # Configure the mock to raise an error
        mock_client_instance = MagicMock()
        mock_qdrant_client.return_value = mock_client_instance
        # Use generic Exception instead of UnexpectedResponse
        mock_client_instance.get_collections.side_effect = Exception("Connection error")
        
        # Call the function and verify it raises the expected error
        with pytest.raises(Exception):
            get_qdrant_client()


class TestNeo4jDriver:
    
    @patch('core.db_clients.GraphDatabase')
    def test_get_neo4j_driver_success(self, mock_graph_db, mock_settings):
        """Test successful Neo4j driver initialization."""
        # Configure the mock
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Call the function
        driver = get_neo4j_driver()
        
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
    
    @patch('core.db_clients.GraphDatabase')
    def test_get_neo4j_driver_connection_error(self, mock_graph_db, mock_settings):
        """Test Neo4j driver initialization with connection error."""
        # Need to fix issue with how we set up the mocking
        # Configure the correct location for the error
        mock_driver = MagicMock()
        mock_graph_db.driver.return_value = mock_driver
        # Make session creation work but make the run method raise an exception
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.side_effect = Exception("Connection error")
        
        # Call the function and verify it raises the expected error
        with pytest.raises(Exception):
            get_neo4j_driver()


class TestDatabaseClients:
    
    @patch('core.db_clients.get_qdrant_client')
    @patch('core.db_clients.get_neo4j_driver')
    def test_get_database_clients(self, mock_get_neo4j, mock_get_qdrant):
        """Test the convenience function to get both clients."""
        # Configure mocks
        mock_qdrant = MagicMock()
        mock_neo4j = MagicMock()
        mock_get_qdrant.return_value = mock_qdrant
        mock_get_neo4j.return_value = mock_neo4j
        
        # Call the function
        qdrant, neo4j = get_database_clients()
        
        # Verify both clients are returned correctly
        assert qdrant == mock_qdrant
        assert neo4j == mock_neo4j
        mock_get_qdrant.assert_called_once()
        mock_get_neo4j.assert_called_once() 