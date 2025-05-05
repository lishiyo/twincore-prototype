"""Admin router for managing backend administration functions.

This router provides endpoints for system administration tasks like
data seeding that should not be exposed to regular users.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Body, status
from typing import Dict, Any, Optional

from api.models import StatusResponse
from services.data_seeder_service import DataSeederService, DataSeederServiceError
from services.data_management_service import DataManagementService, DataManagementServiceError

# Create router with prefix and tags for documentation
router = APIRouter(
    prefix="/v1/admin/api",
    tags=["admin"],
    responses={401: {"description": "Unauthorized"}}
)

# Dependency to get the DataSeederService (will be implemented in main.py)
async def get_data_seeder_service() -> DataSeederService:
    """Dependency to get the DataSeederService instance."""
    # This will be replaced in main.py with the actual dependency
    pass

# Dependency to get the DataManagementService (will be implemented in main.py)
async def get_data_management_service() -> DataManagementService:
    """Dependency to get the DataManagementService instance."""
    # This will be replaced in main.py with the actual dependency
    pass

@router.post("/seed_data", status_code=202)
async def seed_data(
    seeder_service: DataSeederService = Depends(get_data_seeder_service)
) -> Dict[str, Any]:
    """Seed the system with initial mock data.
    
    This endpoint initializes the system with predefined mock data
    for testing and demonstration purposes.
    
    Returns:
        JSON object containing the counts of seeded items by type.
    
    Raises:
        HTTPException: If seeding operation fails
    """
    try:
        result = await seeder_service.seed_initial_data()
        return {
            "status": "success",
            "message": f"Successfully seeded {result['total']} items",
            "data": result
        }
    except DataSeederServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear_data", status_code=202)
async def clear_data(
    management_service: DataManagementService = Depends(get_data_management_service)
) -> Dict[str, Any]:
    """Clear all data from the system.
    
    This endpoint deletes all data from both Qdrant and Neo4j databases.
    This is useful for testing, development, or resetting the system to a clean state.
    
    Returns:
        JSON object containing confirmation of cleared data.
    
    Raises:
        HTTPException: If clearing operation fails
    """
    try:
        result = await management_service.clear_all_data()
        return {
            "status": "success",
            "message": "All data successfully cleared",
            "data": result
        }
    except DataManagementServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/qdrant")
async def get_qdrant_stats(
    management_service: DataManagementService = Depends(get_data_management_service)
) -> Dict[str, Any]:
    """Get statistics about the Qdrant database.
    
    This endpoint retrieves information about the Qdrant collection,
    including the number of vectors and points.
    
    Returns:
        JSON object containing Qdrant statistics.
    
    Raises:
        HTTPException: If retrieving stats fails
    """
    try:
        result = await management_service.get_qdrant_stats()
        return result
    except DataManagementServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/neo4j")
async def get_neo4j_stats(
    management_service: DataManagementService = Depends(get_data_management_service)
) -> Dict[str, Any]:
    """Get statistics about the Neo4j database.
    
    This endpoint retrieves information about the Neo4j database,
    including node and relationship counts by label/type.
    
    Returns:
        JSON object containing Neo4j statistics.
    
    Raises:
        HTTPException: If retrieving stats fails
    """
    try:
        result = await management_service.get_neo4j_stats()
        return result
    except DataManagementServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) 