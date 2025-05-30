"""API router for data ingestion endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from api.models import MessageIngest, DocumentIngest, StatusResponse, IngestChunkRequest
from ingestion.connectors.message_connector import MessageConnector
from ingestion.connectors.document_connector import DocumentConnector

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

# Define a dependency function to get DocumentConnector instance
async def get_document_connector() -> DocumentConnector:
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


@router.post(
    "/document",
    response_model=StatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a document",
    description="Ingest a document into the system, splitting it into chunks and storing in both Qdrant (vector DB) and Neo4j (graph DB)."
)
async def ingest_document(
    document: DocumentIngest,
    document_connector: DocumentConnector = Depends(get_document_connector)
) -> StatusResponse:
    """Ingest a document into the system.
    
    The document will be split into chunks, embedded, and stored in both Qdrant and Neo4j.
    The document structure will be preserved in Neo4j.
    
    Args:
        document: The document data to ingest
        document_connector: Connector for ingesting documents (injected by FastAPI)
        
    Returns:
        StatusResponse: Status information about the ingestion
        
    Raises:
        HTTPException: If ingestion fails
    """
    try:
        logger.info(f"Request to ingest document: {document.doc_name}")
        
        # Convert the Pydantic model to a dictionary for the connector
        document_data = document.model_dump()
        
        # Ingest the document
        await document_connector.ingest_document(document_data)
        
        logger.info(f"Successfully ingested document: {document.doc_name}")
        return StatusResponse(
            status="accepted", 
            message="Document received and queued for ingestion."
        )
        
    except ValueError as e:
        # Value error indicates invalid input
        error_msg = f"Invalid document data: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        # Any other exception indicates a server error
        error_msg = f"Error ingesting document: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": error_msg}
        )

@router.post(
    "/chunk",
    response_model=StatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a text chunk",
    description="Ingest a single text chunk, typically a transcript snippet, associated with a parent document."
)
async def ingest_chunk(
    chunk: IngestChunkRequest,
    document_connector: DocumentConnector = Depends(get_document_connector)
) -> StatusResponse:
    """Ingest a single text chunk (e.g., transcript utterance).

    Ensures the parent document exists in Neo4j and stores the chunk
    in Qdrant and Neo4j.

    Args:
        chunk: The chunk data to ingest.
        document_connector: Connector for handling document/chunk ingestion.

    Returns:
        StatusResponse: Status information about the ingestion.

    Raises:
        HTTPException: If ingestion fails due to bad data or server error.
    """
    try:
        logger.info(f"Request to ingest chunk for document {chunk.doc_id}")
        
        # Convert Pydantic model to dictionary
        chunk_data = chunk.model_dump()
        
        # Call the connector's ingest_chunk method
        await document_connector.ingest_chunk(chunk_data)
        
        logger.info(f"Successfully queued chunk {chunk_data.get('chunk_id', 'N/A')} for document {chunk.doc_id}")
        return StatusResponse(
            status="accepted",
            message="Chunk received and queued for ingestion."
        )

    except ValueError as e:
        error_msg = f"Invalid chunk data: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    except Exception as e:
        error_msg = f"Error ingesting chunk: {str(e)}"
        logger.error(error_msg, exc_info=True) # Log traceback for internal errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "An internal server error occurred during chunk ingestion."}
        ) 