"""Admin router for managing backend administration functions.

This router provides endpoints for system administration tasks like
data seeding that should not be exposed to regular users.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Body, status
from typing import Dict, Any, Optional

from api.models import StatusResponse
from services.data_seeder_service import DataSeederService, DataSeederServiceError
from services.data_management_service import DataManagementService, DataManagementServiceError
from pydantic import BaseModel, Field
from datetime import datetime

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
    prefix="/v1/admin/api",
    tags=["admin"],
    responses={401: {"description": "Unauthorized"}}
)

# Dependency to get the DataSeederService (will be implemented in main.py)
async def get_data_seeder_service() -> DataSeederService:
    """Dependency to get the DataSeederService instance."""
    # This will be replaced in main.py with the actual dependency
    pass

# Dependency to get the DataManagementService (will be implemented in main.py)
async def get_data_management_service() -> DataManagementService:
    """Dependency to get the DataManagementService instance."""
    # This will be replaced in main.py with the actual dependency
    pass

@router.post("/seed_data", status_code=202)
async def seed_data(
    seeder_service: DataSeederService = Depends(get_data_seeder_service)
) -> Dict[str, Any]:
    """Seed the system with initial mock data.
    
    This endpoint initializes the system with predefined mock data
    for testing and demonstration purposes.
    
    Returns:
        JSON object containing the counts of seeded items by type.
    
    Raises:
        HTTPException: If seeding operation fails
    """
    try:
        result = await seeder_service.seed_initial_data()
        return {
            "status": "success",
            "message": f"Successfully seeded {result['total']} items",
            "data": result
        }
    except DataSeederServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear_data", status_code=202)
async def clear_data(
    management_service: DataManagementService = Depends(get_data_management_service)
) -> Dict[str, Any]:
    """Clear all data from the system.
    
    This endpoint deletes all data from both Qdrant and Neo4j databases.
    This is useful for testing, development, or resetting the system to a clean state.
    
    Returns:
        JSON object containing confirmation of cleared data.
    
    Raises:
        HTTPException: If clearing operation fails
    """
    try:
        result = await management_service.clear_all_data()
        return {
            "status": "success",
            "message": "All data successfully cleared",
            "data": result
        }
    except DataManagementServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/documents/{doc_id}/metadata",
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
        success = await management_service.update_document_metadata(
            doc_id=doc_id,
            source_uri=update_data.source_uri,
            metadata=update_data.metadata,
            user_id=update_data.user_id,
            timestamp=update_data.timestamp.isoformat() if update_data.timestamp else None
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Document with ID {doc_id} not found."
            )
            
        return StatusResponse(
            status="success", 
            message=f"Metadata updated successfully for document {doc_id}."
        )
        
    except DataManagementServiceError as e:
        # Service errors might include validation errors or database issues
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        # Catch unexpected errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}") 