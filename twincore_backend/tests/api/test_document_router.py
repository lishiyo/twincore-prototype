"""Tests for the document router endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from services.data_management_service import DataManagementServiceError

def test_update_document_metadata_success(client: TestClient, mock_update_document_metadata):
    """Test successful update of document metadata (200 OK)."""
    doc_id = "doc-abc-123"
    update_payload = {
        "user_id": "user-test-updater",
        "source_uri": "s3://updated-uri/final.txt",
        "metadata": {"status": "finalized"}
    }

    # Configure the mock to return success
    mock_update_document_metadata.return_value = True

    # Call the endpoint
    response = client.post(f"/v1/documents/{doc_id}/metadata", json=update_payload)

    # Verify the response
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "success",
        "message": f"Metadata updated successfully for document {doc_id}."
    }
    
    # Verify the service method was called correctly
    mock_update_document_metadata.assert_called_once_with(
        doc_id=doc_id,
        source_uri=update_payload["source_uri"],
        metadata=update_payload["metadata"]
    )

def test_update_document_metadata_not_found(client: TestClient, mock_update_document_metadata):
    """Test updating metadata for a non-existent document (404 Not Found)."""
    doc_id = "doc-not-found-456"
    update_payload = {
        "user_id": "user-test-updater",
        "source_uri": "s3://some-uri/final.txt"
    }

    # Configure the mock to return failure (document not found)
    mock_update_document_metadata.return_value = False

    # Call the endpoint
    response = client.post(f"/v1/documents/{doc_id}/metadata", json=update_payload)

    # Verify the response
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": f"Document with ID {doc_id} not found."}
    
    # Verify the service method was called
    mock_update_document_metadata.assert_called_once()

def test_update_document_metadata_validation_error(client: TestClient, mock_update_document_metadata):
    """Test update metadata with invalid payload (422 Unprocessable Entity)."""
    doc_id = "doc-validation-789"
    # Missing required 'user_id'
    invalid_payload = {
        "source_uri": "s3://invalid/payload.txt"
    }

    # Call the endpoint
    response = client.post(f"/v1/documents/{doc_id}/metadata", json=invalid_payload)

    # Verify the response
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Check for detail structure typical of Pydantic validation errors
    assert "detail" in response.json()
    assert isinstance(response.json()["detail"], list)
    assert response.json()["detail"][0]["type"] == "missing"
    assert response.json()["detail"][0]["loc"] == ["body", "user_id"]
    
    # Ensure the service method was NOT called
    mock_update_document_metadata.assert_not_called()

def test_update_document_metadata_service_error(client: TestClient, mock_update_document_metadata):
    """Test handling of internal server error from the service (500)."""
    doc_id = "doc-service-error-000"
    update_payload = {
        "user_id": "user-test-updater",
        "source_uri": "s3://error-uri/final.txt"
    }
    error_message = "Database connection lost"

    # Configure the mock to raise an error
    mock_update_document_metadata.side_effect = DataManagementServiceError(error_message)

    # Call the endpoint
    response = client.post(f"/v1/documents/{doc_id}/metadata", json=update_payload)

    # Verify the response
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_message}
    
    # Verify the service method was called
    mock_update_document_metadata.assert_called_once() 