"""Message Ingestion Service for handling message data ingestion.

This service specializes in handling message data ingestion, using
the core IngestionService for actual data storage operations.
"""

import logging
import uuid
import random
from datetime import datetime
from typing import Any, Dict, Optional

from services.ingestion_service import IngestionService, IngestionServiceError

logger = logging.getLogger(__name__)


class MessageIngestionService:
    """Service for ingesting message data into the system.
    
    This service specializes in handling message-specific ingestion
    logic, leveraging the core IngestionService for actual storage.
    """
    
    def __init__(self, ingestion_service: IngestionService):
        """Initialize the message ingestion service.
        
        Args:
            ingestion_service: Core service for handling data storage
        
        Raises:
            ValueError: If the ingestion_service is None
        """
        if ingestion_service is None:
            raise ValueError("IngestionService must be provided to MessageIngestionService")
        
        self._ingestion_service = ingestion_service
        logger.info("MessageIngestionService initialized")
    
    async def ingest_message(self, message_data: Dict[str, Any]) -> bool:
        """Ingest a message into the system.
        
        Args:
            message_data: Dictionary containing message data with the following fields:
                - text: The message text content
                - source_type: Should be "message"
                - user_id: ID of the user who sent the message
                - message_id: Optional ID for the message (will be generated if not provided)
                - project_id: Optional project ID
                - session_id: Optional session ID
                - is_twin_chat: Whether this is a private twin interaction
                - timestamp: Optional timestamp (will use current time if not provided)
                
        Returns:
            bool: True if ingestion was successful
            
        Raises:
            ValueError: If required fields are missing
            IngestionServiceError: If ingestion fails
        """
        # Validate required fields
        if "text" not in message_data:
            raise ValueError("Message text is required")
        if "user_id" not in message_data:
            raise ValueError("user_id is required for message ingestion")
        
        # Extract fields with defaults
        text = message_data["text"]
        source_type = message_data.get("source_type", "message")
        user_id = message_data["user_id"]
        message_id = message_data.get("message_id") or str(uuid.uuid4())
        project_id = message_data.get("project_id")
        session_id = message_data.get("session_id")
        is_twin_chat = message_data.get("is_twin_chat", False)
        timestamp = message_data.get("timestamp")
        
        if timestamp is not None and isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        
        # Generate a UUID for the chunk - using UUID instead of random int
        chunk_id = str(uuid.uuid4())
        
        logger.info(f"Ingesting message from user {user_id}, message_id: {message_id}")
        
        try:
            # Use the ingestion service to store the message
            await self._ingestion_service.ingest_chunk(
                chunk_id=chunk_id,
                text_content=text,
                source_type=source_type,
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                message_id=message_id,
                timestamp=timestamp,
                is_twin_interaction=is_twin_chat,
                is_private=is_twin_chat  # Private if it's a twin chat
            )
            
            logger.info(f"Successfully ingested message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest message: {str(e)}")
            raise 