"""Document Connector for handling document data ingestion.

This connector specializes in handling document data ingestion, using
the core IngestionService for actual data storage operations and
the TextChunker for splitting documents into chunks.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.ingestion_service import IngestionService
from ingestion.processors.text_chunker import TextChunker
from dal.interfaces import INeo4jDAL # Import Neo4j DAL interface

logger = logging.getLogger(__name__)


class DocumentConnector:
    """Connector for ingesting document data into the system.
    
    This connector specializes in handling document-specific ingestion
    logic, including chunking of documents and maintaining the document
    structure in both Qdrant and Neo4j.
    """
    
    def __init__(
        self,
        ingestion_service: IngestionService,
        text_chunker: TextChunker
    ):
        """Initialize the document connector.
        
        Args:
            ingestion_service: Core service for handling data storage
            text_chunker: Processor for splitting text into chunks
        
        Raises:
            ValueError: If any required dependency is None
        """
        if ingestion_service is None:
            raise ValueError("IngestionService must be provided to DocumentConnector")
        if text_chunker is None:
            raise ValueError("TextChunker must be provided to DocumentConnector")
            
        self._ingestion_service = ingestion_service
        self._text_chunker = text_chunker
        logger.info("DocumentConnector initialized")
    
    async def ingest_document(
        self, 
        document_data: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> bool:
        """Ingest a document into the system, chunking it if necessary.
        
        Args:
            document_data: Dictionary containing document data with the following fields:
                - text: The document text content
                - source_type: Should be "document"
                - doc_name: Name of the document
                - user_id: Optional ID of the user who uploaded the document
                - doc_id: Optional ID for the document (will be generated if not provided)
                - project_id: Optional project ID
                - session_id: Optional session ID
                - is_private: Whether this is a private document
                - timestamp: Optional timestamp (will use current time if not provided)
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
                
        Returns:
            bool: True if ingestion was successful
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        if "text" not in document_data:
            raise ValueError("Document text is required")
        if "doc_name" not in document_data:
            raise ValueError("doc_name is required for document ingestion")
        
        # Extract fields with defaults
        text = document_data["text"]
        source_type = document_data.get("source_type", "document")
        doc_name = document_data["doc_name"]
        user_id = document_data.get("user_id")
        doc_id = document_data.get("doc_id") or str(uuid.uuid4())
        project_id = document_data.get("project_id")
        session_id = document_data.get("session_id")
        is_private = document_data.get("is_private", False)
        timestamp = document_data.get("timestamp")
        
        if timestamp is not None and isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        
        logger.info(f"Ingesting document {doc_id} with name {doc_name}")
        
        try:
            # Chunk the document text
            chunks = self._text_chunker.chunk_text(
                text=text,
                chunk_size=chunk_size,
                overlap=chunk_overlap,
                respect_paragraphs=True
            )
            
            if not chunks:
                logger.warning(f"Document {doc_id} produced no chunks, possibly empty")
                chunks = [text]  # Use the original text as a single chunk
            
            logger.info(f"Document {doc_id} split into {len(chunks)} chunks")
            
            # Process each chunk
            for i, chunk_text in enumerate(chunks):
                # Generate a UUID for each chunk
                chunk_id = str(uuid.uuid4())
                
                # Create chunk name with index for better identification
                chunk_metadata = {
                    "original_document": doc_name,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                
                # Use "document_chunk" as source type for chunks
                chunk_source_type = "document_chunk"
                
                await self._ingestion_service.ingest_chunk(
                    chunk_id=chunk_id,
                    text_content=chunk_text,
                    source_type=chunk_source_type,
                    user_id=user_id,
                    project_id=project_id,
                    session_id=session_id,
                    doc_id=doc_id,
                    doc_name=doc_name,
                    timestamp=timestamp,
                    is_twin_interaction=False,  # Documents are not twin interactions
                    is_private=is_private,
                    metadata=chunk_metadata
                )
            
            logger.info(f"Successfully ingested document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest document: {str(e)}")
            raise 

    async def ingest_chunk(
        self,
        chunk_data: Dict[str, Any]
    ) -> bool:
        """Ingest a single chunk, typically a transcript snippet.

        Ensures the parent document exists in Neo4j and then calls the
        IngestionService to handle embedding and storage.

        Args:
            chunk_data: Dictionary containing chunk data with fields:
                - user_id: ID of the speaker/author
                - session_id: Session context ID
                - doc_id: Consistent ID of the parent Document
                - text: The utterance/chunk text content
                - timestamp: Time the utterance occurred
                - project_id: (Optional) Project context ID
                - chunk_id: (Optional) Unique ID for this specific chunk from source

        Returns:
            bool: True if ingestion was successful.

        Raises:
            ValueError: If required fields are missing.
            IngestionServiceError: If the underlying ingestion fails.
        """
        # Validate required fields
        required_fields = ["user_id", "session_id", "doc_id", "text", "timestamp"]
        for field in required_fields:
            if field not in chunk_data or chunk_data[field] is None:
                raise ValueError(f"Missing required field in chunk_data: {field}")

        doc_id = chunk_data["doc_id"]
        session_id = chunk_data["session_id"]
        project_id = chunk_data.get("project_id")
        timestamp = chunk_data["timestamp"]
        user_id = chunk_data["user_id"] # Needed for parent doc creation context
        
        # Use provided chunk_id or generate a new one
        chunk_id_to_use = chunk_data.get("chunk_id") or str(uuid.uuid4())

        logger.info(f"Ingesting chunk {chunk_id_to_use} for document {doc_id}")

        try:
            doc_name = chunk_data.get("metadata", {}).get("doc_name", f"Transcript Document {doc_id}")

            # 2. Call IngestionService to handle embedding and storage
            # Pass all relevant fields from chunk_data
            await self._ingestion_service.ingest_chunk(
                chunk_id=chunk_id_to_use,
                text_content=chunk_data["text"],
                source_type="transcript_snippet", # Specific type for the chunk
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                doc_id=doc_id,
                # message_id=None, # Not applicable here usually
                doc_name=doc_name, # Pass the potentially generated name
                timestamp=timestamp,
                is_twin_interaction=False,
                is_private=False, # Transcripts usually not private by default
                metadata=chunk_data.get("metadata") # Pass optional metadata
            )

            logger.info(f"Successfully ingested chunk {chunk_id_to_use}")
            return True

        except Exception as e:
            logger.error(f"Failed to ingest chunk {chunk_id_to_use}: {str(e)}")
            # Re-raise as IngestionServiceError or a connector-specific error?
            # For now, re-raising the original exception might be okay.
            raise 