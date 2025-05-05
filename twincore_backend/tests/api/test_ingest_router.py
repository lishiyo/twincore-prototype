"""Tests for the ingest router endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi import status

from ingestion.connectors.message_connector import MessageConnector
from ingestion.connectors.document_connector import DocumentConnector
from api.routers import ingest_router


@pytest.fixture
def mock_message_connector():
    """Mock MessageConnector for testing."""
    connector = AsyncMock(spec=MessageConnector)
    return connector


@pytest.fixture
def mock_document_connector():
    """Mock DocumentConnector for testing."""
    connector = AsyncMock(spec=DocumentConnector)
    return connector


class TestMessageIngestionEndpoint:
    """Tests for the message ingestion endpoint."""

    def test_ingest_message_success(self, client, mock_message_connector):
        """Test successful message ingestion."""
        # Arrange
        mock_message_connector.ingest_message.return_value = True
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_message_connector] = lambda: mock_message_connector
        
        # Test data
        message_data = {
            "text": "This is a test message",
            "source_type": "message",
            "user_id": str(uuid.uuid4()),
            "project_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "message_id": str(uuid.uuid4()),
            "is_twin_chat": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Act
        response = client.post("/v1/ingest/message", json=message_data)
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted", "message": "Message received and queued for ingestion."}
        mock_message_connector.ingest_message.assert_called_once()
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_message_without_optional_fields(self, client, mock_message_connector):
        """Test message ingestion with only required fields."""
        # Arrange
        mock_message_connector.ingest_message.return_value = True
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_message_connector] = lambda: mock_message_connector
        
        # Test data with only required fields
        message_data = {
            "text": "This is a test message",
            "source_type": "message",  # This field is required by ContentBase
            "user_id": str(uuid.uuid4())
        }
        
        # Act
        response = client.post("/v1/ingest/message", json=message_data)
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_message_connector.ingest_message.assert_called_once()
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_message_missing_required_fields(self, client, mock_message_connector):
        """Test message ingestion fails with missing required fields."""
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_message_connector] = lambda: mock_message_connector
        
        # Test data missing required user_id
        message_data = {
            "text": "This is a test message",
            "source_type": "message"  # Include source_type but not user_id
        }
        
        # Act
        response = client.post("/v1/ingest/message", json=message_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_message_service_error(self, client, mock_message_connector):
        """Test handling of service errors during message ingestion."""
        # Arrange
        mock_message_connector.ingest_message.side_effect = Exception("Test error")
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_message_connector] = lambda: mock_message_connector
        
        # Test data
        message_data = {
            "text": "This is a test message",
            "source_type": "message",  # This field is required by ContentBase
            "user_id": str(uuid.uuid4())
        }
        
        # Act
        response = client.post("/v1/ingest/message", json=message_data)
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()["detail"]
        
        # Clean up
        app.dependency_overrides.clear()


class TestDocumentIngestionEndpoint:
    """Tests for the document ingestion endpoint."""

    def test_ingest_document_success(self, client, mock_document_connector):
        """Test successful document ingestion."""
        # Arrange
        mock_document_connector.ingest_document.return_value = True
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_document_connector] = lambda: mock_document_connector
        
        # Test data
        document_data = {
            "text": "This is a test document content.",
            "source_type": "document",
            "doc_name": "Test Document.pdf",
            "user_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "project_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "is_private": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Act
        response = client.post("/v1/ingest/document", json=document_data)
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted", "message": "Document received and queued for ingestion."}
        mock_document_connector.ingest_document.assert_called_once()
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_document_without_optional_fields(self, client, mock_document_connector):
        """Test document ingestion with only required fields."""
        # Arrange
        mock_document_connector.ingest_document.return_value = True
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_document_connector] = lambda: mock_document_connector
        
        # Test data with only required fields
        document_data = {
            "text": "This is a test document.",
            "source_type": "document",  # This field is required by ContentBase
            "doc_name": "Test Document.txt"
        }
        
        # Act
        response = client.post("/v1/ingest/document", json=document_data)
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_document_connector.ingest_document.assert_called_once()
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_document_missing_required_fields(self, client, mock_document_connector):
        """Test document ingestion fails with missing required fields."""
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_document_connector] = lambda: mock_document_connector
        
        # Test data missing required doc_name
        document_data = {
            "text": "This is a test document.",
            "source_type": "document"  # Include source_type but not doc_name
        }
        
        # Act
        response = client.post("/v1/ingest/document", json=document_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_document_service_error(self, client, mock_document_connector):
        """Test handling of service errors during document ingestion."""
        # Arrange
        mock_document_connector.ingest_document.side_effect = Exception("Test error")
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_document_connector] = lambda: mock_document_connector
        
        # Test data
        document_data = {
            "text": "This is a test document.",
            "source_type": "document",
            "doc_name": "Test Document.pdf"
        }
        
        # Act
        response = client.post("/v1/ingest/document", json=document_data)
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()["detail"]
        
        # Clean up
        app.dependency_overrides.clear()


class TestChunkIngestionEndpoint:
    """Tests for the chunk ingestion endpoint (/v1/ingest/chunk)."""

    def test_ingest_chunk_success(self, client, mock_document_connector):
        """Test successful chunk ingestion."""
        # Arrange
        mock_document_connector.ingest_chunk.return_value = True
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_document_connector] = lambda: mock_document_connector
        
        # Test data
        chunk_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "text": "This is a transcript utterance chunk.",
            "timestamp": datetime.now().isoformat(),
            "project_id": str(uuid.uuid4()),
            "chunk_id": str(uuid.uuid4()), # Optional source chunk ID
            "metadata": {"turn": 1} 
        }
        
        # Act
        response = client.post("/v1/ingest/chunk", json=chunk_data)
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json() == {"status": "accepted", "message": "Chunk received and queued for ingestion."}
        
        # Convert timestamp string to datetime object for assertion comparison
        expected_call_data = chunk_data.copy()
        expected_call_data["timestamp"] = datetime.fromisoformat(chunk_data["timestamp"])
        
        mock_document_connector.ingest_chunk.assert_called_once_with(expected_call_data)
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_chunk_without_optional_fields(self, client, mock_document_connector):
        """Test chunk ingestion with only required fields."""
        # Arrange
        mock_document_connector.ingest_chunk.return_value = True
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_document_connector] = lambda: mock_document_connector
        
        # Test data with only required fields
        chunk_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "text": "Minimal chunk data.",
            "timestamp": datetime.now().isoformat(),
        }
        
        # Act
        response = client.post("/v1/ingest/chunk", json=chunk_data)
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        # Assert that the connector was called with the data provided
        
        # Convert timestamp string to datetime object for assertion comparison
        expected_call_data = chunk_data.copy()
        expected_call_data["timestamp"] = datetime.fromisoformat(chunk_data["timestamp"])
        expected_call_data["project_id"] = None
        expected_call_data["chunk_id"] = None
        expected_call_data["metadata"] = {}

        mock_document_connector.ingest_chunk.assert_called_once_with(expected_call_data)
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_chunk_missing_required_fields(self, client, mock_document_connector):
        """Test chunk ingestion fails with missing required fields."""
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_document_connector] = lambda: mock_document_connector
        
        # Test data missing required doc_id
        chunk_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            # "doc_id": missing,
            "text": "Chunk missing doc id.",
            "timestamp": datetime.now().isoformat(),
        }
        
        # Act
        response = client.post("/v1/ingest/chunk", json=chunk_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        # Optionally check error detail for the specific missing field
        assert "doc_id" in str(response.json())
        
        # Clean up
        app.dependency_overrides.clear()

    def test_ingest_chunk_connector_error(self, client, mock_document_connector):
        """Test handling of connector errors during chunk ingestion."""
        # Arrange
        mock_document_connector.ingest_chunk.side_effect = Exception("Connector failed")
        
        # Apply the mock using FastAPI's dependency_overrides
        from main import app
        app.dependency_overrides[ingest_router.get_document_connector] = lambda: mock_document_connector
        
        # Test data
        chunk_data = {
            "user_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "doc_id": str(uuid.uuid4()),
            "text": "Chunk destined to fail.",
            "timestamp": datetime.now().isoformat(),
        }
        
        # Act
        response = client.post("/v1/ingest/chunk", json=chunk_data)
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()["detail"]
        assert "chunk ingestion" in response.json()["detail"]["error"]
        
        # Clean up
        app.dependency_overrides.clear() 