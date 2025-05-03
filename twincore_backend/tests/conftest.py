"""Test fixtures for the TwinCore backend."""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import app after modifying path
from main import app
from api.routers import admin_router
from core.db_clients import get_async_qdrant_client


# Create mock services
mock_data_seeder_service = AsyncMock()
mock_data_seeder_instance = AsyncMock()
mock_data_seeder_instance.seed_initial_data = AsyncMock()
mock_data_seeder_service.return_value = mock_data_seeder_instance

# Set up app-level dependency overrides - this is the key fix
app.dependency_overrides[admin_router.get_data_seeder_service] = lambda: mock_data_seeder_instance


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_seed_data():
    """Return the mock for seed_initial_data method."""
    # Reset any side effects before each test
    mock_data_seeder_instance.seed_initial_data.reset_mock()
    return mock_data_seeder_instance.seed_initial_data


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear LRU cache before each test to ensure clean state."""
    get_async_qdrant_client.cache_clear()
    # No longer clearing Neo4j driver cache since it's async
    yield 