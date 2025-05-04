"""Test fixtures for the TwinCore backend."""

import os
import sys
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import app after modifying path
from main import app
from api.routers import admin_router
from core.db_clients import clear_all_client_caches


# Create mock services
mock_data_seeder_service = AsyncMock()
mock_data_seeder_instance = AsyncMock()
mock_data_seeder_instance.seed_initial_data = AsyncMock()
mock_data_seeder_service.return_value = mock_data_seeder_instance

# Create mock for data management service
mock_data_management_instance = AsyncMock()
mock_data_management_instance.clear_all_data = AsyncMock()

# We'll set these up in the fixture instead of globally
# to avoid interfering with E2E tests


@pytest.fixture
def setup_mock_dependencies():
    """Set up mock dependencies for unit tests."""
    # Save existing overrides to restore later
    original_overrides = app.dependency_overrides.copy()
    
    # Apply mock overrides for unit tests
    app.dependency_overrides[admin_router.get_data_seeder_service] = lambda: mock_data_seeder_instance
    app.dependency_overrides[admin_router.get_data_management_service] = lambda: mock_data_management_instance
    
    yield
    
    # Restore original overrides after the test
    app.dependency_overrides = original_overrides


@pytest.fixture
def client(setup_mock_dependencies):
    """Create a test client for the FastAPI app with mock dependencies."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_seed_data():
    """Return the mock for seed_initial_data method."""
    # Reset any side effects before each test
    mock_data_seeder_instance.seed_initial_data.reset_mock()
    return mock_data_seeder_instance.seed_initial_data


@pytest.fixture
def mock_clear_data():
    """Return the mock for clear_all_data method."""
    # Reset any side effects before each test
    mock_data_management_instance.clear_all_data.reset_mock()
    return mock_data_management_instance.clear_all_data


@pytest.fixture(autouse=True)
def clear_db_clients():
    """Clear database client instances before each test to ensure clean state."""
    clear_all_client_caches()
    yield 