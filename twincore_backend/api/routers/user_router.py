import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, Path

from api.models import ChunksResponse, ContentChunk # Import ContentChunk
from services.retrieval_service import RetrievalService
from services.preference_service import PreferenceService
from api.routers.retrieve_router import get_retrieval_service, get_preference_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/users", tags=["User Retrieval"])

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