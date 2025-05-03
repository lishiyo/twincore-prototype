"""Data Access Layer interfaces.

This module defines the abstract interfaces (protocols) for all DAL components.
These interfaces establish the contract that concrete DAL implementations must fulfill.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel


class IQdrantDAL(ABC):
    """Interface for Qdrant vector database operations."""

    @abstractmethod
    async def upsert_vector(
        self,
        chunk_id: str,
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
        """Insert or update a vector in the Qdrant collection.
        
        Args:
            chunk_id: Unique identifier for the text chunk
            vector: Embedding vector for the text
            text_content: Original text content
            source_type: Type of source (e.g., 'message', 'document')
            user_id: ID of the user who created/owns the content
            project_id: Optional project ID the content belongs to
            session_id: Optional session ID the content belongs to
            doc_id: Optional document ID for document chunks
            message_id: Optional message ID for message chunks
            timestamp: Optional timestamp of content creation
            is_twin_interaction: Whether this is part of a twin interaction
            is_private: Whether this content is private to the user
            metadata: Optional additional metadata

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def search_vectors(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_type: Optional[str] = None,
        include_private: bool = False,
        exclude_twin_interactions: bool = False,
        timestamp_start: Optional[str] = None,
        timestamp_end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in the Qdrant collection.
        
        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results to return
            user_id: Filter by user ID
            project_id: Filter by project ID
            session_id: Filter by session ID
            source_type: Filter by source type
            include_private: Whether to include private content
            exclude_twin_interactions: Whether to exclude twin interactions
            timestamp_start: Filter by start timestamp
            timestamp_end: Filter by end timestamp
        
        Returns:
            List of search results with scores and payload
        """
        pass

    @abstractmethod
    async def delete_vectors(
        self,
        chunk_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> int:
        """Delete vectors from the Qdrant collection.
        
        Args:
            chunk_ids: List of chunk IDs to delete
            user_id: Filter by user ID
            project_id: Filter by project ID 
            session_id: Filter by session ID
            doc_id: Filter by document ID
            message_id: Filter by message ID
            
        Returns:
            Number of vectors deleted
        """
        pass


class INeo4jDAL(ABC):
    """Interface for Neo4j graph database operations."""

    @abstractmethod
    async def create_node_if_not_exists(
        self,
        label: str,
        properties: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a node if it doesn't exist or return the existing one.
        
        Args:
            label: Node label (e.g., 'User', 'Project')
            properties: Node properties
            constraints: Properties that uniquely identify the node
            
        Returns:
            Created or existing node properties
        """
        pass

    @abstractmethod
    async def create_relationship_if_not_exists(
        self,
        start_label: str,
        start_constraints: Dict[str, Any],
        end_label: str,
        end_constraints: Dict[str, Any],
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship between nodes if it doesn't exist.
        
        Args:
            start_label: Label of the start node
            start_constraints: Properties that uniquely identify the start node
            end_label: Label of the end node
            end_constraints: Properties that uniquely identify the end node
            relationship_type: Type of relationship
            properties: Relationship properties
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_session_participants(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """Get the participants of a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            List of user nodes that participated in the session
        """
        pass

    @abstractmethod
    async def get_project_context(
        self, project_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get context information for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Dictionary with lists of sessions, documents, and users
        """
        pass


class IPostgresSharedDAL(ABC):
    """Interface for read-only operations on shared Postgres database."""

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from shared Postgres.
        
        Args:
            user_id: ID of the user
            
        Returns:
            User information or None if not found
        """
        pass

    @abstractmethod
    async def get_project_info(
        self, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get project information from shared Postgres.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Project information or None if not found
        """
        pass

    @abstractmethod
    async def get_session_info(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get session information from shared Postgres.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Session information or None if not found
        """
        pass

    @abstractmethod
    async def validate_user_access(
        self, user_id: str, resource_id: str, resource_type: str
    ) -> bool:
        """Validate user access to a resource.
        
        Args:
            user_id: ID of the user
            resource_id: ID of the resource (project or session)
            resource_type: Type of resource ('project' or 'session')
            
        Returns:
            True if user has access, False otherwise
        """
        pass 