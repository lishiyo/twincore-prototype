"""API router for data ingestion endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from api.models import MessageIngest, StatusResponse
from ingestion.connectors.message_connector import MessageConnector

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/ingest",
    tags=["ingestion"],
    responses={404: {"description": "Not found"}},
)

# Define a dependency function to get MessageConnector instance
async def get_message_connector() -> MessageConnector:
    """
    This is just a placeholder function for FastAPI's dependency injection.
    The actual implementation will be provided via dependency_overrides in main.py.
    """
    # This will be overridden by app.dependency_overrides in main.py
    # It's never actually called in production
    raise NotImplementedError("Dependency not overridden")


@router.post(
    "/message",
    response_model=StatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a message",
    description="Ingest a message into the system, storing it in both Qdrant (vector DB) and Neo4j (graph DB)."
)
async def ingest_message(
    message: MessageIngest,
    message_connector: MessageConnector = Depends(get_message_connector)
) -> StatusResponse:
    """Ingest a message into the system.
    
    Args:
        message: The message data to ingest
        message_connector: Connector for ingesting messages (injected by FastAPI)
        
    Returns:
        StatusResponse: Status information about the ingestion
        
    Raises:
        HTTPException: If ingestion fails
    """
    try:
        logger.info(f"Request to ingest message from user {message.user_id}")
        
        # Convert the Pydantic model to a dictionary for the connector
        message_data = message.model_dump()
        
        # Ingest the message
        await message_connector.ingest_message(message_data)
        
        logger.info(f"Successfully ingested message from user {message.user_id}")
        return StatusResponse(status="accepted", message="Message received and queued for ingestion.")
        
    except ValueError as e:
        # Value error indicates invalid input
        error_msg = f"Invalid message data: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        # Any other exception indicates a server error
        error_msg = f"Error ingesting message: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": error_msg}
        ) 