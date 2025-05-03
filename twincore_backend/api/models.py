"""Pydantic models for API request and response validation."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


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
    """Model for querying context."""
    query_text: str = Field(..., description="The query text to search for")
    project_id: str = Field(..., description="ID of the project to search within")
    session_id: str = Field(..., description="ID of the session to search within")
    limit: int = Field(10, description="Maximum number of results to return")


class PrivateMemoryQuery(BaseModel):
    """Model for querying private user memory."""
    user_id: str = Field(..., description="ID of the user whose memory to search")
    query_text: str = Field(..., description="The query text to search for")
    project_id: Optional[str] = Field(None, description="Optional project ID to scope the search")
    session_id: Optional[str] = Field(None, description="Optional session ID to scope the search")
    limit: int = Field(10, description="Maximum number of results to return")


class PreferenceQuery(BaseModel):
    """Model for querying user preferences."""
    user_id: str = Field(..., description="ID of the user whose preferences to query")
    decision_topic: str = Field(..., description="The topic to find preferences for")
    project_id: Optional[str] = Field(None, description="Optional project ID for context")
    session_id: Optional[str] = Field(None, description="Optional session ID for context")
    limit: int = Field(5, description="Maximum number of results to return")


# Response Models
class ContentChunk(BaseModel):
    """A single chunk of content with metadata."""
    chunk_id: str = Field(..., description="Unique ID for this chunk")
    text: str = Field(..., description="The text content of this chunk")
    source_type: str = Field(..., description="Type of source (message, document_chunk, etc.)")
    timestamp: datetime = Field(..., description="When the content was created/uploaded")
    user_id: Optional[str] = Field(None, description="ID of the user associated with this chunk")
    project_id: Optional[str] = Field(None, description="ID of the associated project")
    session_id: Optional[str] = Field(None, description="ID of the associated session")
    doc_id: Optional[str] = Field(None, description="ID of the associated document")
    doc_name: Optional[str] = Field(None, description="Name of the associated document")
    message_id: Optional[str] = Field(None, description="ID of the associated message")
    score: Optional[float] = Field(None, description="Relevance score from the search")


class ChunksResponse(BaseModel):
    """Response model for retrieval endpoints."""
    chunks: List[ContentChunk] = Field(..., description="List of content chunks")
    total: int = Field(..., description="Total number of results found")


# Request Models
class SeedDataRequest(BaseModel):
    """Request model for seeding data."""
    force: bool = Field(default=False, description="Force re-seeding even if data exists")


class ClearDataRequest(BaseModel):
    """Request model for clearing data."""
    confirm: bool = Field(description="Confirmation to clear all data")


class IngestMessageRequest(BaseModel):
    """Request model for ingesting a message."""
    message_id: Optional[str] = Field(default=None, description="Unique identifier for the message (optional)")
    content: str = Field(description="The message text content")
    user_id: str = Field(description="ID of the user who authored the message")
    project_id: Optional[str] = Field(default=None, description="Project ID the message belongs to")
    session_id: Optional[str] = Field(default=None, description="Session ID the message belongs to")
    timestamp: Optional[str] = Field(default=None, description="Timestamp of message creation")
    is_twin_interaction: bool = Field(default=False, description="Whether this is part of a twin interaction")
    is_private: bool = Field(default=False, description="Whether this message is private to the user")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# Response Models
class SeedDataResponse(BaseModel):
    """Response model for seeding data."""
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Status message")


class ClearDataResponse(BaseModel):
    """Response model for clearing data."""
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Status message")


class IngestMessageResponse(BaseModel):
    """Response model for ingesting a message."""
    message_id: str = Field(description="Unique identifier of the message")
    chunk_id: str = Field(description="Unique identifier of the chunk")
    timestamp: str = Field(description="Timestamp when the message was ingested")
    success: bool = Field(description="Whether the operation was successful") 