"""
Database client initialization for Qdrant and Neo4j.

This module provides functions to create and get client instances
for Qdrant (vector database) and Neo4j (graph database).
"""

from functools import lru_cache
import logging
import asyncio
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from core.config import settings

logger = logging.getLogger(__name__)

# Singleton instances
_async_qdrant_client = None
_neo4j_driver = None
_neo4j_loop = None  # To track which event loop created the driver


def get_async_qdrant_client() -> AsyncQdrantClient:
    """
    Initialize and return an asynchronous Qdrant client.
    Uses singleton pattern to prevent multiple client instances.
    
    Returns:
        AsyncQdrantClient: A configured async Qdrant client instance
    """
    global _async_qdrant_client
    if _async_qdrant_client is None:
        try:
            logger.info(f"Initializing async Qdrant client at {settings.qdrant_host}:{settings.qdrant_port}")
            _async_qdrant_client = AsyncQdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                prefer_grpc=settings.qdrant_prefer_grpc,
                grpc_port=settings.qdrant_grpc_port,
                https=False,  # Explicitly use HTTP instead of HTTPS for local development
            )
            # Note: We don't do a health check here since it would require an await
            # Health check is performed at first use
            logger.info("Async Qdrant client initialized")
        except Exception as e:
            logger.error(f"Unexpected error initializing async Qdrant client: {e}")
            raise
    return _async_qdrant_client


async def get_neo4j_driver() -> AsyncDriver:
    """
    Create a fresh Neo4j driver.
    Creates a new connection each time to avoid event loop issues.
    
    Returns:
        AsyncDriver: A newly configured Neo4j driver instance
    """
    logger.info(f"Creating fresh Neo4j driver at {settings.neo4j_uri}")
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    # Verify connection
    async with driver.session() as session:
        await session.run("RETURN 1")
    logger.info("Neo4j driver created successfully")
    return driver


# Helper function to clear caches for testing
def clear_all_client_caches():
    """Clear all client instances for testing."""
    global _async_qdrant_client, _neo4j_driver, _neo4j_loop
    _async_qdrant_client = None
    _neo4j_driver = None
    _neo4j_loop = None

# Helper functions for testing removed, as they are replaced by fixture in conftest.py 