"""Tests for Data Seeder Service implementation.

This module contains tests for the DataSeederService class, with mocked dependencies
to verify that the service correctly orchestrates the seeding process.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime

from services.data_seeder_service import DataSeederService, DataSeederServiceError
from services.ingestion_service import IngestionService


@pytest.fixture
def mock_ingestion_service():
    """Create a mock IngestionService."""
    service = MagicMock(spec=IngestionService)
    service.ingest_chunk = AsyncMock()
    service.ingest_chunk.return_value = True
    return service


@pytest.fixture
def data_seeder_service(mock_ingestion_service):
    """Create a DataSeederService with a mocked IngestionService."""
    return DataSeederService(ingestion_service=mock_ingestion_service)


class TestDataSeederService:
    """Tests for the DataSeederService class."""

    def test_init_missing_dependencies(self):
        """Test initialization with missing dependencies raises errors."""
        with pytest.raises(ValueError, match="IngestionService must be provided"):
            DataSeederService(ingestion_service=None)

    @pytest.mark.asyncio
    @patch('services.data_seeder_service.initial_data_chunks')
    async def test_seed_initial_data_success(self, mock_initial_data, data_seeder_service, mock_ingestion_service):
        """Test successful seeding of initial data."""
        
        # Arrange
        # Create mock data with different source types
        mock_initial_data.__iter__.return_value = [
            {
                "chunk_id": str(uuid.uuid4()),
                "text": "Test message 1",
                "source_type": "message",
                "user_id": str(uuid.uuid4()),
                "project_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "is_private": False,
                "is_twin_interaction": False
            },
            {
                "chunk_id": str(uuid.uuid4()),
                "text": "Test document chunk",
                "source_type": "document_chunk",
                "user_id": str(uuid.uuid4()),
                "doc_id": str(uuid.uuid4()),
                "doc_name": "test.pdf",
                "timestamp": datetime.utcnow().isoformat(),
                "is_private": True,
                "is_twin_interaction": False
            },
            {
                "chunk_id": str(uuid.uuid4()),
                "text": "Test message 2",
                "source_type": "message",
                "user_id": str(uuid.uuid4()),
                "project_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "is_twin_interaction": True,
                "is_private": False
            }
        ]
        
        # Act
        result = await data_seeder_service.seed_initial_data()
        
        # Assert
        assert mock_ingestion_service.ingest_chunk.call_count == 3
        
        # Verify the result format
        assert "total" in result
        assert result["total"] == 3
        assert "counts_by_type" in result
        assert result["counts_by_type"]["message"] == 2
        assert result["counts_by_type"]["document_chunk"] == 1
        
        # Verify ingest_chunk was called with correct parameters for each record
        for i, data in enumerate(mock_initial_data):
            call_args = mock_ingestion_service.ingest_chunk.call_args_list[i][1]
            assert call_args["chunk_id"] == data["chunk_id"]
            assert call_args["text_content"] == data["text"]
            assert call_args["source_type"] == data["source_type"]
            assert call_args["user_id"] == data.get("user_id")
            assert call_args["doc_id"] == data.get("doc_id")
            assert call_args["doc_name"] == data.get("doc_name")
            assert call_args["is_private"] == data.get("is_private", False)
            assert call_args["is_twin_interaction"] == data.get("is_twin_interaction", False)
            
    @pytest.mark.asyncio
    @patch('services.data_seeder_service.initial_data_chunks')
    async def test_seed_initial_data_error(self, mock_initial_data, data_seeder_service, mock_ingestion_service):
        """Test error handling during initial data seeding."""
        
        # Arrange
        mock_initial_data.__iter__.return_value = [
            {
                "chunk_id": str(uuid.uuid4()),
                "text": "Test message",
                "source_type": "message",
                "user_id": str(uuid.uuid4())
            }
        ]
        
        # Make ingest_chunk raise an exception
        mock_ingestion_service.ingest_chunk.side_effect = Exception("Test ingestion error")
        
        # Act & Assert
        with pytest.raises(DataSeederServiceError, match="Failed to seed initial data"):
            await data_seeder_service.seed_initial_data()
            
        # Verify ingestion was attempted
        assert mock_ingestion_service.ingest_chunk.called
    
    @pytest.mark.asyncio
    async def test_seed_custom_data_success(self, data_seeder_service, mock_ingestion_service):
        """Test successful seeding of custom data."""
        
        # Arrange
        custom_data = [
            {
                "chunk_id": str(uuid.uuid4()),
                "text": "Custom message",
                "source_type": "message",
                "user_id": str(uuid.uuid4()),
                "message_id": str(uuid.uuid4()),
                "is_private": True
            },
            {
                "chunk_id": str(uuid.uuid4()),
                "text": "Custom document",
                "source_type": "document_chunk",
                "doc_id": str(uuid.uuid4()),
                "doc_name": "custom.txt"
            }
        ]
        
        # Act
        result = await data_seeder_service.seed_custom_data(custom_data)
        
        # Assert
        assert mock_ingestion_service.ingest_chunk.call_count == 2
        
        # Verify the result format
        assert "total" in result
        assert result["total"] == 2
        assert "counts_by_type" in result
        assert result["counts_by_type"]["message"] == 1
        assert result["counts_by_type"]["document_chunk"] == 1
        
        # Verify ingest_chunk was called with correct parameters
        for i, data in enumerate(custom_data):
            call_args = mock_ingestion_service.ingest_chunk.call_args_list[i][1]
            assert call_args["chunk_id"] == data["chunk_id"]
            assert call_args["text_content"] == data["text"]
            assert call_args["source_type"] == data["source_type"]
    
    @pytest.mark.asyncio
    async def test_seed_custom_data_validation(self, data_seeder_service):
        """Test validation of custom data."""
        
        # Missing chunk_id
        invalid_data_1 = [{"text": "Test", "source_type": "message"}]
        with pytest.raises(DataSeederServiceError, match="Each data chunk must have a chunk_id"):
            await data_seeder_service.seed_custom_data(invalid_data_1)
            
        # Missing text
        invalid_data_2 = [{"chunk_id": str(uuid.uuid4()), "source_type": "message"}]
        with pytest.raises(DataSeederServiceError, match="missing required 'text' field"):
            await data_seeder_service.seed_custom_data(invalid_data_2)
            
        # Missing source_type
        invalid_data_3 = [{"chunk_id": str(uuid.uuid4()), "text": "Test"}]
        with pytest.raises(DataSeederServiceError, match="missing required 'source_type' field"):
            await data_seeder_service.seed_custom_data(invalid_data_3)
    
    @pytest.mark.asyncio
    async def test_seed_custom_data_error(self, data_seeder_service, mock_ingestion_service):
        """Test error handling during custom data seeding."""
        
        # Arrange
        custom_data = [{
            "chunk_id": str(uuid.uuid4()),
            "text": "Custom message",
            "source_type": "message"
        }]
        
        # Make ingest_chunk raise an exception
        mock_ingestion_service.ingest_chunk.side_effect = Exception("Test ingestion error")
        
        # Act & Assert
        with pytest.raises(DataSeederServiceError, match="Failed to seed custom data"):
            await data_seeder_service.seed_custom_data(custom_data)
            
        # Verify ingestion was attempted
        assert mock_ingestion_service.ingest_chunk.called 