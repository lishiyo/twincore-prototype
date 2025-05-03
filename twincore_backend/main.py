from fastapi import FastAPI, Depends
from functools import lru_cache

from core.config import settings
from core.db_clients import get_async_qdrant_client, get_neo4j_driver
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from services.embedding_service import EmbeddingService
from services.ingestion_service import IngestionService
from services.data_seeder_service import DataSeederService
from api.routers import admin_router

app = FastAPI(
    title="TwinCore API",
    description="Digital Twin Backend Service for Context Retrieval and User Representation",
    version="0.1.0"
)

# Dependencies setup
@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Create and cache the EmbeddingService."""
    return EmbeddingService(openai_api_key=settings.openai_api_key)

@lru_cache
def get_qdrant_dal() -> QdrantDAL:
    """Create and cache the QdrantDAL."""
    return QdrantDAL(client=get_async_qdrant_client())

@lru_cache
async def get_neo4j_dal() -> Neo4jDAL:
    """Create and cache the Neo4jDAL."""
    driver = await get_neo4j_driver()
    return Neo4jDAL(driver=driver)

@lru_cache
async def get_ingestion_service(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    qdrant_dal: QdrantDAL = Depends(get_qdrant_dal),
    neo4j_dal: Neo4jDAL = Depends(get_neo4j_dal)
) -> IngestionService:
    """Create and cache the IngestionService."""
    return IngestionService(
        embedding_service=embedding_service,
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal
    )

@lru_cache
async def get_data_seeder_service(
    ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> DataSeederService:
    """Create and cache the DataSeederService."""
    return DataSeederService(ingestion_service=ingestion_service)

# Register routers
app.include_router(admin_router.router)

# Set up application-level dependency overrides
app.dependency_overrides[admin_router.get_data_seeder_service] = get_data_seeder_service

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {"status": "online", "service": "TwinCore API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 