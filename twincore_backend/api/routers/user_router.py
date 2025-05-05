import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, Path

from api.models import ChunksResponse, ContentChunk, PrivateMemoryQuery # Import PrivateMemoryQuery
from services.retrieval_service import RetrievalService
from services.preference_service import PreferenceService
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from api.routers.retrieve_router import get_retrieval_service, get_qdrant_dal, get_neo4j_dal, get_embedding_service, get_retrieval_service_with_message_connector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/users", tags=["User Retrieval"])

# Dependency injection
async def get_preference_service(
    qdrant_dal: QdrantDAL = Depends(get_qdrant_dal),
    neo4j_dal: Neo4jDAL = Depends(get_neo4j_dal),
    embedding_service = Depends(get_embedding_service),
):
    """Get PreferenceService instance."""
    service = PreferenceService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service,
    )
    return service

@router.get(
    "/{user_id}/context",
    response_model=ChunksResponse, 
    summary="Retrieve User Context (Read-Only)",
    description="Retrieves relevant text chunks associated specifically with a given user based on a semantic query. "
                "This searches across all user's relevant data (private docs, group messages, twin interactions, etc.), "
                "optionally filtered by project/session scope. This endpoint is read-only and performs no ingestion."
)
async def get_user_context(
    user_id: str = Path(..., description="The ID of the user whose context is being queried."),
    query_text: str = Query(..., description="The natural language query for semantic search."),
    session_id: Optional[str] = Query(None, description="Scope: Further filter results by session."),
    project_id: Optional[str] = Query(None, description="Scope: Further filter results by project."),
    limit: int = Query(10, description="Maximum number of chunks to return."),
    include_messages_to_twin: bool = Query(True, description="If true, results will include chunks where `is_twin_interaction` is true (i.e., user queries to the twin). Set to false to exclude these interactions."),
    include_private: bool = Query(True, description="If true, include user's private docs in the query."),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
) -> ChunksResponse:
    """API endpoint to retrieve context specific to a user."""
    try:
        logger.info(f"Received request for user context: user_id={user_id}, query='{query_text}'")
        results = await retrieval_service.retrieve_user_context(
            user_id=user_id,
            query_text=query_text,
            session_id=session_id,
            project_id=project_id,
            limit=limit,
            include_messages_to_twin=include_messages_to_twin,
            include_private=include_private,
        )
        
        # Convert DAL results to ContentChunk model instances
        chunks = []
        for result in results:
            # Handle timestamp conversion (like in retrieve_router)
            timestamp = result.get("timestamp")
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    logger.warning(f"Could not parse timestamp '{timestamp}' for chunk {result.get('chunk_id')}. Using current time.")
                    timestamp = datetime.now()
            elif timestamp is None:
                 logger.warning(f"Missing timestamp for chunk {result.get('chunk_id')}. Using current time.")
                 timestamp = datetime.now()
            # If it's already a datetime, keep it.
                 
            # Instantiate ContentChunk, mapping text_content to text
            try:
                chunk_model = ContentChunk(
                    chunk_id=result.get("chunk_id"),
                    text=result.get("text_content"), # Explicit mapping
                    source_type=result.get("source_type"),
                    timestamp=timestamp,
                    user_id=result.get("user_id"), # Pydantic will raise error if missing
                    project_id=result.get("project_id"),
                    session_id=result.get("session_id"),
                    doc_id=result.get("doc_id"),
                    doc_name=result.get("doc_name"),
                    message_id=result.get("message_id"),
                    score=result.get("score"),
                    metadata=result.get("metadata", {}) # Use payload directly if it exists
                )
                chunks.append(chunk_model)
            except Exception as model_error: # Catch validation errors during model creation
                 logger.error(f"Validation failed for chunk {result.get('chunk_id')}: {model_error}. Raw data: {result}")
                 # Optionally skip this chunk or raise a different error
                 # continue 
                 
        return ChunksResponse(chunks=chunks, total=len(chunks))
    except Exception as e:
        logger.exception(f"Error retrieving user context for user_id={user_id}: {e}")
        # Consider specific exceptions for 404 Not Found if user_id doesn't exist
        raise HTTPException(status_code=500, detail="Internal server error retrieving user context.") 

