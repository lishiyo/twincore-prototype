"""Router for document-specific operations."""

from fastapi import APIRouter, Depends, HTTPException, Path, Body, status
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from api.models import StatusResponse
from services.data_management_service import DataManagementService, DataManagementServiceError
import logging

logger = logging.getLogger(__name__)

# Define request body model for metadata update
class DocumentMetadataUpdateRequest(BaseModel):
    user_id: str = Field(..., description="ID of the user performing the update")
    source_uri: Optional[str] = Field(None, description="The URI of the raw document file (e.g., completed transcript)")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp of the update (defaults to now)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Other metadata fields to add or update")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "user-system-123",
                    "source_uri": "s3://my-transcripts/session-abc-final.txt",
                    "metadata": {
                        "final_participant_count": 3,
                        "duration_seconds": 3600
                    }
                }
            ]
        }
    }


# Create router with prefix and tags for documentation
router = APIRouter(
    prefix="/v1/documents",
    tags=["documents"],
    responses={404: {"description": "Not Found"}}
)

# Dependency to get the DataManagementService (will be implemented in main.py)
# NOTE: This needs to be correctly implemented/imported in main.py
async def get_data_management_service() -> DataManagementService:
    """Dependency placeholder for DataManagementService."""
    # This will be replaced in main.py with the actual dependency
    pass

@router.post(
    "/{doc_id}/metadata",
    status_code=status.HTTP_200_OK,
    response_model=StatusResponse,
    summary="Update Document Metadata",
    description="Updates metadata for an existing document, such as adding a source URI for a completed transcript."
)
async def update_document_metadata_endpoint(
    doc_id: str = Path(..., description="The unique ID of the document to update."),
    update_data: DocumentMetadataUpdateRequest = Body(...),
    management_service: DataManagementService = Depends(get_data_management_service)
) -> StatusResponse:
    """Update metadata for a specific document identified by doc_id."""
    try:
        logger.info(f"Updating metadata for document {doc_id} with source URI: {update_data.source_uri} and metadata: {update_data.metadata}")
        
        success = await management_service.update_document_metadata(
            doc_id=doc_id,
            source_uri=update_data.source_uri,
            metadata=update_data.metadata
        )
        
        logger.info(f"Service call returned: {success}")

        if not success:
            logger.info("Raising 404 error...")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {doc_id} not found."
            )

        return StatusResponse(
            status="success",
            message=f"Metadata updated successfully for document {doc_id}."
        )

    except DataManagementServiceError as e:
        logger.error(f"DataManagementServiceError caught: {e}", exc_info=True)
        # Service errors might include validation errors or database issues
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    