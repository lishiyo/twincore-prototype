"""Admin router for managing backend administration functions.

This router provides endpoints for system administration tasks like
data seeding that should not be exposed to regular users.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from services.data_seeder_service import DataSeederService, DataSeederServiceError

# Create router with prefix and tags for documentation
router = APIRouter(
    prefix="/api",
    tags=["admin"],
    responses={401: {"description": "Unauthorized"}}
)

# Dependency to get the DataSeederService (will be implemented in main.py)
async def get_data_seeder_service() -> DataSeederService:
    """Dependency to get the DataSeederService instance."""
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