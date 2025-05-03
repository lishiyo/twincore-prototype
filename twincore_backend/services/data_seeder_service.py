"""Data Seeder Service for initializing the system with mock data.

This service is responsible for orchestrating the seeding of initial mock data
into the system, using the IngestionService to handle the actual data ingestion.
"""

import logging
from typing import Dict, Any, Optional, List

from core.mock_data import initial_data_chunks
from services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


class DataSeederServiceError(Exception):
    """Base exception for data seeder service errors."""
    pass


class DataSeederService:
    """Service for seeding initial data into the system.
    
    This service is responsible for loading mock data and orchestrating
    its ingestion into the system using the IngestionService.
    """
    
    def __init__(self, ingestion_service: IngestionService):
        """Initialize the data seeder service with required dependencies.
        
        Args:
            ingestion_service: Service for handling data ingestion
        
        Raises:
            ValueError: If ingestion_service is None
        """
        if ingestion_service is None:
            raise ValueError("IngestionService must be provided to DataSeederService")
        
        self._ingestion_service = ingestion_service
        logger.info("DataSeederService initialized")
    
    async def seed_initial_data(self) -> Dict[str, Any]:
        """Seed the system with initial mock data.
        
        Iterates through predefined mock data chunks from core.mock_data
        and uses the IngestionService to ingest each chunk into the system.
        
        Returns:
            Dict containing counts of successfully ingested items by source type
            
        Raises:
            DataSeederServiceError: If seeding fails
        """
        try:
            logger.info("Starting initial data seeding")
            
            # Keep track of ingestion counts by source type
            ingestion_counts = {}
            
            # Iterate through initial data chunks and ingest each one
            for chunk in initial_data_chunks:
                await self._ingestion_service.ingest_chunk(
                    chunk_id=chunk["chunk_id"],
                    text_content=chunk["text"],
                    source_type=chunk["source_type"],
                    user_id=chunk.get("user_id"),
                    project_id=chunk.get("project_id"),
                    session_id=chunk.get("session_id"),
                    doc_id=chunk.get("doc_id"),
                    message_id=chunk.get("message_id"),
                    doc_name=chunk.get("doc_name"),
                    timestamp=chunk.get("timestamp"),
                    is_twin_interaction=chunk.get("is_twin_interaction", False),
                    is_private=chunk.get("is_private", False),
                    metadata=chunk.get("metadata")
                )
                
                # Update counts
                source_type = chunk["source_type"]
                if source_type in ingestion_counts:
                    ingestion_counts[source_type] += 1
                else:
                    ingestion_counts[source_type] = 1
            
            total_count = sum(ingestion_counts.values())
            logger.info(f"Successfully seeded {total_count} data chunks")
            
            return {
                "total": total_count,
                "counts_by_type": ingestion_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to seed initial data: {str(e)}")
            raise DataSeederServiceError(f"Failed to seed initial data: {str(e)}")
    
    async def seed_custom_data(self, data_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Seed the system with custom provided data.
        
        Allows for seeding data beyond the initial mock data, useful for
        testing or specialized initialization scenarios.
        
        Args:
            data_chunks: List of data chunks to ingest, each following the
                        same format as items in initial_data_chunks
        
        Returns:
            Dict containing counts of successfully ingested items by source type
            
        Raises:
            DataSeederServiceError: If seeding fails
        """
        try:
            logger.info(f"Starting custom data seeding with {len(data_chunks)} chunks")
            
            # Keep track of ingestion counts by source type
            ingestion_counts = {}
            
            # Iterate through data chunks and ingest each one
            for chunk in data_chunks:
                # Ensure chunk_id exists
                if "chunk_id" not in chunk:
                    raise ValueError("Each data chunk must have a chunk_id")
                
                # Ensure required fields exist
                if "text" not in chunk:
                    raise ValueError(f"Data chunk {chunk['chunk_id']} is missing required 'text' field")
                if "source_type" not in chunk:
                    raise ValueError(f"Data chunk {chunk['chunk_id']} is missing required 'source_type' field")
                
                await self._ingestion_service.ingest_chunk(
                    chunk_id=chunk["chunk_id"],
                    text_content=chunk["text"],
                    source_type=chunk["source_type"],
                    user_id=chunk.get("user_id"),
                    project_id=chunk.get("project_id"),
                    session_id=chunk.get("session_id"),
                    doc_id=chunk.get("doc_id"),
                    message_id=chunk.get("message_id"),
                    doc_name=chunk.get("doc_name"),
                    timestamp=chunk.get("timestamp"),
                    is_twin_interaction=chunk.get("is_twin_interaction", False),
                    is_private=chunk.get("is_private", False),
                    metadata=chunk.get("metadata")
                )
                
                # Update counts
                source_type = chunk["source_type"]
                if source_type in ingestion_counts:
                    ingestion_counts[source_type] += 1
                else:
                    ingestion_counts[source_type] = 1
            
            total_count = sum(ingestion_counts.values())
            logger.info(f"Successfully seeded {total_count} custom data chunks")
            
            return {
                "total": total_count,
                "counts_by_type": ingestion_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to seed custom data: {str(e)}")
            raise DataSeederServiceError(f"Failed to seed custom data: {str(e)}") 