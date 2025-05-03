"""Tests for the admin router endpoints."""

import pytest
from fastapi.testclient import TestClient

from services.data_seeder_service import DataSeederServiceError

def test_seed_data_success(client: TestClient, mock_seed_data):
    """Test that the seed_data endpoint returns 202 with success message when seeding succeeds."""
    
    # Mock data to be returned by the seed_initial_data method
    mock_result = {
        "total": 15,
        "counts_by_type": {
            "message": 8,
            "document_chunk": 7
        }
    }
    
    # Configure the mock to return our test data
    mock_seed_data.return_value = mock_result
    
    # Call the endpoint
    response = client.post("/api/seed_data")
    
    # Verify the response
    assert response.status_code == 202
    assert response.json()["status"] == "success"
    assert response.json()["message"] == "Successfully seeded 15 items"
    assert response.json()["data"] == mock_result
    
    # Verify the service method was called
    mock_seed_data.assert_called_once()

def test_seed_data_failure(client: TestClient, mock_seed_data):
    """Test that the seed_data endpoint returns 500 when seeding fails."""
    
    # Configure the mock to raise an exception
    mock_seed_data.side_effect = DataSeederServiceError("Failed to seed data")
    
    # Call the endpoint
    response = client.post("/api/seed_data")
    
    # Verify the response
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to seed data"
    
    # Verify the service method was called
    mock_seed_data.assert_called_once() 