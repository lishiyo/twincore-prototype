"""API Router for retrieval endpoints.

This module defines the FastAPI router for retrieving context, private memory,
and other semantic search operations against the twin's memory store.
"""

import logging
from typing import List, Optional, Dict, Any
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
    RelatedContentQuery,
    TopicQuery,
    PreferenceQuery,
)
from services.preference_service import PreferenceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/retrieve",
    tags=["retrieve"],
    responses={404: {"description": "Not found"}},
)


# Dependency injection functions
async def get_qdrant_dal():
    """Get QdrantDAL instance."""
    client = get_async_qdrant_client()
    dal = QdrantDAL(client)
    try:
        yield dal
    finally:
        # No cleanup needed for Qdrant client
        pass


async def get_neo4j_dal():
    """Get Neo4jDAL instance."""
    driver = await get_neo4j_driver()
    dal = Neo4jDAL(driver)
    try:
        yield dal
    finally:
        # No explicit cleanup needed as driver is managed by singleton
        pass


async def get_embedding_service():
    """Get EmbeddingService instance."""
    service = EmbeddingService()
    return service


async def get_message_connector(
    qdrant_dal: QdrantDAL = Depends(get_qdrant_dal),
    neo4j_dal: Neo4jDAL = Depends(get_neo4j_dal),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Get MessageConnector instance."""
    connector = MessageConnector(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service,
    )
    return connector


async def get_retrieval_service(
    qdrant_dal: QdrantDAL = Depends(get_qdrant_dal),
    neo4j_dal: Neo4jDAL = Depends(get_neo4j_dal),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    message_connector: MessageConnector = Depends(get_message_connector),
):
    """Get RetrievalService instance."""
    service = RetrievalService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service,
        message_connector=message_connector,
    )
    return service


async def get_preference_service(
    qdrant_dal: QdrantDAL = Depends(get_qdrant_dal),
    neo4j_dal: Neo4jDAL = Depends(get_neo4j_dal),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Get PreferenceService instance."""
    service = PreferenceService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service,
    )
    return service


# Dependency injection for RetrievalService
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


@router.get("/context", response_model=ChunksResponse)
async def retrieve_context(
    query_text: str,
    limit: int = 10,
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
    include_graph: bool = Query(False, description="Whether to include graph relationships"),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """Retrieve context-relevant information based on semantic search.
    
    This endpoint retrieves content chunks from the memory store based on
    semantic similarity to the provided query text, filtered by the specified
    project and session context.
    
    Args:
        query_text: The text to search for
        limit: Maximum number of results to return
        project_id: Optional filter by project ID
        session_id: Optional filter by session ID
        include_graph: Whether to include graph-based enrichments
        retrieval_service: The retrieval service dependency
    """
    try:
        if include_graph:
            results = await retrieval_service.retrieve_enriched_context(
                query_text=query_text,
                limit=limit,
                project_id=project_id,
                session_id=session_id
            )
        else:
            results = await retrieval_service.retrieve_context(
                query_text=query_text,
                limit=limit,
                project_id=project_id,
                session_id=session_id
            )
        
        # Convert to response model
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
                
            # Create chunk with properly mapped fields
            chunk = ContentChunk(
                chunk_id=result.get("chunk_id"),
                text=result.get("text_content"),  # Map text_content to text
                source_type=result.get("source_type"),
                timestamp=timestamp,
                user_id=result.get("user_id"),
                project_id=result.get("project_id"),
                session_id=result.get("session_id"),
                doc_id=result.get("doc_id", None),
                doc_name=result.get("doc_name", None),
                message_id=result.get("message_id", None),
                score=result.get("score", None),
            )
            
            # Add graph enrichment data to metadata if present
            if "project_context" in result:
                chunk.metadata["project_context"] = result["project_context"]
            
            if "session_participants" in result:
                chunk.metadata["session_participants"] = result["session_participants"]
                
            # Add relationship data if available
            if "outgoing_relationships" in result:
                chunk.metadata["outgoing_relationships"] = result["outgoing_relationships"]
            if "incoming_relationships" in result:
                chunk.metadata["incoming_relationships"] = result["incoming_relationships"]
            
            chunks.append(chunk)
        
        return ChunksResponse(chunks=chunks, total=len(chunks))
        
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving context: {str(e)}"
        )


