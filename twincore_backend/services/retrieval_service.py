"""Retrieval Service for searching and retrieving content from the memory store.

This service provides methods for retrieving context-relevant information from 
the memory store based on semantic search and filtering criteria.
"""

import logging
from typing import Dict, List, Optional, Any

import numpy as np

from dal.interfaces import IQdrantDAL, INeo4jDAL
from services.embedding_service import EmbeddingService
from ingestion.connectors.message_connector import MessageConnector

logger = logging.getLogger(__name__)


class RetrievalService:
    """Service for retrieving context-relevant information from the memory store.
    
    This service handles the orchestration of vector search operations on Qdrant
    and graph operations on Neo4j to retrieve relevant information based on 
    semantic search and filtering criteria.
    """
    
    def __init__(
        self, 
        qdrant_dal: IQdrantDAL, 
        neo4j_dal: INeo4jDAL,
        embedding_service: EmbeddingService,
        message_connector: Optional[MessageConnector] = None
    ):
        """Initialize the RetrievalService with DAL dependencies.
        
        Args:
            qdrant_dal: Data access layer for Qdrant vector operations
            neo4j_dal: Data access layer for Neo4j graph operations
            embedding_service: Service for generating embeddings
            message_connector: Optional - Used for ingesting queries in private memory retrieval
        """
        self._qdrant_dal = qdrant_dal
        self._neo4j_dal = neo4j_dal
        self._embedding_service = embedding_service
        self._message_connector = message_connector
    
    async def retrieve_context(
        self,
        query_text: str,
        limit: int = 10,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_type: Optional[str] = None,
        include_private: bool = False,
        exclude_twin_interactions: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieve context-relevant information based on semantic search.
        
        Args:
            query_text: The text query to search for
            limit: Maximum number of results to return
            user_id: Optional filter by user ID
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            source_type: Optional filter by source type
            include_private: Whether to include private content
            exclude_twin_interactions: Whether to exclude twin interactions (default: True)
        
        Returns:
            List of content chunks with relevance scores and metadata
        """
        # Get embedding for the query text
        query_embedding = await self._embedding_service.get_embedding(query_text)
        
        # If session_id is provided, get participants (optional for extra context)
        participants = []
        if session_id:
            try:
                participants = await self._neo4j_dal.get_session_participants(session_id)
                logger.debug(f"Found {len(participants)} participants for session {session_id}")
            except Exception as e:
                logger.warning(f"Error getting session participants: {e}")
        
        # Search vectors in Qdrant with appropriate filters
        search_results = await self._qdrant_dal.search_vectors(
            query_vector=query_embedding,
            limit=limit,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            source_type=source_type,
            include_private=include_private,
            exclude_twin_interactions=exclude_twin_interactions,
        )
        
        logger.info(f"Retrieved {len(search_results)} context chunks for query: {query_text}")
        return search_results
    
    async def retrieve_private_memory(
        self,
        query_text: str,
        user_id: str,
        limit: int = 10,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve user's private memory based on semantic search.
        
        This method also ingests the query itself as a twin interaction.
        
        Args:
            query_text: The text query to search for
            user_id: User ID whose private memory to search
            limit: Maximum number of results to return
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
        
        Returns:
            List of content chunks with relevance scores and metadata
        """
        # First ingest the query as a twin interaction
        if self._message_connector:
            try:
                await self._message_connector.ingest_message({
                    "text": query_text,
                    "user_id": user_id,
                    "project_id": project_id,
                    "session_id": session_id,
                    "is_twin_chat": True,
                    "source_type": "query"
                })
                logger.debug(f"Ingested twin query: {query_text}")
            except Exception as e:
                logger.error(f"Error ingesting twin query: {e}")
        else:
            logger.warning("MessageConnector not provided, query won't be ingested")
            
        # Get embedding for the query text
        query_embedding = await self._embedding_service.get_embedding(query_text)
        
        # Search vectors with strict filtering (user_id is required, include_private=True)
        search_results = await self._qdrant_dal.search_vectors(
            query_vector=query_embedding,
            limit=limit,
            user_id=user_id,  # Required for private memory
            project_id=project_id,
            session_id=session_id,
            include_private=True,  # Include both private and non-private content
            exclude_twin_interactions=True,  # Exclude other twin interactions
        )
        
        logger.info(f"Retrieved {len(search_results)} private memory chunks for user {user_id}")
        return search_results 