"""Data Management Service for database operations like clearing data.

This service is responsible for operations that affect the overall data state
in the system, such as clearing all data for testing or resetting.
"""

import logging
from typing import Dict, Any, Optional

from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL

logger = logging.getLogger(__name__)


class DataManagementServiceError(Exception):
    """Base exception for data management service errors."""
    pass


class DataManagementService:
    """Service for managing database operations across the system.
    
    This service is responsible for operations that affect the overall 
    data state, such as clearing all data. It uses DAL implementations
    directly to coordinate these operations.
    """
    
    def __init__(self, qdrant_dal: QdrantDAL, neo4j_dal: Neo4jDAL):
        """Initialize the data management service with required dependencies.
        
        Args:
            qdrant_dal: Data access layer for Qdrant
            neo4j_dal: Data access layer for Neo4j
        
        Raises:
            ValueError: If any DAL is None
        """
        if qdrant_dal is None:
            raise ValueError("QdrantDAL must be provided to DataManagementService")
        if neo4j_dal is None:
            raise ValueError("Neo4jDAL must be provided to DataManagementService")
        
        self._qdrant_dal = qdrant_dal
        self._neo4j_dal = neo4j_dal
        logger.info("DataManagementService initialized")
    
    async def clear_all_data(self) -> Dict[str, Any]:
        """Clear all data from all databases.
        
        Coordinates the deletion of data from both Qdrant and Neo4j.
        This is useful for testing, development, or resetting the system.
        
        Returns:
            Dict containing confirmation of cleared data sources
            
        Raises:
            DataManagementServiceError: If clearing fails in any database
        """
        try:
            logger.info("Starting clearing of all data")
            
            # Clear data from Neo4j
            neo4j_result = await self._neo4j_dal.delete_all_data()
            logger.info(f"Cleared all data from Neo4j: {neo4j_result}")
            
            # Clear data from Qdrant
            qdrant_result = await self._qdrant_dal.delete_all_vectors()
            logger.info(f"Cleared all vectors from Qdrant: {qdrant_result}")
            
            return {
                "status": "success",
                "message": "All data cleared successfully",
                "details": {
                    "neo4j": neo4j_result,
                    "qdrant": qdrant_result
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to clear all data: {str(e)}"
            logger.error(error_msg)
            raise DataManagementServiceError(error_msg)

    async def update_document_metadata(
        self,
        doc_id: str,
        source_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update metadata for a specific document in Neo4j.

        Args:
            doc_id: The ID of the document to update.
            source_uri: The optional URI string to set/update.
            metadata: An optional dictionary of other metadata fields to set/update.
            user_id: The ID of the user performing the update (for logging/audit).
            timestamp: The timestamp of the update (for logging/audit).

        Returns:
            True if the update was successful, False if the document was not found.
        
        Raises:
            DataManagementServiceError: If the update fails.
        """
        if source_uri is None and metadata is None:
            logger.warning(f"Update document metadata called for {doc_id} with no data.")
            return False 
            
        try:
            logger.info(f"Updating metadata for document {doc_id}. URI: {source_uri is not None}, Metadata keys: {list(metadata.keys()) if metadata else []}")
            
            success = await self._neo4j_dal.update_document_metadata(
                doc_id=doc_id,
                source_uri=source_uri,
                metadata=metadata
            )
            
            if not success:
                logger.warning(f"Document {doc_id} not found for metadata update.")
                return False
                
            logger.info(f"Successfully updated metadata for document {doc_id}")
            return True

        except ValueError as ve:
             logger.error(f"Value error updating metadata for doc {doc_id}: {ve}")
             raise DataManagementServiceError(f"Invalid data for metadata update: {ve}")
        except Exception as e:
            error_msg = f"Failed to update metadata for document {doc_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise DataManagementServiceError(error_msg) 