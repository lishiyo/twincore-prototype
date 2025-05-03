"""Test fixtures for the TwinCore backend."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app
from core.db_clients import get_qdrant_client, get_async_qdrant_client, get_neo4j_driver, get_database_clients


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """Clear LRU cache before each test to ensure clean state."""
    get_qdrant_client.cache_clear()
    get_async_qdrant_client.cache_clear()
    get_neo4j_driver.cache_clear()
    get_database_clients.cache_clear()
    yield 