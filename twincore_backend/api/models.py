"""Pydantic models for API request and response validation."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


# Common Models
class StatusResponse(BaseModel):
    """Basic status response model."""
    status: str
    message: Optional[str] = None


# Base Models for Content Types
class ContentBase(BaseModel):
    """Base model for any content to be ingested."""
    text: str = Field(..., description="The text content to be processed")
    source_type: str = Field(..., description="Type of source (e.g., message, document_chunk, transcript_snippet)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the content was created/uploaded")


# Ingestion Models
class MessageIngest(ContentBase):
    """Model for ingesting a message."""
    user_id: str = Field(..., description="ID of the user who sent the message")
    message_id: Optional[str] = Field(None, description="Unique ID for the message")
    project_id: Optional[str] = Field(None, description="ID of the associated project")
    session_id: Optional[str] = Field(None, description="ID of the associated session")
    is_twin_chat: bool = Field(False, description="Whether this is a private twin interaction")


class DocumentIngest(ContentBase):
    """Model for ingesting a document."""
    user_id: Optional[str] = Field(None, description="ID of the user who uploaded the document")
    doc_id: Optional[str] = Field(None, description="Unique ID for the document")
    doc_name: str = Field(..., description="Name of the document")
    project_id: Optional[str] = Field(None, description="ID of the associated project")
    session_id: Optional[str] = Field(None, description="ID of the associated session")
    is_private: bool = Field(False, description="Whether this is a private document")


# Retrieval Models
class ContextQuery(BaseModel):
    """Query parameters for retrieving context."""
    
    query_text: str = Field(..., description="The text to search for")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    project_id: Optional[str] = Field(None, description="Optional project ID filter")
    session_id: Optional[str] = Field(None, description="Optional session ID filter")
    include_twin_interactions: bool = Field(False, description="Whether to include twin interactions")

class PrivateMemoryQuery(BaseModel):
    """Query parameters for retrieving private memory."""
    
    query_text: str = Field(..., description="The text to search for")
    user_id: str = Field(..., description="User ID to retrieve private memory for")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    project_id: Optional[str] = Field(None, description="Optional project ID filter")
    session_id: Optional[str] = Field(None, description="Optional session ID filter")
    include_messages_to_twin: bool = Field(True, description="Whether to include user messages to the twin in results")


class RelatedContentQuery(BaseModel):
    """Query parameters for retrieving content related to a specific chunk."""
    
    chunk_id: str = Field(..., description="ID of the content chunk to find related content for")
    relationship_types: Optional[List[str]] = Field(None, description="Optional list of relationship types to traverse")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    include_private: bool = Field(False, description="Whether to include private content")
    max_depth: int = Field(2, ge=1, le=5, description="Maximum relationship traversal depth")
    include_twin_interactions: bool = Field(False, description="Whether to include twin interactions")

class TopicQuery(BaseModel):
    """Query parameters for retrieving content related to a specific topic."""
    
    topic_name: str = Field(..., description="Name of the topic to find related content for")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    user_id: Optional[str] = Field(None, description="Optional user ID filter")
    project_id: Optional[str] = Field(None, description="Optional project ID filter")
    session_id: Optional[str] = Field(None, description="Optional session ID filter")
    include_private: bool = Field(False, description="Whether to include private content")
    include_twin_interactions: bool = Field(False, description="Whether to include twin interactions")

class PreferenceQuery(BaseModel):
    """Model for querying user preferences."""
    user_id: str = Field(..., description="ID of the user whose preferences to query")
    decision_topic: str = Field(..., description="The topic to find preferences for")
    project_id: Optional[str] = Field(None, description="Optional project ID for context")
    session_id: Optional[str] = Field(None, description="Optional session ID for context")
    limit: int = Field(5, description="Maximum number of results to return")
    include_twin_interactions: bool = Field(True, description="Whether to include twin interactions")
    score_threshold: Optional[float] = Field(0.6, description="Minimum score threshold for results")


# Response Models
class ContentChunk(BaseModel):
    """Model for a content chunk with metadata."""
    
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    text: str = Field(..., description="Text content of the chunk")
    source_type: str = Field(..., description="Type of source (e.g., 'message', 'document')")
    timestamp: datetime = Field(..., description="Timestamp when the content was created/ingested")
    user_id: str = Field(..., description="ID of the user who created/owns the content")
    project_id: Optional[str] = Field(None, description="Project ID the content belongs to")
    session_id: Optional[str] = Field(None, description="Session ID the content belongs to")
    doc_id: Optional[str] = Field(None, description="Document ID for document chunks")
    doc_name: Optional[str] = Field(None, description="Document name for document chunks")
    message_id: Optional[str] = Field(None, description="Message ID for message chunks")
    score: Optional[float] = Field(None, description="Relevance score from search")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ChunksResponse(BaseModel):
    """Response model for endpoints returning multiple chunks."""
    
    chunks: List[ContentChunk] = Field(..., description="List of content chunks")
    total: int = Field(..., description="Total number of chunks returned")


class MessageRequest(BaseModel):
    """Request model for ingesting a message."""
    
    text: str = Field(..., description="Message text content")
    user_id: str = Field(..., description="ID of the user who created the message")
    project_id: Optional[str] = Field(None, description="Project ID the message belongs to")
    session_id: Optional[str] = Field(None, description="Session ID the message belongs to")
    timestamp: Optional[str] = Field(None, description="Timestamp when the message was created")
    is_twin_chat: bool = Field(False, description="Whether this is a twin interaction message")
    source_type: str = Field("message", description="Source type (default: 'message')")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MessageResponse(BaseModel):
    """Response model for message ingestion."""
    
    message_id: str = Field(..., description="ID of the ingested message")
    chunk_ids: List[str] = Field(..., description="IDs of the chunks created from the message")
    success: bool = Field(..., description="Whether the ingestion was successful")
    

class DocumentRequest(BaseModel):
    """Request model for ingesting a document."""
    
    content: str = Field(..., description="Document text content")
    title: str = Field(..., description="Document title")
    user_id: str = Field(..., description="ID of the user who uploaded the document")
    project_id: Optional[str] = Field(None, description="Project ID the document belongs to")
    session_id: Optional[str] = Field(None, description="Session ID the document belongs to")
    doc_type: str = Field("text", description="Document type (e.g., 'text', 'pdf')")
    timestamp: Optional[str] = Field(None, description="Timestamp when the document was created")
    is_private: bool = Field(False, description="Whether this is a private document")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DocumentResponse(BaseModel):
    """Response model for document ingestion."""
    
    doc_id: str = Field(..., description="ID of the ingested document")
    chunk_ids: List[str] = Field(..., description="IDs of the chunks created from the document")
    chunk_count: int = Field(..., description="Number of chunks created")
    success: bool = Field(..., description="Whether the ingestion was successful") 