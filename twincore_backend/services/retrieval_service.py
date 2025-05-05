"""Retrieval Service for searching and retrieving content from the memory store.

This service provides methods for retrieving context-relevant information from 
the memory store based on semantic search and filtering criteria.
"""

import logging
from typing import Dict, List, Optional, Any

import numpy as np
import asyncio

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
        include_messages_to_twin: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve context-relevant information based on semantic search. 
        
        Args:
            query_text: The text query to search for
            limit: Maximum number of results to return
            user_id: Optional filter by user ID
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            source_type: Optional filter by source type
            include_private: Whether to include private content like personal docs (default False)
            include_messages_to_twin: Whether to include messages to twin interactions (default False)
        
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
            include_twin_interactions=include_messages_to_twin,
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
        include_messages_to_twin: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieve user's private memory based on semantic search.
        
        This method also ingests the query itself as a twin interaction.
        
        Args:
            query_text: The text query to search for
            user_id: User ID whose private memory to search
            limit: Maximum number of results to return
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            include_messages_to_twin: Whether to include messages to twin interactions
        
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
                    "source_type": "query",
                    "is_private": True
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
            include_twin_interactions=include_messages_to_twin,
        )
        
        logger.info(f"Retrieved {len(search_results)} private memory chunks for user {user_id}")
        return search_results

    async def retrieve_enriched_context(
        self,
        query_text: str,
        limit: int = 10,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_type: Optional[str] = None,
        include_private: bool = False,
        include_messages_to_twin: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve context with graph enrichment from Neo4j.
        
        This method performs vector search first, then enriches results with
        graph relationship data from Neo4j for more contextually relevant information.
        
        Args:
            query_text: The text query to search for
            limit: Maximum number of results to return
            user_id: Optional filter by user ID
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            source_type: Optional filter by source type
            include_private: Whether to include private content
            include_messages_to_twin: Whether to include messages to twin interactions
        
        Returns:
            List of content chunks with relevance scores, metadata, and graph relationship enrichments
        """
        # First, perform standard vector search
        search_results = await self.retrieve_context(
            query_text=query_text,
            limit=limit,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            source_type=source_type,
            include_private=include_private,
            include_messages_to_twin=include_messages_to_twin,
        )
        
        if not search_results:
            return []
        
        # Extract IDs for enrichment
        chunk_ids = [result["chunk_id"] for result in search_results]
        
        # Enrich with project context if project_id is provided
        if project_id:
            try:
                project_context = await self._neo4j_dal.get_project_context(project_id)
                
                # Add project context to all results
                for result in search_results:
                    result["project_context"] = {
                        "session_count": len(project_context.get("sessions", [])),
                        "document_count": len(project_context.get("documents", [])),
                        "user_count": len(project_context.get("users", []))
                    }
            except Exception as e:
                logger.warning(f"Error enriching results with project context: {e}")
        
        # Get session participants if session_id is provided
        if session_id:
            try:
                participants = await self._neo4j_dal.get_session_participants(session_id)
                
                # Add participants to all results
                for result in search_results:
                    result["session_participants"] = [
                        {"user_id": p.get("user_id"), "name": p.get("name")}
                        for p in participants
                    ]
            except Exception as e:
                logger.warning(f"Error enriching results with session participants: {e}")
        
        logger.info(f"Retrieved and enriched {len(search_results)} context chunks for query: {query_text}")
        return search_results
        
    async def retrieve_related_content(
        self,
        chunk_id: str,
        relationship_types: Optional[List[str]] = None,
        limit: int = 10,
        include_private: bool = False,
        max_depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """Retrieve content related to a specific chunk through graph relationships.
        
        This method uses Neo4j graph traversal to find content related to the 
        specified chunk through relationships, without relying on vector similarity.
        
        Args:
            chunk_id: The ID of the content chunk to find related content for
            relationship_types: Optional list of relationship types to traverse
            limit: Maximum number of results to return
            include_private: Whether to include private content
            max_depth: Maximum relationship traversal depth
        
        Returns:
            List of related content with relationship information
        """
        logger.info(f"Retrieving content related to chunk_id={chunk_id} (max_depth={max_depth})")
        
        # Use the Neo4jDAL implementation
        try:
            related_content = await self._neo4j_dal.get_related_content(
                chunk_id=chunk_id,
                relationship_types=relationship_types,
                limit=limit,
                include_private=include_private,
                max_depth=max_depth
            )
            
            logger.info(f"Retrieved {len(related_content)} related content items")
            return related_content
        except Exception as e:
            logger.error(f"Error retrieving related content: {e}")
            return []
    
    async def retrieve_by_topic(
        self,
        topic_name: str,
        limit: int = 10,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        include_private: bool = False,
        include_messages_to_twin: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve content related to a specific topic using graph relationships.
        
        This method uses Neo4j to find content related to the specified topic,
        using graph relationships rather than vector similarity.
        
        Args:
            topic_name: The name of the topic to find related content for
            limit: Maximum number of results to return
            user_id: Optional filter by user ID
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            include_private: Whether to include private content
            include_messages_to_twin: Whether to include messages to twin interactions
        
        Returns:
            List of content related to the specified topic
        """
        logger.info(f"Retrieving content related to topic={topic_name}")
        
        try:
            # Use the Neo4jDAL implementation
            topic_content = await self._neo4j_dal.get_content_by_topic(
                topic_name=topic_name,
                limit=limit,
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                include_private=include_private,
                include_twin_interactions=include_messages_to_twin,
            )
            
            # If we found results through graph relationships, return them
            if topic_content and len(topic_content) > 0:
                logger.info(f"Retrieved {len(topic_content)} content chunks for topic: {topic_name} (via graph)")
                return topic_content
            
            # Fall back to vector search if no graph results found
            logger.info(f"No graph results found for topic: {topic_name}, falling back to vector search")
            query_embedding = await self._embedding_service.get_embedding(topic_name)
            
            search_results = await self._qdrant_dal.search_vectors(
                query_vector=query_embedding,
                limit=limit,
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                include_private=include_private,
                include_twin_interactions=include_messages_to_twin,
            )
            
            logger.info(f"Retrieved {len(search_results)} content chunks for topic: {topic_name} (via vector search)")
            return search_results
            
        except Exception as e:
            logger.error(f"Error retrieving content by topic: {e}")
            
            # Fall back to vector search on error
            try:
                logger.info(f"Error in graph retrieval, falling back to vector search for topic: {topic_name}")
                query_embedding = await self._embedding_service.get_embedding(topic_name)
                
                search_results = await self._qdrant_dal.search_vectors(
                    query_vector=query_embedding,
                    limit=limit,
                    user_id=user_id,
                    project_id=project_id,
                    session_id=session_id,
                    include_private=include_private,
                    include_twin_interactions=include_messages_to_twin,
                )
                
                logger.info(f"Retrieved {len(search_results)} content chunks for topic: {topic_name} (via vector search)")
                return search_results   
            except Exception as e:
                logger.error(f"Error retrieving topic content for {topic_name}: {e}", exc_info=True)
                return [] # Return empty list on error

    async def retrieve_group_context(
        self,
        query_text: str,
        limit_per_user: int = 5,
        session_id: str | None = None,
        project_id: str | None = None,
        team_id: str | None = None,
        include_messages_to_twin: bool = True,
        include_private: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieves context from multiple users within a defined scope.

        Args:
            query_text: The natural language query.
            limit_per_user: Max results per user.
            session_id: Scope to session.
            project_id: Scope to project.
            team_id: Scope to team.
            include_messages_to_twin: Whether to include twin interactions.
            include_private: Whether to include private content.

        Returns:
            A list of dictionaries, each containing a user_id and their relevant chunks.
        """
        if not any([session_id, project_id, team_id]):
            raise ValueError("Must provide one scope ID (session_id, project_id, or team_id).")
        if sum(bool(id) for id in [session_id, project_id, team_id]) > 1:
            raise ValueError("Only one scope ID (session_id, project_id, or team_id) can be provided.")

        participants = []
        scope_type = None
        scope_id = None

        try:
            if session_id:
                scope_type = "session"
                scope_id = session_id
                participants = await self._neo4j_dal.get_session_participants(session_id)
            elif project_id:
                scope_type = "project"
                scope_id = project_id
                participants = await self._neo4j_dal.get_project_participants(project_id)
            elif team_id:
                scope_type = "team"
                scope_id = team_id
                # TODO: Implement get_team_participants in Neo4jDAL if needed
                # participants = await self.neo4j_dal.get_team_participants(team_id)
                logger.warning(f"Team scope retrieval not fully implemented yet for team {team_id}. Returning empty results.")
                participants = [] # Placeholder

            if not participants:
                logger.info(f"No participants found for {scope_type} scope {scope_id}.")
                return []

            logger.info(f"Found {len(participants)} participants for {scope_type} scope {scope_id}.")

        except Exception as e:
            logger.error(f"Error retrieving participants for {scope_type} scope {scope_id}: {e}", exc_info=True)
            return []

        # Get embedding for the main query
        try:
            query_vector = await self._embedding_service.get_embedding(query_text)
        except Exception as e:
            logger.error(f"Error getting embedding for group query '{query_text}': {e}", exc_info=True)
            return []

        group_results = []
        search_tasks = []

        # Create search tasks for each participant
        for participant in participants:
            user_id = participant.get("user_id")
            if user_id:
                # Define search scope for this user within the overall scope
                user_filters = {
                    "user_id": user_id,
                    "project_id": project_id, # Pass down original scope filters
                    "session_id": session_id,
                    # team_id could be added if needed
                    "include_private": include_private,
                    "include_twin_interactions": include_messages_to_twin
                }
                search_tasks.append(
                    self._qdrant_dal.search_vectors(
                        query_vector=query_vector,
                        limit=limit_per_user,
                        **user_filters
                    )
                )
            else:
                logger.warning(f"Participant missing user_id: {participant}")
                search_tasks.append(asyncio.sleep(0, result=[])) # Placeholder for missing ID

        # Run searches concurrently
        try:
            user_search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error during concurrent Qdrant searches for group context: {e}", exc_info=True)
            return []

        # Process results
        for i, result in enumerate(user_search_results):
            user_id = participants[i].get("user_id")
            if isinstance(result, Exception):
                logger.error(f"Error searching Qdrant for user {user_id}: {result}", exc_info=result)
            elif user_id and result:
                logger.info(f"Found {len(result)} results for user {user_id} in group query.")
                group_results.append({
                    "user_id": user_id,
                    "results": result
                })
            elif user_id:
                 logger.info(f"No results found for user {user_id} in group query.")
                 # Optionally add an entry with empty results:
                 # group_results.append({"user_id": user_id, "results": []})

        return group_results

    async def retrieve_user_context(
        self,
        user_id: str,
        query_text: str,
        limit: int = 10,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        include_messages_to_twin: bool = True,
        include_private: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieve context-relevant information specific to a user based on semantic search.

        This searches across all user's relevant data (private docs, group messages, 
        twin interactions, etc.), optionally filtered by project/session scope.
        It is read-only and does not perform ingestion.

        Args:
            user_id: The ID of the user whose context is being queried (REQUIRED)
            query_text: The text query to search for (REQUIRED)
            limit: Maximum number of results to return
            project_id: Optional filter by project ID
            session_id: Optional filter by session ID
            include_messages_to_twin: Whether to include messages to twin interactions (default True)
            include_private: Whether to include the user's private documents (default True)

        Returns:
            List of content chunks with relevance scores and metadata
        """
        logger.info(f"Retrieving context for user_id={user_id} with query: {query_text}")

        # Get embedding for the query text
        query_embedding = await self._embedding_service.get_embedding(query_text)

        # Search vectors in Qdrant with user_id as a required filter
        # and appropriate flags for private content and twin interactions
        search_results = await self._qdrant_dal.search_vectors(
            query_vector=query_embedding,
            limit=limit,
            user_id=user_id,  # Required filter for user-specific context
            project_id=project_id,
            session_id=session_id,
            include_private=include_private,
            include_twin_interactions=include_messages_to_twin,
        )

        logger.info(f"Retrieved {len(search_results)} context chunks for user {user_id}")
        return search_results 