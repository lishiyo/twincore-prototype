"""Message Ingestion Service for handling message ingestion specifically.

This service specializes in the ingestion of messages into the system, 
building on the base IngestionService's functionality.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from services.ingestion_service import IngestionService, IngestionServiceError

logger = logging.getLogger(__name__)


class MessageIngestionServiceError(Exception):
    """Base exception for message ingestion service errors."""
    pass


class MessageIngestionService:
    """Service specializing in ingestion of messages into the system.
    
    This service builds on top of the base IngestionService, providing
    methods tailored specifically for handling message ingestion.
    """
    
    def __init__(
        self,
        ingestion_service: IngestionService
    ):
        """Initialize the message ingestion service with the base ingestion service.
        
        Args:
            ingestion_service: The base ingestion service to handle core ingestion logic
            
        Raises:
            ValueError: If ingestion_service is None
        """
        if ingestion_service is None:
            raise ValueError("IngestionService must be provided to MessageIngestionService")
        
        self._ingestion_service = ingestion_service
        logger.info("MessageIngestionService initialized")
    
    async def ingest_message(
        self,
        message_id: Optional[str],
        content: str,
        user_id: str,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        is_twin_interaction: bool = False,
        is_private: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Ingest a message into the system.
        
        Args:
            message_id: Optional unique identifier for the message (generated if not provided)
            content: The message text to ingest
            user_id: ID of the user who authored the message
            project_id: Optional project ID the message belongs to
            session_id: Optional session ID the message belongs to
            timestamp: Optional timestamp of message creation
            is_twin_interaction: Whether this is part of a twin interaction
            is_private: Whether this message is private to the user
            metadata: Optional additional metadata
            
        Returns:
            Dict containing the ingestion details including the message_id
            
        Raises:
            MessageIngestionServiceError: If message ingestion fails
        """
        try:
            # Generate message_id if not provided
            if message_id is None:
                message_id = str(uuid.uuid4())
            
            # Generate chunk_id for this message
            chunk_id = f"msg_{message_id}"
            
            # Use current timestamp if not provided
            if timestamp is None:
                timestamp = datetime.utcnow().isoformat()
            
            # Set source type as 'message'
            source_type = 'message'
            
            # Ingest the message as a chunk
            await self._ingestion_service.ingest_chunk(
                chunk_id=chunk_id,
                text_content=content,
                source_type=source_type,
                user_id=user_id,
                project_id=project_id, 
                session_id=session_id,
                message_id=message_id,
                timestamp=timestamp,
                is_twin_interaction=is_twin_interaction,
                is_private=is_private,
                metadata=metadata
            )
            
            logger.info(f"Successfully ingested message {message_id}")
            
            # Return information about the ingested message
            return {
                "message_id": message_id,
                "chunk_id": chunk_id,
                "timestamp": timestamp,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to ingest message: {str(e)}")
            raise MessageIngestionServiceError(f"Failed to ingest message: {str(e)}") 