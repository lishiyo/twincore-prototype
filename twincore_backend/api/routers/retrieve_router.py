"""API Router for retrieval endpoints.

This module defines the FastAPI router for retrieving context, private memory,
and other semantic search operations against the twin's memory store.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import UUID4

from services.retrieval_service import RetrievalService
from services.ingestion_service import IngestionService
from services.embedding_service import EmbeddingService
from ingestion.connectors.message_connector import MessageConnector
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from api.models import (
    ContextQuery,
    PrivateMemoryQuery,
    ContentChunk,
    ChunksResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/retrieve",
    tags=["retrieve"],
    responses={404: {"description": "Not found"}},
)


# Dependency injection for RetrievalService
async def get_retrieval_service() -> RetrievalService:
    """Get an instance of RetrievalService with injected dependencies.
    
    This function follows the dependency injection pattern to create a new
    RetrievalService instance for each request with fresh database connections.
    """
    qdrant_client = get_async_qdrant_client()
    neo4j_driver = await get_neo4j_driver()
    
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    # Return a fresh instance for this request
    return RetrievalService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service,
    )


# Enhanced dependency injection including MessageConnector for private memory
async def get_retrieval_service_with_message_connector() -> RetrievalService:
    """Get an instance of RetrievalService including MessageConnector for private memory.
    
    This extended dependency function creates a RetrievalService that also has
    access to MessageConnector, needed for private memory retrieval.
    """
    qdrant_client = get_async_qdrant_client()
    neo4j_driver = await get_neo4j_driver()
    
    qdrant_dal = QdrantDAL(client=qdrant_client)
    neo4j_dal = Neo4jDAL(driver=neo4j_driver)
    embedding_service = EmbeddingService()
    
    # Create IngestionService for the connector
    ingestion_service = IngestionService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service,
    )
    
    # Create MessageConnector using IngestionService
    message_connector = MessageConnector(ingestion_service=ingestion_service)
    
    # Return a fresh instance for this request
    return RetrievalService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service,
        message_connector=message_connector,
    )


@router.post("/context", response_model=ChunksResponse)
async def retrieve_context(
    query: ContextQuery,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """Retrieve context-relevant information based on semantic search.
    
    This endpoint retrieves content chunks from the memory store based on
    semantic similarity to the provided query text, filtered by the specified
    project and session context.
    """
    try:
        # Call the retrieval service with the query parameters
        results = await retrieval_service.retrieve_context(
            query_text=query.query_text,
            limit=query.limit,
            project_id=query.project_id,
            session_id=query.session_id,
        )
        
        # Convert to ContentChunk model objects
        chunks = []
        for result in results:
            # Extract timestamp and ensure it's a proper datetime
            timestamp = result.get("timestamp")
            if isinstance(timestamp, (int, float)):
                # Convert Unix timestamp to datetime
                timestamp = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                # Try parsing ISO format
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
                
            chunks.append(
                ContentChunk(
                    chunk_id=result.get("chunk_id"),
                    text=result.get("text_content"),
                    source_type=result.get("source_type"),
                    timestamp=timestamp,
                    user_id=result.get("user_id"),
                    project_id=result.get("project_id"),
                    session_id=result.get("session_id"),
                    doc_id=result.get("doc_id"),
                    doc_name=result.get("doc_name") if "doc_name" in result else None,
                    message_id=result.get("message_id"),
                    score=result.get("score"),
                )
            )
        
        return ChunksResponse(
            chunks=chunks,
            total=len(chunks),
        )
        
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving context: {str(e)}")


@router.post("/private_memory", response_model=ChunksResponse)
async def retrieve_private_memory(
    query: PrivateMemoryQuery,
    retrieval_service: RetrievalService = Depends(get_retrieval_service_with_message_connector),
):
    """Retrieve a user's private memory based on semantic search.
    
    This endpoint retrieves content chunks from the user's private memory based on
    semantic similarity to the provided query text. It also ingests the query itself
    as a twin interaction, storing it in the memory store.
    """
    try:
        # Call the private memory retrieval method
        results = await retrieval_service.retrieve_private_memory(
            query_text=query.query_text,
            user_id=query.user_id,
            limit=query.limit,
            project_id=query.project_id,
            session_id=query.session_id,
        )
        
        # Convert to ContentChunk model objects (similar to context endpoint)
        chunks = []
        for result in results:
            # Extract timestamp and ensure it's a proper datetime
            timestamp = result.get("timestamp")
            if isinstance(timestamp, (int, float)):
                # Convert Unix timestamp to datetime
                timestamp = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                # Try parsing ISO format
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
                
            chunks.append(
                ContentChunk(
                    chunk_id=result.get("chunk_id"),
                    text=result.get("text_content"),
                    source_type=result.get("source_type"),
                    timestamp=timestamp,
                    user_id=result.get("user_id"),
                    project_id=result.get("project_id"),
                    session_id=result.get("session_id"),
                    doc_id=result.get("doc_id"),
                    doc_name=result.get("doc_name") if "doc_name" in result else None,
                    message_id=result.get("message_id"),
                    score=result.get("score"),
                )
            )
        
        return ChunksResponse(
            chunks=chunks,
            total=len(chunks),
        )
        
    except Exception as e:
        logger.error(f"Error retrieving private memory: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving private memory: {str(e)}") 