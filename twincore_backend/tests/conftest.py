"""Test fixtures for the TwinCore backend."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app) 