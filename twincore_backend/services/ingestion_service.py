"""Ingestion Service for coordinating data storage across databases.

This service orchestrates the process of ingesting data into the system,
handling embedding generation and storage in both Qdrant and Neo4j.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
from pydantic import ValidationError

from services.embedding_service import EmbeddingService
from dal.interfaces import IQdrantDAL, INeo4jDAL
from core.mock_data import get_user_name

logger = logging.getLogger(__name__)


class IngestionServiceError(Exception):
    """Base exception for ingestion service errors."""
    pass


class IngestionService:
    """Service for orchestrating data ingestion into Qdrant and Neo4j.
    
    This service coordinates the process of embedding text data,
    storing it in the vector database (Qdrant), and maintaining
    the relationship graph in Neo4j.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_dal: IQdrantDAL,
        neo4j_dal: INeo4jDAL
    ):
        """Initialize the ingestion service with required dependencies.
        
        Args:
            embedding_service: Service for generating text embeddings
            qdrant_dal: Data access layer for Qdrant vector database
            neo4j_dal: Data access layer for Neo4j graph database
        
        Raises:
            ValueError: If any required dependency is None
        """
        if embedding_service is None:
            raise ValueError("EmbeddingService must be provided to IngestionService")
        if qdrant_dal is None:
            raise ValueError("QdrantDAL must be provided to IngestionService")
        if neo4j_dal is None:
            raise ValueError("Neo4jDAL must be provided to IngestionService")
        
        self._embedding_service = embedding_service
        self._qdrant_dal = qdrant_dal
        self._neo4j_dal = neo4j_dal
        
        logger.info("IngestionService initialized")
    
    async def _prepare_qdrant_point(
        self,
        chunk_id: Union[int, str],
        text_content: str,
        source_type: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        is_twin_interaction: bool = False,
        is_private: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Prepare a point for insertion into Qdrant by generating an embedding.
        
        Args:
            chunk_id: Unique identifier for the text chunk (integer or string)
            text_content: The text to embed and store
            source_type: Type of source (e.g., 'message', 'document')
            user_id: Optional ID of the user who created/owns the content
            project_id: Optional project ID the content belongs to
            session_id: Optional session ID the content belongs to
            doc_id: Optional document ID for document chunks
            message_id: Optional message ID for message chunks
            timestamp: Optional timestamp of content creation
            is_twin_interaction: Whether this is part of a twin interaction
            is_private: Whether this content is private to the user
            metadata: Optional additional metadata
            
        Returns:
            Dict containing the embedding vector and all metadata
            
        Raises:
            IngestionServiceError: If embedding generation fails
        """
        try:
            # Generate embedding for the text
            vector = await self._embedding_service.get_embedding(text_content)
            
            # Use current timestamp if not provided
            if timestamp is None:
                timestamp = datetime.utcnow().isoformat()
            
            # Ensure chunk_id is a string
            chunk_id_str = str(chunk_id)
            
            # Combine metadata
            qdrant_metadata = {
                "chunk_id": chunk_id_str,
                "text_content": text_content,
                "source_type": source_type,
                "timestamp": timestamp,
                "is_twin_interaction": is_twin_interaction,
                "is_private": is_private
            }
            
            # Add optional fields if provided
            if user_id:
                qdrant_metadata["user_id"] = user_id
            if project_id:
                qdrant_metadata["project_id"] = project_id
            if session_id:
                qdrant_metadata["session_id"] = session_id
            if doc_id:
                qdrant_metadata["doc_id"] = doc_id
            if message_id:
                qdrant_metadata["message_id"] = message_id
            
            # Add any additional metadata
            if metadata:
                qdrant_metadata.update(metadata)
            
            return {
                "chunk_id": chunk_id_str,
                "vector": vector,
                "metadata": qdrant_metadata
            }
        except Exception as e:
            raise IngestionServiceError(f"Failed to prepare Qdrant point: {str(e)}")
    
    async def _update_neo4j_graph(
        self,
        source_type: str,
        chunk_id: Union[int, str],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        message_id: Optional[str] = None,
        doc_name: Optional[str] = None,
        timestamp: Optional[str] = None,
        is_twin_interaction: bool = False,
        is_private: bool = False
    ) -> bool:
        """Update the Neo4j graph with nodes and relationships for the ingested content.
        
        Args:
            source_type: Type of source (e.g., 'message', 'document', 'document_chunk')
            chunk_id: Unique identifier for the text chunk (integer)
            user_id: Optional ID of the user who created/owns the content
            project_id: Optional project ID the content belongs to
            session_id: Optional session ID the content belongs to
            doc_id: Optional document ID for document chunks
            message_id: Optional message ID for message chunks
            doc_name: Optional name of the document
            timestamp: Optional timestamp of content creation
            is_twin_interaction: Whether this is part of a twin interaction
            is_private: Whether this content is private to the user
            
        Returns:
            True if the graph was updated successfully
            
        Raises:
            IngestionServiceError: If Neo4j update fails
        """
        try:
            # Use current timestamp if not provided
            if timestamp is None:
                timestamp = datetime.utcnow().isoformat()
            
            # Create Chunk node (always created)
            # Convert chunk_id to string for Neo4j
            chunk_id_str = str(chunk_id)
            
            chunk_properties = {
                "chunk_id": chunk_id_str,
                "timestamp": timestamp,
                "is_twin_interaction": is_twin_interaction,
                "is_private": is_private
            }
            await self._neo4j_dal.create_node_if_not_exists("Chunk", chunk_properties, {"chunk_id": chunk_id_str})
            
            # Create and link nodes based on provided IDs
            created_nodes = []
            
            # User node and relationship (if user_id provided)
            if user_id:
                # Get user name from mock data
                user_name = get_user_name(user_id)
                user_props = {"user_id": user_id, "name": user_name}
                await self._neo4j_dal.create_node_if_not_exists("User", user_props, {"user_id": user_id})
                created_nodes.append(("User", {"user_id": user_id}))
                
                # Connect User to Chunk
                await self._neo4j_dal.create_relationship_if_not_exists(
                    "User", {"user_id": user_id},
                    "Chunk", {"chunk_id": chunk_id_str},
                    "OWNS" if is_private else "CREATED",
                    {"timestamp": timestamp}
                )
            
            # Project node and relationship (if project_id provided)
            if project_id:
                project_props = {"project_id": project_id}
                await self._neo4j_dal.create_node_if_not_exists("Project", project_props, {"project_id": project_id})
                created_nodes.append(("Project", {"project_id": project_id}))
                
                # Connect Chunk to Project
                await self._neo4j_dal.create_relationship_if_not_exists(
                    "Chunk", {"chunk_id": chunk_id_str},
                    "Project", {"project_id": project_id},
                    "PART_OF",
                    {"timestamp": timestamp}
                )
            
            # Session node and relationships (if session_id provided)
            if session_id:
                session_props = {"session_id": session_id}
                if project_id:
                    session_props["project_id"] = project_id
                
                await self._neo4j_dal.create_node_if_not_exists("Session", session_props, {"session_id": session_id})
                created_nodes.append(("Session", {"session_id": session_id}))
                
                # Connect Chunk to Session
                await self._neo4j_dal.create_relationship_if_not_exists(
                    "Chunk", {"chunk_id": chunk_id_str},
                    "Session", {"session_id": session_id},
                    "PART_OF",
                    {"timestamp": timestamp}
                )
                
                # Connect Session to Project if both are provided
                if project_id:
                    await self._neo4j_dal.create_relationship_if_not_exists(
                        "Session", {"session_id": session_id},
                        "Project", {"project_id": project_id},
                        "PART_OF",
                        {}
                    )
                
                # Connect User to Session if both are provided
                if user_id:
                    await self._neo4j_dal.create_relationship_if_not_exists(
                        "User", {"user_id": user_id},
                        "Session", {"session_id": session_id},
                        "PARTICIPATED_IN",
                        {}
                    )
            
            # Handle document and message specific logic
            if source_type == 'document' or source_type == 'document_chunk':
                if doc_id:
                    doc_props = {"document_id": doc_id}
                    if doc_name:
                        doc_props["name"] = doc_name
                    if user_id:
                        doc_props["uploader_id"] = user_id
                    if is_private:
                        doc_props["is_private"] = is_private
                    
                    await self._neo4j_dal.create_node_if_not_exists("Document", doc_props, {"document_id": doc_id})
                    created_nodes.append(("Document", {"document_id": doc_id}))
                    
                    # Connect Chunk to Document
                    await self._neo4j_dal.create_relationship_if_not_exists(
                        "Chunk", {"chunk_id": chunk_id_str},
                        "Document", {"document_id": doc_id},
                        "PART_OF",
                        {"timestamp": timestamp}
                    )
                    
                    # Connect User to Document if both provided
                    if user_id:
                        await self._neo4j_dal.create_relationship_if_not_exists(
                            "User", {"user_id": user_id},
                            "Document", {"document_id": doc_id},
                            "UPLOADED",
                            {"timestamp": timestamp}
                        )
                    
                    # Connect Document to Project if both provided
                    if project_id:
                        await self._neo4j_dal.create_relationship_if_not_exists(
                            "Document", {"document_id": doc_id},
                            "Project", {"project_id": project_id},
                            "PART_OF",
                            {}
                        )
                    
                    # Connect Document to Session if both provided
                    if session_id:
                        await self._neo4j_dal.create_relationship_if_not_exists(
                            "Document", {"document_id": doc_id},
                            "Session", {"session_id": session_id},
                            "UPLOADED_IN",
                            {"timestamp": timestamp}
                        )
            
            elif source_type == 'message':
                if message_id:
                    message_props = {
                        "message_id": message_id,
                        "timestamp": timestamp
                    }
                    if is_twin_interaction:
                        message_props["is_twin_interaction"] = is_twin_interaction
                    
                    await self._neo4j_dal.create_node_if_not_exists("Message", message_props, {"message_id": message_id})
                    created_nodes.append(("Message", {"message_id": message_id}))
                    
                    # Connect Chunk to Message
                    await self._neo4j_dal.create_relationship_if_not_exists(
                        "Chunk", {"chunk_id": chunk_id_str},
                        "Message", {"message_id": message_id},
                        "PART_OF",
                        {"timestamp": timestamp}
                    )
                    
                    # Connect User to Message if both provided
                    if user_id:
                        await self._neo4j_dal.create_relationship_if_not_exists(
                            "User", {"user_id": user_id},
                            "Message", {"message_id": message_id},
                            "AUTHORED",
                            {"timestamp": timestamp}
                        )
                    
                    # Connect Message to Session if both provided
                    if session_id:
                        await self._neo4j_dal.create_relationship_if_not_exists(
                            "Message", {"message_id": message_id},
                            "Session", {"session_id": session_id},
                            "POSTED_IN",
                            {"timestamp": timestamp}
                        )
            
            return True
        except Exception as e:
            raise IngestionServiceError(f"Failed to update Neo4j graph: {str(e)}")
    
    async def ingest_chunk(
        self,
        chunk_id: Union[int, str],
        text_content: str,
        source_type: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        message_id: Optional[str] = None,
        doc_name: Optional[str] = None,
        timestamp: Optional[str] = None,
        is_twin_interaction: bool = False,
        is_private: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Ingest a text chunk into the system, storing it in both Qdrant and Neo4j.
        
        This is the main entry point for ingesting data into the system.
        
        Args:
            chunk_id: Unique identifier for the text chunk (integer or string)
            text_content: The text to ingest
            source_type: Type of source (e.g., 'message', 'document', 'document_chunk')
            user_id: Optional ID of the user who created/owns the content
            project_id: Optional project ID the content belongs to
            session_id: Optional session ID the content belongs to
            doc_id: Optional document ID for document chunks
            message_id: Optional message ID for message chunks
            doc_name: Optional name of the document
            timestamp: Optional timestamp of content creation
            is_twin_interaction: Whether this is part of a twin interaction
            is_private: Whether this content is private to the user
            metadata: Optional additional metadata
            
        Returns:
            True if ingestion was successful
            
        Raises:
            IngestionServiceError: If ingestion fails
        """
        try:
            # No need to validate or convert chunk_id - just use it as provided
            # Can be integer or string (like UUID)
                
            logger.info(f"Ingesting chunk {chunk_id} of source type {source_type}")
            
            # Prepare Qdrant point (get embedding and format metadata)
            point_data = await self._prepare_qdrant_point(
                chunk_id=chunk_id,
                text_content=text_content,
                source_type=source_type,
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                doc_id=doc_id,
                message_id=message_id,
                timestamp=timestamp,
                is_twin_interaction=is_twin_interaction,
                is_private=is_private,
                metadata=metadata
            )
            
            # Store in Qdrant
            await self._qdrant_dal.upsert_vector(
                chunk_id=chunk_id,
                vector=point_data["vector"],
                text_content=text_content,
                source_type=source_type,
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                doc_id=doc_id,
                message_id=message_id,
                timestamp=timestamp,
                is_twin_interaction=is_twin_interaction,
                is_private=is_private,
                metadata=metadata
            )
            
            # Update Neo4j graph
            await self._update_neo4j_graph(
                source_type=source_type,
                chunk_id=chunk_id,
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                doc_id=doc_id,
                message_id=message_id,
                doc_name=doc_name,
                timestamp=timestamp,
                is_twin_interaction=is_twin_interaction,
                is_private=is_private
            )
            
            logger.info(f"Successfully ingested chunk {chunk_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ingest chunk {chunk_id}: {str(e)}")
            raise IngestionServiceError(f"Failed to ingest chunk: {str(e)}") 