@router.post("/private_memory", response_model=ChunksResponse)
async def retrieve_private_memory(
    query: PrivateMemoryQuery,
    include_graph: bool = False,
    retrieval_service: RetrievalService = Depends(get_retrieval_service_with_message_connector),
):
    """Retrieve a user's private memory based on semantic search.
    
    This endpoint retrieves content chunks from the user's private memory based on
    semantic similarity to the provided query text. It also ingests the query itself
    as a twin interaction, storing it in the memory store.
    
    Args:
        query: The private memory query parameters
        include_graph: Whether to include graph-based enrichments
        retrieval_service: The retrieval service dependency with message connector
    """
    try:
        # First call the private memory retrieval method
        results = await retrieval_service.retrieve_private_memory(
            query_text=query.query_text,
            user_id=query.user_id,
            limit=query.limit,
            project_id=query.project_id,
            session_id=query.session_id,
        )
        
        # If include_graph is True, enhance with graph data
        if include_graph and results:
            # Build a new list of enriched results
            enriched_results = []
            for result in results:
                # Add the basic result
                enriched_results.append(result)
                
                # For each result, we could optionally get related content
                if "chunk_id" in result:
                    try:
                        related = await retrieval_service.retrieve_related_content(
                            chunk_id=result["chunk_id"],
                            limit=3,  # Small limit to avoid overwhelming
                            include_private=True  # Include private since this is private memory
                        )
                        
                        # Add related items as separate results
                        enriched_results.extend(related)
                    except Exception as e:
                        logger.warning(f"Error enriching result with related content: {e}")
            
            # Replace the original results with enriched ones
            results = enriched_results
        
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
                
            # Create base chunk with standard fields
            chunk = ContentChunk(
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
            
            # Add relationship data if available from graph enrichment
            if "outgoing_relationships" in result:
                chunk.metadata["outgoing_relationships"] = result["outgoing_relationships"]
            if "incoming_relationships" in result:
                chunk.metadata["incoming_relationships"] = result["incoming_relationships"]
                
            chunks.append(chunk)
        
        return ChunksResponse(
            chunks=chunks,
            total=len(chunks),
        )
        
    except Exception as e:
        logger.error(f"Error retrieving private memory: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving private memory: {str(e)}")


@router.get("/related_content", response_model=ChunksResponse)
async def retrieve_related_content(
    chunk_id: str,
    limit: int = 10,
    include_private: bool = False,
    max_depth: int = 2,
    relationship_types: Optional[List[str]] = Query(None),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """Retrieve content related to a specific chunk through graph relationships.
    
    This endpoint uses Neo4j graph traversal to find content related to the
    specified chunk through relationships, without relying on vector similarity.
    
    Args:
        chunk_id: ID of the content chunk to find related content for
        limit: Maximum number of results to return
        include_private: Whether to include private content
        max_depth: Maximum relationship traversal depth
        relationship_types: Optional list of relationship types to traverse
        retrieval_service: The retrieval service dependency
    """
    try:
        # Log the received parameters for debugging
        logger.info(f"Retrieve related content request with chunk_id={chunk_id}, relationship_types={relationship_types}")
        
        # Call the graph-based retrieval method
        results = await retrieval_service.retrieve_related_content(
            chunk_id=chunk_id,
            relationship_types=relationship_types,
            limit=limit,
            include_private=include_private,
            max_depth=max_depth,
        )
        
        print(f"Retrieved {len(results)} related content items for chunk {chunk_id}")
        
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
                
            # Create chunk with relationship data in metadata
            chunk = ContentChunk(
                chunk_id=result.get("chunk_id"),
                text=result.get("text_content"),  # Map text_content to text
                source_type=result.get("source_type"),
                timestamp=timestamp,
                user_id=result.get("user_id"),
                project_id=result.get("project_id"),
                session_id=result.get("session_id"),
                doc_id=result.get("doc_id", None),
                doc_name=result.get("doc_name", None) if "doc_name" in result else None,
                message_id=result.get("message_id", None),
                score=result.get("score", None),
            )
            
            # Add relationship data from graph search
            if "outgoing_relationships" in result:
                chunk.metadata["outgoing_relationships"] = result["outgoing_relationships"]
            if "incoming_relationships" in result:
                chunk.metadata["incoming_relationships"] = result["incoming_relationships"]
                
            chunks.append(chunk)
        
        return ChunksResponse(
            chunks=chunks,
            total=len(chunks),
        )
        
    except Exception as e:
        logger.error(f"Error retrieving related content: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving related content: {str(e)}")


@router.get("/topic", response_model=ChunksResponse)
async def retrieve_by_topic(
    topic_name: str,
    limit: int = 10,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
    include_private: bool = False,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """Retrieve content related to a specific topic.
    
    This endpoint retrieves content chunks that mention or are related to
    a specific topic, ordered by relevance.
    
    Args:
        topic_name: Name of the topic to find related content for
        limit: Maximum number of results to return
        user_id: Optional filter by user ID
        project_id: Optional filter by project ID
        session_id: Optional filter by session ID
        include_private: Whether to include private content
        retrieval_service: The retrieval service dependency
    """
    try:
        results = await retrieval_service.retrieve_by_topic(
            topic_name=topic_name,
            limit=limit,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            include_private=include_private,
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
                
            # Create base chunk with standard fields
            chunk = ContentChunk(
                chunk_id=result.get("chunk_id"),
                text=result.get("text_content"),
                source_type=result.get("source_type"),
                timestamp=timestamp,
                user_id=result.get("user_id"),
                project_id=result.get("project_id"),
                session_id=result.get("session_id"),
                score=result.get("score"),
            )
            
            # Add topic data as metadata
            if "topic" in result:
                chunk.metadata["topic"] = result["topic"]
                
            chunks.append(chunk)
        
        return ChunksResponse(
            chunks=chunks,
            total=len(chunks),
        )
        
    except Exception as e:
        logger.error(f"Error retrieving topic content: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving topic content: {str(e)}")


# Add the preference endpoint
@router.get("/preferences", response_model=Dict[str, Any])
async def retrieve_preferences(
    user_id: str,
    decision_topic: str,
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 5,
    score_threshold: Optional[float] = 0.6,
    preference_service: PreferenceService = Depends(get_preference_service)
):
    """Retrieve the user's preference statements related to a specific decision topic.
    
    This endpoint combines both vector search and graph relationships to find 
    user statements expressing preferences about a specific topic or decision.
    
    Args:
        user_id: ID of the user whose preferences to query
        decision_topic: The topic to find preferences for (e.g., "dark mode", "notification settings")
        project_id: Optional project ID for context
        session_id: Optional session ID for context
        limit: Maximum number of preference statements to return
        score_threshold: Optional score threshold for vector search
        preference_service: The preference service dependency
    
    Returns:
        A dictionary containing preference statements and metadata
    """
    try:
        preference_data = await preference_service.query_user_preference(
            user_id=user_id,
            decision_topic=decision_topic,
            project_id=project_id,
            session_id=session_id,
            limit=limit,
            score_threshold=score_threshold
        )
        
        return preference_data
        
    except Exception as e:
        logger.error(f"Error retrieving user preferences: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user preferences: {str(e)}"
        ) 