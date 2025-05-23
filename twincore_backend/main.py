from fastapi import FastAPI, Depends
from functools import lru_cache

from core.config import settings
from core.db_clients import get_async_qdrant_client, get_neo4j_driver, _async_qdrant_client as qdrant_client_instance
from dal.qdrant_dal import QdrantDAL
from dal.neo4j_dal import Neo4jDAL
from services.embedding_service import EmbeddingService
from services.ingestion_service import IngestionService
from services.retrieval_service import RetrievalService
from ingestion.connectors.message_connector import MessageConnector
from ingestion.connectors.document_connector import DocumentConnector
from ingestion.processors.text_chunker import TextChunker
from services.data_seeder_service import DataSeederService
from services.data_management_service import DataManagementService
from api.routers import admin_router, ingest_router, retrieve_router, document_router
from api.routers import user_router
from core.db_setup import initialize_databases

app = FastAPI(
    title="TwinCore API",
    description="Digital Twin Backend Service for Context Retrieval and User Representation",
    version="0.1.0"
)

# Singleton instances - only used for services that don't depend on event loop
_embedding_service = None
_qdrant_dal = None
_text_chunker = None

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
    """
    Create Neo4jDAL with a fresh driver.
    Each call creates a new driver to avoid event loop issues.
    """
    driver = await get_neo4j_driver()
    return Neo4jDAL(driver=driver)

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

@lru_cache
def get_text_chunker() -> TextChunker:
    """Create and cache the TextChunker."""
    global _text_chunker
    if _text_chunker is None:
        _text_chunker = TextChunker()
    return _text_chunker

async def get_message_connector() -> MessageConnector:
    """
    Create a fresh MessageConnector instance for each request.
    This ensures no event loop issues between test runs.
    """
    # Create a fresh ingestion service for this request
    ingestion_service = IngestionService(
        embedding_service=get_embedding_service(),
        qdrant_dal=get_qdrant_dal(),
        neo4j_dal=await get_neo4j_dal()
    )
    
    # Create a fresh connector
    return MessageConnector(ingestion_service=ingestion_service)

async def get_document_connector() -> DocumentConnector:
    """
    Create a fresh DocumentConnector instance for each request.
    This ensures no event loop issues between test runs.
    """
    # Create a fresh ingestion service for this request
    ingestion_service = IngestionService(
        embedding_service=get_embedding_service(),
        qdrant_dal=get_qdrant_dal(),
        neo4j_dal=await get_neo4j_dal()
    )
    
    # Create a fresh connector
    return DocumentConnector(
        ingestion_service=ingestion_service,
        text_chunker=get_text_chunker()
    )

async def get_data_seeder_service() -> DataSeederService:
    """
    Create a fresh DataSeederService instance for each request.
    This ensures no event loop issues between test runs.
    """
    # Create a fresh ingestion service for this request
    ingestion_service = IngestionService(
        embedding_service=get_embedding_service(),
        qdrant_dal=get_qdrant_dal(),
        neo4j_dal=await get_neo4j_dal()
    )
    
    # Create a fresh seeder service
    return DataSeederService(ingestion_service=ingestion_service)

async def get_data_management_service() -> DataManagementService:
    """
    Create a fresh DataManagementService instance for each request.
    This ensures no event loop issues between test runs.
    """
    # Create a fresh DALs for this request
    qdrant_dal = get_qdrant_dal()
    neo4j_dal = await get_neo4j_dal()
    
    # Create a fresh management service
    return DataManagementService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal
    )

async def get_retrieval_service() -> RetrievalService:
    """
    Create a fresh RetrievalService instance for each request.
    This ensures no event loop issues between test runs.
    """
    # Create a fresh DALs for this request
    qdrant_dal = get_qdrant_dal()
    neo4j_dal = await get_neo4j_dal()
    embedding_service = get_embedding_service()
    
    # Create a fresh retrieval service
    return RetrievalService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service
    )

async def get_retrieval_service_with_message_connector() -> RetrievalService:
    """
    Create a fresh RetrievalService instance with MessageConnector for each request.
    This ensures no event loop issues between test runs.
    """
    # Create fresh DALs for this request
    qdrant_dal = get_qdrant_dal()
    neo4j_dal = await get_neo4j_dal()
    embedding_service = get_embedding_service()
    
    # Create a fresh ingestion service
    ingestion_service = IngestionService(
        embedding_service=embedding_service,
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal
    )
    
    # Create a message connector
    message_connector = MessageConnector(ingestion_service=ingestion_service)
    
    # Create a fresh retrieval service with message connector
    return RetrievalService(
        qdrant_dal=qdrant_dal,
        neo4j_dal=neo4j_dal,
        embedding_service=embedding_service,
        message_connector=message_connector
    )

# Register routers
app.include_router(admin_router.router)
app.include_router(ingest_router.router)
app.include_router(retrieve_router.router)
app.include_router(document_router.router)
app.include_router(user_router.router)

# Set up application-level dependency overrides
app.dependency_overrides[admin_router.get_data_seeder_service] = get_data_seeder_service
app.dependency_overrides[admin_router.get_data_management_service] = get_data_management_service
app.dependency_overrides[ingest_router.get_message_connector] = get_message_connector
app.dependency_overrides[ingest_router.get_document_connector] = get_document_connector
app.dependency_overrides[retrieve_router.get_retrieval_service] = get_retrieval_service
app.dependency_overrides[retrieve_router.get_retrieval_service_with_message_connector] = get_retrieval_service_with_message_connector
app.dependency_overrides[document_router.get_data_management_service] = get_data_management_service
app.dependency_overrides[user_router.get_retrieval_service] = get_retrieval_service

@app.on_event("startup")
async def startup_event():
    """Initialize databases when the application starts."""
    await initialize_databases()

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {"status": "online", "service": "TwinCore API"}

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application stops."""
    # Close the Qdrant client if it was initialized
    if qdrant_client_instance:
        try:
            await qdrant_client_instance.close()
            print("Qdrant client closed.") # Optional: for logging/confirmation
        except Exception as e:
            print(f"Error closing Qdrant client: {e}") # Optional: log error

    # Neo4j drivers are typically created per-request or managed within specific functions,
    # so no global driver needs closing here based on the current setup.
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 