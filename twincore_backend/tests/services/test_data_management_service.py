import pytest
from unittest.mock import AsyncMock

from services.data_management_service import DataManagementService, DataManagementServiceError
from dal.qdrant_dal import QdrantDAL  # Assuming we need this for instantiation
from dal.neo4j_dal import Neo4jDAL

# Mock dependencies
@pytest.fixture
def mock_qdrant_dal() -> AsyncMock:
    return AsyncMock(spec=QdrantDAL)

@pytest.fixture
def mock_neo4j_dal() -> AsyncMock:
    return AsyncMock(spec=Neo4jDAL)

@pytest.fixture
def data_management_service(
    mock_qdrant_dal: AsyncMock, mock_neo4j_dal: AsyncMock
) -> DataManagementService:
    """Fixture to create a DataManagementService with mocked DALs."""
    return DataManagementService(qdrant_dal=mock_qdrant_dal, neo4j_dal=mock_neo4j_dal)

@pytest.mark.asyncio
async def test_update_document_metadata_success(
    data_management_service: DataManagementService, mock_neo4j_dal: AsyncMock
):
    """Test update_document_metadata successfully updates via Neo4jDAL."""
    doc_id = "test-doc-123"
    source_uri = "s3://new-uri/doc.txt"
    metadata = {"key": "value"}
    
    # Configure mock DAL to return success
    mock_neo4j_dal.update_document_metadata.return_value = True
    
    success = await data_management_service.update_document_metadata(
        doc_id=doc_id, source_uri=source_uri, metadata=metadata
    )
    
    assert success is True
    mock_neo4j_dal.update_document_metadata.assert_awaited_once_with(
        doc_id=doc_id, source_uri=source_uri, metadata=metadata
    )

@pytest.mark.asyncio
async def test_update_document_metadata_not_found(
    data_management_service: DataManagementService, mock_neo4j_dal: AsyncMock
):
    """Test update_document_metadata returns False if DAL indicates document not found."""
    doc_id = "non-existent-doc"
    source_uri = "s3://new-uri/doc.txt"
    metadata = {"key": "value"}
    
    # Configure mock DAL to return failure (document not found)
    mock_neo4j_dal.update_document_metadata.return_value = False
    
    success = await data_management_service.update_document_metadata(
        doc_id=doc_id, source_uri=source_uri, metadata=metadata
    )
    
    assert success is False
    mock_neo4j_dal.update_document_metadata.assert_awaited_once_with(
        doc_id=doc_id, source_uri=source_uri, metadata=metadata
    )

@pytest.mark.asyncio
async def test_update_document_metadata_dal_error(
    data_management_service: DataManagementService, mock_neo4j_dal: AsyncMock
):
    """Test update_document_metadata raises DataManagementServiceError if DAL fails."""
    doc_id = "test-doc-error"
    source_uri = "s3://new-uri/doc.txt"
    metadata = {"key": "value"}
    error_message = "Neo4j connection failed"
    
    # Configure mock DAL to raise an exception
    mock_neo4j_dal.update_document_metadata.side_effect = Exception(error_message)
    
    with pytest.raises(DataManagementServiceError) as excinfo:
        await data_management_service.update_document_metadata(
            doc_id=doc_id, source_uri=source_uri, metadata=metadata
        )
        
    assert error_message in str(excinfo.value)
    mock_neo4j_dal.update_document_metadata.assert_awaited_once_with(
        doc_id=doc_id, source_uri=source_uri, metadata=metadata
    ) 