@router.get(
    "/{user_id}/preferences",
    response_model=Dict[str, Any],
    summary="Retrieve User Preferences",
    description="Retrieves known preferences for a specific user, filtered by a required decision topic and optionally by project/session scope. Combines explicit statements, inferred preferences, and relevant chat history."
)
async def get_user_preferences(
    user_id: str = Path(..., description="The ID of the user whose preferences are being queried."),
    decision_topic: str = Query(..., description="The topic to find preferences for (e.g., 'dark mode', 'notification settings')"),
    project_id: Optional[str] = Query(None, description="Scope: Filter preferences relevant to a specific project."),
    session_id: Optional[str] = Query(None, description="Scope: Filter preferences relevant to a specific session."),
    limit: int = Query(5, description="Maximum number of relevant statements/items to return."),
    score_threshold: Optional[float] = Query(0.6, description="Minimum score for vector search results to be considered."),
    include_messages_to_twin: bool = Query(True, description="If false, results from the vector search portion will exclude chunks where is_twin_interaction is true."),
    preference_service: PreferenceService = Depends(get_preference_service)
) -> Dict[str, Any]:
    """API endpoint to retrieve preferences for a specific user."""
    try:
        logger.info(f"Received request for user preferences: user_id={user_id}, topic='{decision_topic}'")
        preference_data = await preference_service.query_user_preference(
            user_id=user_id,
            decision_topic=decision_topic,
            project_id=project_id,
            session_id=session_id,
            limit=limit,
            score_threshold=score_threshold,
            include_messages_to_twin=include_messages_to_twin
        )
        return preference_data
    except Exception as e:
        logger.error(f"Error retrieving user preferences: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user preferences: {str(e)}"
        )

@router.post(
    "/{user_id}/private_memory",
    response_model=ChunksResponse,
    summary="Create + Retrieve Private Memory (User Interaction)",
    description="Retrieves a user's private memory based on semantic search AND ingests the query itself as a twin interaction (marked with is_twin_interaction: true). "
                "This endpoint is designed specifically for the user's direct interaction loop with their twin simulation. "
                "By default, the retrieval includes previous user messages to the twin. Set include_messages_to_twin to false to exclude them."
)
async def retrieve_user_private_memory(
    user_id: str = Path(..., description="The ID of the user whose memory is being queried and whose query is being ingested."),
    query: PrivateMemoryQuery = ...,
    include_graph: bool = Query(False, description="Whether to include graph-based enrichments"),
    retrieval_service: RetrievalService = Depends(get_retrieval_service_with_message_connector),
) -> ChunksResponse:
    """API endpoint to retrieve a user's private memory and ingest the query."""
    try:
        logger.info(f"Received private memory request for user_id={user_id}, query='{query.query_text}'")
        
        # First call the private memory retrieval method, passing user_id from the path
        results = await retrieval_service.retrieve_private_memory(
            query_text=query.query_text,
            user_id=user_id,  # Use the path parameter instead of from the request body
            limit=query.limit,
            project_id=query.project_id,
            session_id=query.session_id,
            include_messages_to_twin=query.include_messages_to_twin
        )
        
        # If include_graph is True, enhance with graph data
        if include_graph and results:
            # Build a new list of enriched results
            enriched_results = []
            for result in results:
                # Add the basic result
                enriched_results.append(result)
                logger.info(f"Adding to enriched result the qdrant result: {result}")
                
                # For each result, we could optionally get related content
                if "chunk_id" in result:
                    try:
                        related = await retrieval_service.retrieve_related_content(
                            chunk_id=result["chunk_id"],
                            limit=3,  # Small limit to avoid overwhelming
                            include_private=True  # Include private since this is private memory
                        )
                        logger.info(f"Found related content: {related}")
                        
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