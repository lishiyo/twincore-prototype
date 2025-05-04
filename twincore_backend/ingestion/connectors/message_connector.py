"""Message Connector for handling message data ingestion.

This connector specializes in handling message data ingestion, using
the core IngestionService for actual data storage operations.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


class MessageConnector:
    """Connector for ingesting message data into the system.
    
    This connector specializes in handling message-specific ingestion
    logic, leveraging the core IngestionService for actual storage.
    """
    
    def __init__(self, ingestion_service: IngestionService):
        """Initialize the message connector.
        
        Args:
            ingestion_service: Core service for handling data storage
        
        Raises:
            ValueError: If the ingestion_service is None
        """
        if ingestion_service is None:
            raise ValueError("IngestionService must be provided to MessageConnector")
        
        self._ingestion_service = ingestion_service
        logger.info("MessageConnector initialized")
    
    async def ingest_message(self, message_data: Dict[str, Any]) -> Optional[str]:
        """Ingest a message and return the generated chunk ID.
        
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
                - is_private: Whether the message is private
                
        Returns:
            chunk_id: The ID of the chunk that was ingested
            
        Raises:
            ValueError: If required fields are missing
        """
        try:
            # Try to extract required fields
            text = message_data.get("text")
            user_id = message_data.get("user_id")
            if not text or not user_id:
                logger.error(f"Missing required fields for message ingestion: {message_data}")
                raise ValueError("Missing required fields for message ingestion")
                
            # Extract or generate optional fields
            timestamp = message_data.get("timestamp", datetime.now().isoformat())
            #  timestamp = message_data.get("timestamp")
        
            if timestamp is not None and isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
            
            # For testing, we might want to override message_id rather than generate
            message_id = message_data.get("message_id", f"{uuid.uuid4()}")
            source_type = message_data.get("source_type", "message")
            
            # Flag for twin interaction - when user is directly talking to their twin
            is_twin_chat = message_data.get("is_twin_chat", False)
            
            # For privacy control - respect explicit is_private if provided, otherwise derive from is_twin_chat
            is_private = message_data.get("is_private")
            if is_private is None:
                # Default behavior: twin chat messages are private by default
                is_private = is_twin_chat
            
            # Context IDs (optional)
            project_id = message_data.get("project_id")
            session_id = message_data.get("session_id")
            
            # Generate a UUID for the chunk
            chunk_id = str(uuid.uuid4())
        
            logger.info(f"Ingesting message from user {user_id}, message_id: {message_id}, chunk_id: {chunk_id}")
        
            # Use the service to ingest the actual chunk
            chunk_id = await self._ingestion_service.ingest_chunk(
                chunk_id=chunk_id,
                text_content=text,
                user_id=user_id,
                source_type=source_type,
                is_twin_interaction=is_twin_chat,
                is_private=is_private,
                timestamp=timestamp,
                project_id=project_id,
                session_id=session_id,
                message_id=message_id
            )
            
            logger.info(f"Successfully ingested message {message_id}")
            return chunk_id
            
        except Exception as e:
            logger.error(f"Failed to ingest message: {str(e)}")
            raise 