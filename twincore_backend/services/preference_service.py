"""Preference Service for querying user preferences.

This service provides methods for retrieving and interpreting user preferences
from previous interactions stored in the memory system.
"""

import logging
from typing import Dict, List, Optional, Any

import numpy as np

from dal.interfaces import IQdrantDAL, INeo4jDAL
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class PreferenceService:
    """Service for querying user preferences from the memory store.
    
    This service handles the orchestration of retrieval operations to find
    and interpret user preferences on specific topics.
    """
    
    def __init__(
        self, 
        qdrant_dal: IQdrantDAL, 
        neo4j_dal: INeo4jDAL,
        embedding_service: EmbeddingService,
    ):
        """Initialize the PreferenceService with DAL dependencies.
        
        Args:
            qdrant_dal: Data access layer for Qdrant vector operations
            neo4j_dal: Data access layer for Neo4j graph operations
            embedding_service: Service for generating embeddings
        """
        self._qdrant_dal = qdrant_dal
        self._neo4j_dal = neo4j_dal
        self._embedding_service = embedding_service
    
    async def query_user_preference(
        self,
        user_id: str,
        decision_topic: str,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 5,
        score_threshold: Optional[float] = 0.6,
        include_messages_to_twin: bool = True
    ) -> Dict[str, Any]:
        """Query user preferences on a specific topic.
        
        This method combines graph and vector search to find the most relevant
        user statements related to the specified topic that might indicate
        preferences or opinions.
        
        Args:
            user_id: ID of the user whose preferences to query
            decision_topic: The topic to find preferences for
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            limit: Maximum number of results to return per source
            score_threshold: Optional score threshold for vector search
            include_messages_to_twin: Flag to include messages to twin
            
        Returns:
            Dictionary containing relevant preference statements and metadata
        """
        logger.info(f"Querying preferences for user {user_id} on topic '{decision_topic}'")
        
        # Generate embedding for the decision topic
        topic_embedding = await self._embedding_service.get_embedding(decision_topic)
        
        # Combine search results from both sources (graph and vector)
        graph_results = []
        vector_results = []
        
        # 1. Try to find preference statements through graph relationships
        try:
            graph_results = await self._neo4j_dal.get_user_preference_statements(
                user_id=user_id,
                topic=decision_topic,
                limit=limit,
                project_id=project_id,
                session_id=session_id,
                include_twin_interactions=include_messages_to_twin
            )
            logger.info(f"Found {len(graph_results)} preference statements via graph for user {user_id}")
        except Exception as e:
            logger.error(f"Error retrieving preference statements from graph: {e}")
        
        # 2. Perform vector search for semantically similar content to the topic
        try:
            vector_results = await self._qdrant_dal.search_user_preferences(
                query_vector=topic_embedding,
                user_id=user_id,
                decision_topic=decision_topic,
                limit=limit,
                project_id=project_id,
                session_id=session_id,
                score_threshold=score_threshold,
                include_twin_interactions=include_messages_to_twin
            )
            logger.info(f"Found {len(vector_results)} preference statements via vector search for user {user_id}")
        except Exception as e:
            logger.error(f"Error retrieving preference statements via vector search: {e}")
        
        # 3. Check if we have results from either source
        if not graph_results and not vector_results:
            logger.warning(f"No preference statements found for user {user_id} on topic '{decision_topic}'")
            return {
                "user_id": user_id,
                "decision_topic": decision_topic,
                "has_preferences": False,
                "preference_statements": [],
                "graph_results_count": 0,
                "vector_results_count": 0
            }
        
        # 4. Deduplicate results (graph results might overlap with vector results)
        # We prioritize graph results as they come from explicit relationships
        all_chunk_ids = set()
        combined_results = []
        
        # Process graph results first
        for result in graph_results:
            chunk_id = result.get("chunk_id")
            if chunk_id and chunk_id not in all_chunk_ids:
                all_chunk_ids.add(chunk_id)
                # Add source indicator
                result["source"] = "graph"
                combined_results.append(result)
        
        # Then add unique vector results
        for result in vector_results:
            chunk_id = result.get("chunk_id")
            if chunk_id and chunk_id not in all_chunk_ids:
                all_chunk_ids.add(chunk_id)
                # Add source indicator
                result["source"] = "vector"
                combined_results.append(result)
        
        # 5. Sort by relevance score (if available)
        combined_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 6. Return the combined results with metadata
        return {
            "user_id": user_id,
            "decision_topic": decision_topic,
            "has_preferences": len(combined_results) > 0,
            "preference_statements": combined_results[:limit],  # Limit the final combined results
            "graph_results_count": len(graph_results),
            "vector_results_count": len(vector_results)
        } 