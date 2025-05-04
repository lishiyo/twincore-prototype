"""Qdrant Data Access Layer implementation.

This module provides the concrete implementation of the IQdrantDAL interface,
handling vector operations with the Qdrant vector database using the asynchronous client.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue, Range, PointIdsList, FilterSelector
from qdrant_client.http.exceptions import UnexpectedResponse

from core.config import settings
from dal.interfaces import IQdrantDAL

logger = logging.getLogger(__name__)


class QdrantDAL(IQdrantDAL):
    """Qdrant Data Access Layer implementation (Async).
    
    This class handles all interactions with the Qdrant vector database using
    an injected asynchronous client.
    """

    def __init__(self, client: AsyncQdrantClient):
        """Initialize the Qdrant DAL with an existing async client.
        
        Args:
            client: An initialized async Qdrant client instance.
        """
        if client is None:
            raise ValueError("AsyncQdrantClient must be provided to QdrantDAL")
        self._client = client
        self._collection_name = settings.qdrant_collection_name

    @property
    def client(self) -> AsyncQdrantClient:
        """Get the injected async Qdrant client instance.
        
        Returns:
            AsyncQdrantClient: The initialized async Qdrant client passed during construction.
        """
        return self._client

    async def delete_all_vectors(self) -> Dict[str, Any]:
        """Delete all vectors from the Qdrant collection.
        
        This is a destructive operation that removes all vectors.
        Use with caution - generally only for testing, development, or resetting.
        
        Returns:
            Dict: Information about what was deleted
            
        Raises:
            UnexpectedResponse: If Qdrant errors occur
            Exception: For any other unexpected errors
        """
        try:
            logger.info(f"Deleting all vectors from collection {self._collection_name}")
            
            # First, count how many vectors we have
            count_result = await self._client.count(
                collection_name=self._collection_name
            )
            total_vectors = count_result.count
            
            # Use an empty filter to match all points
            empty_filter = models.Filter()
            points_selector = models.FilterSelector(filter=empty_filter)
            
            # Delete all points
            await self._client.delete(
                collection_name=self._collection_name,
                points_selector=points_selector,
                wait=True
            )
            
            logger.info(f"Successfully deleted all {total_vectors} vectors from collection {self._collection_name}")
            
            return {
                "vectors_deleted": total_vectors,
                "collection": self._collection_name
            }
            
        except UnexpectedResponse as e:
            logger.error(f"Qdrant error deleting all vectors: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting all vectors: {str(e)}")
            raise

    async def upsert_vector(
        self,
        chunk_id: Union[int, str],
        vector: np.ndarray,
        text_content: str,
        source_type: str,
        user_id: str,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        is_twin_interaction: bool = False,
        is_private: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Insert or update a vector in the Qdrant collection."""
        try:
            # Generate UUID if not provided
            if not chunk_id:
                chunk_id = str(uuid.uuid4())
            
            # Convert chunk_id to string if it's not already
            chunk_id_str = str(chunk_id)
            
            # Create payload with required fields
            payload = {
                "text_content": text_content,
                "source_type": source_type,
                "user_id": user_id,
                "is_twin_interaction": is_twin_interaction,
                "is_private": is_private,
                # Store timestamp as Unix timestamp (float) for range queries
                "timestamp": (datetime.fromisoformat(timestamp).timestamp() 
                              if timestamp else datetime.now().timestamp()),
            }
            
            # Add optional fields if present
            if project_id:
                payload["project_id"] = project_id
            if session_id:
                payload["session_id"] = session_id
            if doc_id:
                payload["doc_id"] = doc_id
            if message_id:
                payload["message_id"] = message_id
                
            # Add additional metadata if provided
            if metadata:
                payload.update(metadata)
            
            # Ensure vector is in the correct format (list)
            vector_data = vector.tolist() if isinstance(vector, np.ndarray) else vector
                
            # Check for NaN or Inf values in the vector
            if not np.isfinite(vector_data).all():
                logger.error(f"Vector for chunk_id={chunk_id} contains NaN or Inf values.")
                raise ValueError(f"Vector for chunk_id={chunk_id} contains NaN or Inf values.")
            
            # debug vector length
            logger.info(f"Vector length: {len(vector_data)}")
            logger.info(f"Upserting vector with chunk_id={chunk_id_str} and payload={payload}")
            
            # Create a list of PointStruct objects for upsert
            points = [
                models.PointStruct(
                    id=chunk_id_str,  # Use string ID
                    vector=vector_data,
                    payload=payload
                )
            ]

            # Use the upsert method with points list
            await self._client.upsert(
                collection_name=self._collection_name,
                wait=True,
                points=points  # Pass the list of PointStruct objects
            )
            
            logger.debug(f"Successfully upserted vector with chunk_id={chunk_id}")
            return True
            
        except UnexpectedResponse as e:
            logger.error(f"Qdrant error upserting vector: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error upserting vector: {str(e)}")
            raise

    async def search_vectors(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_type: Optional[str] = None,
        include_private: bool = False,
        include_twin_interactions: bool = False,
        timestamp_start: Optional[str] = None,
        timestamp_end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in the Qdrant collection."""
        try:
            filter_conditions = []
  
            if user_id: filter_conditions.append(models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)))
            if project_id: filter_conditions.append(models.FieldCondition(key="project_id", match=models.MatchValue(value=project_id)))
            if session_id: filter_conditions.append(models.FieldCondition(key="session_id", match=models.MatchValue(value=session_id)))                
            if source_type: filter_conditions.append(models.FieldCondition(key="source_type", match=models.MatchValue(value=source_type)))
            if not include_private: filter_conditions.append(models.FieldCondition(key="is_private", match=models.MatchValue(value=False)))
            if not include_twin_interactions: 
                filter_conditions.append(models.FieldCondition(key="is_twin_interaction", match=models.MatchValue(value=False)))
  
            # Build range conditions separately, converting ISO strings to Unix timestamps
            range_conditions = {}
            if timestamp_start:
                try:
                    dt_start = datetime.fromisoformat(timestamp_start)
                    range_conditions["gte"] = dt_start.timestamp()
                except ValueError:
                    logger.warning(f"Invalid ISO format for timestamp_start: {timestamp_start}")
            if timestamp_end:
                 try:
                    dt_end = datetime.fromisoformat(timestamp_end)
                    range_conditions["lte"] = dt_end.timestamp()
                 except ValueError:
                    logger.warning(f"Invalid ISO format for timestamp_end: {timestamp_end}")
                    
            if range_conditions:
                 filter_conditions.append(models.FieldCondition(key="timestamp", range=models.Range(**range_conditions)))
 
            search_filter = models.Filter(must=filter_conditions) if filter_conditions else None
  
            vector_data = query_vector.tolist() if isinstance(query_vector, np.ndarray) else query_vector
            
            # Use the search method with proper filter structure
            search_results = await self._client.search(
                collection_name=self._collection_name,
                query_vector=vector_data,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            logger.info(f"Search results: {search_results}")
            
            # Format results as list of dictionaries
            formatted_results = []
            for hit in search_results:
                result = {
                    "chunk_id": hit.id,
                    "score": hit.score,
                    **hit.payload  # Include all payload fields
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except UnexpectedResponse as e:
            logger.error(f"Qdrant error searching vectors: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching vectors: {str(e)}")
            raise

    async def delete_vectors(
        self,
        chunk_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> int:
        """Delete vectors from the Qdrant collection."""
        print("!!!! DELETE_VECTORS METHOD CALLED !!!!")  # This will print even if logs are filtered
        logger.error("DELETE_VECTORS METHOD CALLED")  # Using error level to ensure it shows up
        try:
            if chunk_ids and len(chunk_ids) > 0:
                # Log chunk IDs we're trying to delete
                logger.info(f"Attempting to delete chunk IDs: {chunk_ids}")
                
                # Verify points exist before deletion
                for chunk_id in chunk_ids:
                    response = await self._client.retrieve(
                        collection_name=self._collection_name,
                        ids=[chunk_id]
                    )
                    logger.info(f"Before deletion - Point {chunk_id} exists: {len(response) > 0}")
                
                # Log the selector info (without client attributes)
                logger.info(f"Deleting points: {chunk_ids}")
                
                # Try deletion with detailed error handling
                try:
                    # Use delete with a points_selector
                    points_selector = models.PointIdsList(points=chunk_ids)
                    result = await self._client.delete(
                        collection_name=self._collection_name,
                        points_selector=points_selector,
                        wait=True
                    )
                    logger.info(f"Delete result: {result}")
                    
                    # Check points after deletion
                    for chunk_id in chunk_ids:
                        response = await self._client.retrieve(
                            collection_name=self._collection_name,
                            ids=[chunk_id]
                        )
                        logger.info(f"After deletion - Point {chunk_id} exists: {len(response) > 0}")
                    
                except Exception as e:
                    logger.error(f"Delete operation failed with exception: {e}")
                    logger.error(f"Exception type: {type(e)}")
                    raise
                
                return len(chunk_ids)
            else:
                # For filter-based deletion, need to count matching points first
                filter_conditions = []
                if user_id: filter_conditions.append(models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)))
                if project_id: filter_conditions.append(models.FieldCondition(key="project_id", match=models.MatchValue(value=project_id)))
                if session_id: filter_conditions.append(models.FieldCondition(key="session_id", match=models.MatchValue(value=session_id)))
                if doc_id: filter_conditions.append(models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id)))
                if message_id: filter_conditions.append(models.FieldCondition(key="message_id", match=models.MatchValue(value=message_id)))
                
                if not filter_conditions:
                    raise ValueError("At least one filter parameter (chunk_ids or metadata field) must be provided for deletion")
                
                # Count matching points before deletion
                filter_obj = models.Filter(must=filter_conditions)
                count_result = await self._client.count(
                    collection_name=self._collection_name,
                    count_filter=filter_obj
                )
                count_before = count_result.count
                
                # Create filter selector for deletion
                points_selector = models.FilterSelector(filter=filter_obj)
                
                # Use the delete method with the filter selector
                await self._client.delete(
                    collection_name=self._collection_name,
                    points_selector=points_selector,
                    wait=True
                )
                
                logger.debug(f"Deleted approximately {count_before} vectors.")
                return count_before
            
        except UnexpectedResponse as e:
            logger.error(f"Qdrant error deleting vectors: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting vectors: {str(e)}")
            raise 

    async def search_user_preferences(
        self,
        query_vector: np.ndarray,
        user_id: str,
        decision_topic: str,
        limit: int = 5,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        score_threshold: Optional[float] = 0.6,
        include_twin_interactions: bool = True
    ) -> List[Dict[str, Any]]:
        """Search for vectors related to user preferences on a specific topic.
        
        This method performs a semantic search for preferences related to the specified topic
        that belong to the specified user. It applies filters to ensure only the correct
        user's content is returned.
        
        Args:
            query_vector: Embedding vector of the decision topic
            user_id: ID of the user whose preferences to query
            decision_topic: The topic to find preferences for
            limit: Maximum number of results to return
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            score_threshold: Minimum score threshold for results
            include_twin_interactions: Whether to include twin interactions
        Returns:
            List of vectors containing user preferences related to the topic
        """
        try:
            # Create filters to ensure we're only looking at the specified user's content
            filter_conditions = [
                models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))
            ]
            
            # Updated filter logic: only add the filter if we explicitly want to exclude twin interactions
            if not include_twin_interactions:
                filter_conditions.append(
                    models.FieldCondition(key="is_twin_interaction", match=models.MatchValue(value=False))
                )
            
            # Add optional project and session filters
            if project_id:
                filter_conditions.append(
                    models.FieldCondition(key="project_id", match=models.MatchValue(value=project_id))
                )
            if session_id:
                filter_conditions.append(
                    models.FieldCondition(key="session_id", match=models.MatchValue(value=session_id))
                )
                
            # Create the search filter
            search_filter = models.Filter(must=filter_conditions)
            
            # Prepare the query vector
            vector_data = query_vector.tolist() if isinstance(query_vector, np.ndarray) else query_vector
            
            # Search for relevant content
            search_results = await self._client.search(
                collection_name=self._collection_name,
                query_vector=vector_data,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False
            )

            # Log the raw results with scores
            logger.info(f"Raw Qdrant search results for user {user_id} on topic '{decision_topic}': {search_results}")

            # Format the results, applying the score threshold manually
            formatted_results = []
            for hit in search_results:
                # Ensure score meets the threshold if provided
                if score_threshold is None or hit.score >= score_threshold:
                    result = {
                        "chunk_id": hit.id,
                        "score": hit.score,
                        "query_topic": decision_topic,
                        **hit.payload  # Include all payload fields
                    }
                    formatted_results.append(result)
            
            # Log the count AFTER filtering
            logger.info(f"Found {len(formatted_results)} preference-related chunks (above threshold {score_threshold}) for user {user_id} on topic '{decision_topic}'")
            return formatted_results
            
        except UnexpectedResponse as e:
            logger.error(f"Qdrant error searching user preferences: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching user preferences: {str(e)}")
            raise 