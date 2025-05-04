from fastapi import FastAPI, Depends
from functools import lru_cache

from core.config import settings
from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from services.embedding_service import EmbeddingService
from services.ingestion_service import IngestionService
from ingestion.connectors.message_connector import MessageConnector
from services.data_seeder_service import DataSeederService
from services.data_management_service import DataManagementService
from api.routers import admin_router, ingest_router

app = FastAPI(
    title="TwinCore API",
    description="Digital Twin Backend Service for Context Retrieval and User Representation",
    version="0.1.0"
)

# Singleton instances
_embedding_service = None
_qdrant_dal = None
_neo4j_dal = None
_ingestion_service = None
_message_connector = None
_data_seeder_service = None
_data_management_service = None

# Dependencies setup
@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Create and cache the EmbeddingService."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(api_key=settings.openai_api_key)
    return _embedding_service

@lru_cache
def get_qdrant_dal() -> QdrantDAL:
    """Create and cache the QdrantDAL."""
    global _qdrant_dal
    if _qdrant_dal is None:
        _qdrant_dal = QdrantDAL(client=get_async_qdrant_client())
    return _qdrant_dal

async def get_neo4j_dal() -> Neo4jDAL:
    """Create and cache the Neo4jDAL."""
    global _neo4j_dal
    if _neo4j_dal is None:
        driver = await get_neo4j_driver()
        _neo4j_dal = Neo4jDAL(driver=driver)
    return _neo4j_dal

async def get_ingestion_service() -> IngestionService:
    """Create and cache the IngestionService."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService(
            embedding_service=get_embedding_service(),
            qdrant_dal=get_qdrant_dal(),
            neo4j_dal=await get_neo4j_dal()
        )
    return _ingestion_service

async def get_message_connector() -> MessageConnector:
    """Create and cache the MessageConnector."""
    global _message_connector
    if _message_connector is None:
        _message_connector = MessageConnector(
            ingestion_service=await get_ingestion_service()
        )
    return _message_connector

async def get_data_seeder_service() -> DataSeederService:
    """Create and cache the DataSeederService."""
    global _data_seeder_service
    if _data_seeder_service is None:
        _data_seeder_service = DataSeederService(
            ingestion_service=await get_ingestion_service()
        )
    return _data_seeder_service

async def get_data_management_service() -> DataManagementService:
    """Create and cache the DataManagementService."""
    global _data_management_service
    if _data_management_service is None:
        _data_management_service = DataManagementService(
            qdrant_dal=get_qdrant_dal(),
            neo4j_dal=await get_neo4j_dal()
        )
    return _data_management_service

# Register routers
app.include_router(admin_router.router)
app.include_router(ingest_router.router)

# Set up application-level dependency overrides
app.dependency_overrides[admin_router.get_data_seeder_service] = get_data_seeder_service
app.dependency_overrides[admin_router.get_data_management_service] = get_data_management_service
app.dependency_overrides[ingest_router.get_message_connector] = get_message_connector

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {"status": "online", "service": "TwinCore API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 