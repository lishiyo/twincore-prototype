"""API Router for Ingestion Endpoints.

This module defines the API routes for ingesting various types of data
into the TwinCore system.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from api.models import IngestMessageRequest, IngestMessageResponse
from services.message_ingestion_service import MessageIngestionService, MessageIngestionServiceError

logger = logging.getLogger(__name__)

# Create router with version prefix
router = APIRouter(prefix="/v1/api/ingest", tags=["ingestion"])

# This function will be overridden by the app's dependency injection system
async def get_message_ingestion_service() -> MessageIngestionService:
    """Get the MessageIngestionService instance.
    
    This is a placeholder that will be overridden by the application's
    dependency injection system in main.py.
    """
    raise NotImplementedError("This dependency should be overridden by the application")


@router.post("/message", response_model=IngestMessageResponse)
async def ingest_message(
    request: IngestMessageRequest,
    message_ingestion_service: MessageIngestionService = Depends(get_message_ingestion_service)
) -> IngestMessageResponse:
    """Ingest a message into the system.
    
    Args:
        request: Message data to ingest
        message_ingestion_service: Dependency-injected service for message ingestion
        
    Returns:
        Response indicating success and message details
        
    Raises:
        HTTPException: If message ingestion fails
    """
    try:
        result = await message_ingestion_service.ingest_message(
            message_id=request.message_id,
            content=request.content,
            user_id=request.user_id,
            project_id=request.project_id,
            session_id=request.session_id,
            timestamp=request.timestamp,
            is_twin_interaction=request.is_twin_interaction,
            is_private=request.is_private,
            metadata=request.metadata
        )
        
        return IngestMessageResponse(
            message_id=result["message_id"],
            chunk_id=result["chunk_id"],
            timestamp=result["timestamp"],
            success=result["success"]
        )
    
    except MessageIngestionServiceError as e:
        logger.error(f"Failed to ingest message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest message: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error ingesting message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error ingesting message: {str(e)}") 